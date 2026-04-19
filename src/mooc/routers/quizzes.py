"""Quiz / exercise / exam routes."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Enrollment,
    Lesson,
    Question,
    Quiz,
    QuizAttempt,
    User,
    UserRole,
)
from ..schemas import (
    QuestionIn,
    QuestionOut,
    QuizAttemptIn,
    QuizAttemptOut,
    QuizIn,
    QuizOut,
)
from ..security import get_current_user, require_instructor
from ..services import xapi
from ..services.audit import log as audit_log
from ..services.grading import grade_attempt

router = APIRouter(prefix="/api", tags=["quizzes"])


@router.post("/lessons/{lesson_id}/quiz", response_model=QuizOut, status_code=201)
def create_quiz(
    lesson_id: int,
    payload: QuizIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    course = lesson.module.course
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")
    if lesson.quiz:
        raise HTTPException(status_code=400, detail="هذا الدرس يحتوي على اختبار بالفعل")

    quiz = Quiz(
        lesson_id=lesson_id,
        title_ar=payload.title_ar,
        instructions_ar=payload.instructions_ar,
        time_limit_minutes=payload.time_limit_minutes,
        passing_score=payload.passing_score,
        max_attempts=payload.max_attempts,
        shuffle_questions=payload.shuffle_questions,
        show_correct_answers=payload.show_correct_answers,
    )
    db.add(quiz)
    db.flush()
    audit_log(db, user, "quiz.create", "quiz", quiz.id)
    db.commit()
    return quiz


@router.post("/quizzes/{quiz_id}/questions", response_model=QuestionOut, status_code=201)
def add_question(
    quiz_id: int,
    payload: QuestionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="الاختبار غير موجود")
    course = quiz.lesson.module.course
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")

    question = Question(
        quiz_id=quiz_id,
        question_type=payload.question_type,
        text_ar=payload.text_ar,
        choices=payload.choices,
        correct_answer=payload.correct_answer,
        explanation_ar=payload.explanation_ar,
        points=payload.points,
        order_index=payload.order_index,
    )
    db.add(question)
    db.flush()
    audit_log(db, user, "question.create", "question", question.id)
    db.commit()
    return question


@router.get("/quizzes/{quiz_id}", response_model=QuizOut)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="الاختبار غير موجود")
    return quiz


@router.post("/quizzes/{quiz_id}/attempts", response_model=QuizAttemptOut)
def submit_attempt(
    quiz_id: int,
    payload: QuizAttemptIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
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
        raise HTTPException(status_code=400, detail="أنت غير مسجّل في المقرر")

    prior = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user.id)
        .count()
    )
    if quiz.max_attempts and prior >= quiz.max_attempts:
        raise HTTPException(status_code=400, detail="لقد استنفذت عدد المحاولات المسموحة")

    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=user.id,
        enrollment_id=enrollment.id,
    )
    db.add(attempt)
    db.flush()
    grade_attempt(db, quiz, attempt, payload.answers or {})

    xapi.record_statement(
        db,
        actor=user,
        verb="scored",
        object_type="quiz",
        object_id=quiz.id,
        result={
            "score": {
                "raw": attempt.score,
                "max": attempt.max_score,
                "scaled": (attempt.score / attempt.max_score) if attempt.max_score else 0,
            },
            "success": attempt.passed,
        },
    )
    xapi.record_statement(
        db,
        actor=user,
        verb="passed" if attempt.passed else "failed",
        object_type="quiz",
        object_id=quiz.id,
    )
    db.commit()
    return attempt
