"""Teacher / instructor portal (صفحة المعلم)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import (
    Assignment,
    AssignmentSubmission,
    Course,
    CourseLevel,
    CourseStatus,
    Enrollment,
    Lesson,
    LessonType,
    Module,
    Question,
    QuestionType,
    Quiz,
    User,
    UserRole,
)
from ..security import require_roles
from ..services.audit import log as audit_log

router = APIRouter(prefix="/teacher", tags=["teacher-portal"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

require_teacher = require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)


def _ctx(request, user, **kwargs):
    return {"request": request, "user": user, "settings": get_settings(), **kwargs}


def _own_course(db: Session, course_id: int, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")
    return course


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    courses = (
        db.query(Course)
        .filter(Course.instructor_id == user.id)
        .order_by(Course.created_at.desc())
        .all()
    )
    total_students = (
        db.query(Enrollment)
        .join(Course, Enrollment.course_id == Course.id)
        .filter(Course.instructor_id == user.id)
        .count()
    )
    return templates.TemplateResponse(request, "teacher/dashboard.html",
        _ctx(
            request,
            user,
            courses=courses,
            total_students=total_students,
            stats={
                "published": sum(
                    1 for c in courses if c.status == CourseStatus.PUBLISHED
                ),
                "draft": sum(1 for c in courses if c.status == CourseStatus.DRAFT),
                "in_review": sum(
                    1 for c in courses if c.status == CourseStatus.UNDER_REVIEW
                ),
            },
        ),
    )


# ---------------------------------------------------------------------------
# Course CRUD
# ---------------------------------------------------------------------------


@router.get("/courses/new", response_class=HTMLResponse)
def new_course(
    request: Request,
    user: User = Depends(require_teacher),
):
    return templates.TemplateResponse(request, "teacher/course_form.html",
        _ctx(request, user, course=None),
    )


@router.post("/courses/new")
def create_course(
    request: Request,
    code: str = Form(...),
    title_ar: str = Form(...),
    short_description_ar: str = Form(...),
    description_ar: str = Form(...),
    level: str = Form("beginner"),
    duration_hours: float = Form(0.0),
    passing_grade: int = Form(60),
    learning_outcomes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    if db.query(Course).filter(Course.code == code).first():
        raise HTTPException(status_code=400, detail="رمز المقرر مستخدم")
    outcomes = [line.strip() for line in learning_outcomes.splitlines() if line.strip()]
    course = Course(
        code=code,
        title_ar=title_ar,
        short_description_ar=short_description_ar,
        description_ar=description_ar,
        level=CourseLevel(level) if level in {l.value for l in CourseLevel} else CourseLevel.BEGINNER,
        duration_hours=duration_hours,
        passing_grade=passing_grade,
        learning_outcomes=outcomes,
        instructor_id=user.id,
    )
    db.add(course)
    db.flush()
    audit_log(db, user, "course.create", "course", course.public_id)
    db.commit()
    return RedirectResponse(
        f"/teacher/courses/{course.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/courses/{course_id}", response_class=HTMLResponse)
def course_editor(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _own_course(db, course_id, user)
    return templates.TemplateResponse(request, "teacher/course_editor.html",
        _ctx(
            request,
            user,
            course=course,
            lesson_types=[t.value for t in LessonType],
        ),
    )


@router.post("/courses/{course_id}/submit-for-review")
def submit_for_review(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _own_course(db, course_id, user)
    course.status = CourseStatus.UNDER_REVIEW
    audit_log(db, user, "course.submit_review", "course", course.public_id)
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


# ---------------------------------------------------------------------------
# Modules & lessons
# ---------------------------------------------------------------------------


@router.post("/courses/{course_id}/modules")
def add_module(
    course_id: int,
    title_ar: str = Form(...),
    description_ar: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _own_course(db, course_id, user)
    order = len(course.modules) + 1
    module = Module(
        course_id=course_id,
        title_ar=title_ar,
        description_ar=description_ar,
        order_index=order,
    )
    db.add(module)
    audit_log(db, user, "module.create", "module", None)
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


@router.post("/modules/{module_id}/lessons")
def add_lesson(
    module_id: int,
    title_ar: str = Form(...),
    lesson_type: str = Form("text"),
    content: str = Form(""),
    resource_url: str = Form(""),
    duration_minutes: int = Form(0),
    has_transcript: str = Form("off"),
    transcript_text: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="الوحدة غير موجودة")
    course = _own_course(db, module.course_id, user)

    lesson = Lesson(
        module_id=module_id,
        title_ar=title_ar,
        lesson_type=LessonType(lesson_type)
        if lesson_type in {t.value for t in LessonType}
        else LessonType.TEXT,
        content=content or None,
        resource_url=resource_url or None,
        duration_minutes=duration_minutes,
        order_index=len(module.lessons) + 1,
        has_transcript=has_transcript == "on",
        transcript_text=transcript_text or None,
    )
    db.add(lesson)
    audit_log(db, user, "lesson.create", "lesson", None)
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course.id}", status_code=303)


# ---------------------------------------------------------------------------
# Quiz builder
# ---------------------------------------------------------------------------


@router.get("/lessons/{lesson_id}/quiz", response_class=HTMLResponse)
def quiz_builder(
    lesson_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    _own_course(db, lesson.module.course_id, user)
    quiz = lesson.quiz
    return templates.TemplateResponse(request, "teacher/quiz_builder.html",
        _ctx(
            request,
            user,
            lesson=lesson,
            quiz=quiz,
            question_types=[t.value for t in QuestionType],
        ),
    )


@router.post("/lessons/{lesson_id}/quiz")
def create_quiz(
    lesson_id: int,
    title_ar: str = Form(...),
    instructions_ar: str = Form(""),
    time_limit_minutes: int = Form(0),
    passing_score: int = Form(60),
    max_attempts: int = Form(3),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    _own_course(db, lesson.module.course_id, user)
    if lesson.quiz:
        raise HTTPException(status_code=400, detail="هذا الدرس يحتوي اختباراً")
    quiz = Quiz(
        lesson_id=lesson_id,
        title_ar=title_ar,
        instructions_ar=instructions_ar,
        time_limit_minutes=time_limit_minutes,
        passing_score=passing_score,
        max_attempts=max_attempts,
    )
    db.add(quiz)
    audit_log(db, user, "quiz.create", "quiz", None)
    db.commit()
    return RedirectResponse(f"/teacher/lessons/{lesson_id}/quiz", status_code=303)


@router.post("/quizzes/{quiz_id}/questions")
def add_question(
    quiz_id: int,
    question_type: str = Form(...),
    text_ar: str = Form(...),
    choices: str = Form(""),
    correct_answer: str = Form(""),
    points: float = Form(1.0),
    explanation_ar: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="الاختبار غير موجود")
    _own_course(db, quiz.lesson.module.course_id, user)

    qt = (
        QuestionType(question_type)
        if question_type in {q.value for q in QuestionType}
        else QuestionType.MULTIPLE_CHOICE
    )
    choices_list = [c.strip() for c in choices.splitlines() if c.strip()]
    correct_list = [c.strip() for c in correct_answer.splitlines() if c.strip()]

    question = Question(
        quiz_id=quiz_id,
        question_type=qt,
        text_ar=text_ar,
        choices=choices_list,
        correct_answer=correct_list,
        points=points,
        explanation_ar=explanation_ar or None,
        order_index=len(quiz.questions) + 1,
    )
    db.add(question)
    audit_log(db, user, "question.create", "question", None)
    db.commit()
    return RedirectResponse(f"/teacher/lessons/{quiz.lesson_id}/quiz", status_code=303)


# ---------------------------------------------------------------------------
# Assignments & grading
# ---------------------------------------------------------------------------


@router.post("/courses/{course_id}/assignments")
def add_assignment(
    course_id: int,
    title_ar: str = Form(...),
    instructions_ar: str = Form(...),
    max_score: float = Form(100.0),
    due_at: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _own_course(db, course_id, user)
    due = None
    if due_at:
        try:
            due = datetime.fromisoformat(due_at)
        except ValueError:
            due = None
    assignment = Assignment(
        course_id=course_id,
        title_ar=title_ar,
        instructions_ar=instructions_ar,
        max_score=max_score,
        due_at=due,
    )
    db.add(assignment)
    audit_log(db, user, "assignment.create", "assignment", None)
    db.commit()
    return RedirectResponse(f"/teacher/courses/{course_id}", status_code=303)


@router.get("/submissions/{course_id}", response_class=HTMLResponse)
def list_submissions(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _own_course(db, course_id, user)
    submissions = (
        db.query(AssignmentSubmission)
        .join(Assignment, AssignmentSubmission.assignment_id == Assignment.id)
        .filter(Assignment.course_id == course_id)
        .order_by(AssignmentSubmission.submitted_at.desc())
        .all()
    )
    return templates.TemplateResponse(request, "teacher/submissions.html",
        _ctx(request, user, course=course, submissions=submissions),
    )


@router.post("/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    score: float = Form(...),
    feedback_ar: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    submission = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="التسليم غير موجود")
    assignment = submission.assignment
    _own_course(db, assignment.course_id, user)
    submission.score = score
    submission.feedback_ar = feedback_ar
    submission.graded_at = datetime.utcnow()
    submission.graded_by_id = user.id
    audit_log(db, user, "submission.grade", "submission", submission.id)
    db.commit()
    return RedirectResponse(
        f"/teacher/submissions/{assignment.course_id}", status_code=303
    )


# ---------------------------------------------------------------------------
# Class roster
# ---------------------------------------------------------------------------


@router.get("/courses/{course_id}/students", response_class=HTMLResponse)
def course_students(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _own_course(db, course_id, user)
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id)
        .order_by(Enrollment.progress_percent.desc())
        .all()
    )
    return templates.TemplateResponse(request, "teacher/students.html",
        _ctx(request, user, course=course, enrollments=enrollments),
    )
