"""Lesson and module routes — API + lesson viewer helpers."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
    User,
    UserRole,
)
from ..schemas import LessonIn, LessonOut, ModuleIn, ModuleOut
from ..security import get_current_user, require_instructor
from ..services import xapi
from ..services.audit import log as audit_log
from ..services.grading import recompute_progress

router = APIRouter(prefix="/api", tags=["lessons"])


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------


@router.post(
    "/courses/{course_id}/modules", response_model=ModuleOut, status_code=201
)
def create_module(
    course_id: int,
    payload: ModuleIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")

    module = Module(
        course_id=course_id,
        title_ar=payload.title_ar,
        description_ar=payload.description_ar,
        order_index=payload.order_index,
    )
    db.add(module)
    db.flush()
    audit_log(db, user, "module.create", "module", module.id)
    db.commit()
    return module


@router.get("/courses/{course_id}/modules", response_model=List[ModuleOut])
def list_modules(course_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Module)
        .filter(Module.course_id == course_id)
        .order_by(Module.order_index)
        .all()
    )


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------


@router.post(
    "/modules/{module_id}/lessons", response_model=LessonOut, status_code=201
)
def create_lesson(
    module_id: int,
    payload: LessonIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="الوحدة غير موجودة")
    course = module.course
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")

    lesson = Lesson(
        module_id=module_id,
        title_ar=payload.title_ar,
        lesson_type=payload.lesson_type,
        content=payload.content,
        resource_url=payload.resource_url,
        duration_minutes=payload.duration_minutes,
        order_index=payload.order_index,
        is_free_preview=payload.is_free_preview,
        has_transcript=payload.has_transcript,
        transcript_text=payload.transcript_text,
        has_sign_language=payload.has_sign_language,
        captions_url=payload.captions_url,
    )
    db.add(lesson)
    db.flush()
    audit_log(db, user, "lesson.create", "lesson", lesson.id)
    db.commit()
    return lesson


@router.post("/lessons/{lesson_id}/complete")
def complete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    course_id = lesson.module.course_id
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=400, detail="أنت غير مسجّل في هذا المقرر")

    progress = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.enrollment_id == enrollment.id,
            LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    if not progress:
        progress = LessonProgress(
            enrollment_id=enrollment.id,
            lesson_id=lesson_id,
            first_viewed_at=datetime.utcnow(),
        )
        db.add(progress)

    progress.completed = True
    progress.completed_at = datetime.utcnow()

    xapi.record_statement(
        db,
        actor=user,
        verb="completed",
        object_type="lesson",
        object_id=lesson.id,
        context={"course_id": course_id},
    )
    recompute_progress(db, enrollment)
    db.commit()
    return {"status": "ok", "progress": enrollment.progress_percent}
