"""Student portal (صفحة الطالب)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import (
    Certificate,
    Course,
    CourseStatus,
    DiscussionPost,
    DiscussionThread,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
    Quiz,
    QuizAttempt,
    User,
    UserRole,
)
from ..security import get_current_user, require_roles
from ..services import xapi
from ..services.audit import log as audit_log
from ..services.certificates import issue_certificate
from ..services.grading import (
    compute_final_grade,
    grade_attempt,
    recompute_progress,
)

router = APIRouter(prefix="/student", tags=["student-portal"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

require_student_access = require_roles(
    UserRole.STUDENT, UserRole.INSTRUCTOR, UserRole.ADMIN
)


def _ctx(request: Request, user: User, **kwargs):
    return {"request": request, "user": user, "settings": get_settings(), **kwargs}


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
):
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id)
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    certificates = (
        db.query(Certificate).filter(Certificate.user_id == user.id).all()
    )
    return templates.TemplateResponse(request, "student/dashboard.html",
        _ctx(request, user, enrollments=enrollments, certificates=certificates),
    )


@router.get("/enroll/{course_id}")
def enroll_course(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course.status != CourseStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="المقرر غير متاح")

    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        enrollment = Enrollment(user_id=user.id, course_id=course_id)
        db.add(enrollment)
        db.flush()
        xapi.record_statement(
            db, user, "registered", "course", course.id, commit=False
        )
        audit_log(db, user, "enrollment.create", "enrollment", enrollment.id)
        db.commit()
    return RedirectResponse(
        f"/student/course/{course_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/course/{course_id}", response_class=HTMLResponse)
def course_player(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=403, detail="سجّل في المقرر أولاً")

    progress_map = {
        p.lesson_id: p
        for p in db.query(LessonProgress)
        .filter(LessonProgress.enrollment_id == enrollment.id)
        .all()
    }
    return templates.TemplateResponse(request, "student/course_player.html",
        _ctx(
            request,
            user,
            course=course,
            enrollment=enrollment,
            progress_map=progress_map,
        ),
    )


@router.get("/lesson/{lesson_id}", response_class=HTMLResponse)
def lesson_view(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
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
        raise HTTPException(status_code=403, detail="سجّل في المقرر أولاً")

    # Record first view
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
        xapi.record_statement(db, user, "experienced", "lesson", lesson.id)
    enrollment.last_accessed_at = datetime.utcnow()
    db.commit()

    return templates.TemplateResponse(request, "student/lesson.html",
        _ctx(
            request,
            user,
            lesson=lesson,
            course=lesson.module.course,
            enrollment=enrollment,
            progress=progress,
        ),
    )


@router.post("/lesson/{lesson_id}/complete")
def lesson_complete(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
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
        raise HTTPException(status_code=403, detail="سجّل في المقرر أولاً")

    progress = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.enrollment_id == enrollment.id,
            LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    if not progress:
        progress = LessonProgress(enrollment_id=enrollment.id, lesson_id=lesson_id)
        db.add(progress)
    progress.completed = True
    progress.completed_at = datetime.utcnow()
    xapi.record_statement(db, user, "completed", "lesson", lesson.id)
    recompute_progress(db, enrollment)
    db.commit()
    return RedirectResponse(
        f"/student/course/{course_id}", status_code=status.HTTP_303_SEE_OTHER
    )


# ---------------------------------------------------------------------------
# Quizzes (exercises + exams)
# ---------------------------------------------------------------------------


@router.get("/quiz/{quiz_id}", response_class=HTMLResponse)
def quiz_view(
    quiz_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="الاختبار غير موجود")
    course_id = quiz.lesson.module.course_id
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=403, detail="سجّل في المقرر أولاً")

    prior = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user.id)
        .order_by(QuizAttempt.started_at.desc())
        .all()
    )
    return templates.TemplateResponse(request, "student/quiz.html",
        _ctx(request, user, quiz=quiz, course=quiz.lesson.module.course, attempts=prior),
    )


@router.post("/quiz/{quiz_id}/submit", response_class=HTMLResponse)
async def quiz_submit(
    quiz_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="الاختبار غير موجود")
    course_id = quiz.lesson.module.course_id
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=403, detail="سجّل في المقرر أولاً")

    form = await request.form()
    answers = {}
    for key, value in form.multi_items():
        if key.startswith("q_"):
            qid = key[2:]
            answers.setdefault(qid, [])
            answers[qid].append(value)
    # Flatten single answers
    for k, v in list(answers.items()):
        if len(v) == 1:
            answers[k] = v[0]

    attempt = QuizAttempt(
        quiz_id=quiz_id, user_id=user.id, enrollment_id=enrollment.id
    )
    db.add(attempt)
    db.flush()
    grade_attempt(db, quiz, attempt, answers)
    xapi.record_statement(
        db,
        user,
        "scored",
        "quiz",
        quiz.id,
        result={"score": {"raw": attempt.score, "max": attempt.max_score}},
    )
    xapi.record_statement(
        db, user, "passed" if attempt.passed else "failed", "quiz", quiz.id
    )
    recompute_progress(db, enrollment)
    db.commit()
    return templates.TemplateResponse(request, "student/quiz_result.html",
        _ctx(
            request,
            user,
            quiz=quiz,
            attempt=attempt,
            course=quiz.lesson.module.course,
        ),
    )


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------


@router.post("/course/{course_id}/claim-certificate")
def claim_certificate(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
):
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="لا يوجد تسجيل للمقرر")
    recompute_progress(db, enrollment)
    grade = compute_final_grade(db, enrollment)
    enrollment.final_grade = grade
    course = db.query(Course).filter(Course.id == course_id).first()
    if enrollment.progress_percent < 100.0 or grade < course.passing_grade:
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"لم تكتمل متطلبات الشهادة بعد. التقدم: {enrollment.progress_percent}٪، الدرجة: {grade}",
        )
    cert = issue_certificate(db, enrollment, grade)
    xapi.record_statement(
        db, user, "earned", "certificate", cert.verification_code
    )
    db.commit()
    return RedirectResponse(
        f"/certificates/{cert.verification_code}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ---------------------------------------------------------------------------
# Discussions
# ---------------------------------------------------------------------------


@router.post("/course/{course_id}/thread")
def post_thread(
    course_id: int,
    title_ar: str = Form(...),
    body_ar: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_student_access),
):
    if not db.query(Course).filter(Course.id == course_id).first():
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    thread = DiscussionThread(
        course_id=course_id,
        author_id=user.id,
        title_ar=title_ar,
        body_ar=body_ar,
    )
    db.add(thread)
    audit_log(db, user, "thread.create", "thread", None)
    db.commit()
    return RedirectResponse(
        f"/student/course/{course_id}", status_code=status.HTTP_303_SEE_OTHER
    )
