"""Course CRUD API."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Category, Course, CourseStatus, User, UserRole
from ..schemas import CategoryOut, CourseIn, CourseOut
from ..security import get_current_user, require_instructor, require_admin
from ..services.audit import log as audit_log

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name_ar).all()


@router.get("", response_model=List[CourseOut])
def list_courses(
    q: Optional[str] = Query(None),
    category_id: Optional[int] = None,
    status: Optional[CourseStatus] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Course)
    if status:
        query = query.filter(Course.status == status)
    else:
        query = query.filter(Course.status == CourseStatus.PUBLISHED)
    if category_id:
        query = query.filter(Course.category_id == category_id)
    if q:
        like = f"%{q}%"
        query = query.filter(Course.title_ar.ilike(like))
    return query.order_by(Course.published_at.desc().nullslast()).limit(100).all()


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    return course


@router.post("", response_model=CourseOut, status_code=201)
def create_course(
    payload: CourseIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    if db.query(Course).filter(Course.code == payload.code).first():
        raise HTTPException(status_code=400, detail="رمز المقرر مستخدم بالفعل")

    course = Course(
        code=payload.code,
        title_ar=payload.title_ar,
        title_en=payload.title_en,
        short_description_ar=payload.short_description_ar,
        description_ar=payload.description_ar,
        category_id=payload.category_id,
        level=payload.level,
        language=payload.language,
        duration_hours=payload.duration_hours,
        price=payload.price,
        is_free=payload.is_free,
        passing_grade=payload.passing_grade,
        max_attempts=payload.max_attempts,
        learning_outcomes=payload.learning_outcomes,
        target_audience=payload.target_audience,
        prerequisites=payload.prerequisites,
        accessibility_features=payload.accessibility_features,
        instructor_id=user.id,
        status=CourseStatus.DRAFT,
    )
    db.add(course)
    db.flush()
    audit_log(
        db,
        actor=user,
        action="course.create",
        entity_type="course",
        entity_id=course.public_id,
        metadata={"code": course.code},
    )
    db.commit()
    return course


@router.put("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    payload: CourseIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="لا يمكنك تعديل مقرر غيرك")

    for field, value in payload.model_dump().items():
        setattr(course, field, value)
    audit_log(
        db,
        actor=user,
        action="course.update",
        entity_type="course",
        entity_id=course.public_id,
    )
    db.commit()
    return course


@router.post("/{course_id}/submit-for-review", response_model=CourseOut)
def submit_for_review(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="لا يمكنك إرسال مقرر غيرك للمراجعة")
    course.status = CourseStatus.UNDER_REVIEW
    audit_log(
        db,
        actor=user,
        action="course.submit_review",
        entity_type="course",
        entity_id=course.public_id,
    )
    db.commit()
    return course


@router.post("/{course_id}/publish", response_model=CourseOut)
def publish_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    if course.status != CourseStatus.APPROVED:
        raise HTTPException(
            status_code=400, detail="يجب أن يمر المقرر بمراجعة الجودة وينال الاعتماد أولاً"
        )
    course.status = CourseStatus.PUBLISHED
    course.published_at = datetime.utcnow()
    audit_log(
        db,
        actor=user,
        action="course.publish",
        entity_type="course",
        entity_id=course.public_id,
    )
    db.commit()
    return course
