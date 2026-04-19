"""Automated grading for quizzes + progress recomputation helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from ..models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    Lesson,
    LessonProgress,
    Module,
    Question,
    QuestionType,
    Quiz,
    QuizAttempt,
)


def _normalize(value) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    if value is None:
        return []
    return [str(value).strip()]


def grade_question(question: Question, answer) -> Tuple[float, bool]:
    """Return ``(earned_points, is_correct)`` for a single question."""
    correct = _normalize(question.correct_answer)
    given = _normalize(answer)

    if question.question_type in (
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.TRUE_FALSE,
    ):
        is_correct = bool(given) and given[0].lower() == (correct[0].lower() if correct else "")
    elif question.question_type == QuestionType.MULTIPLE_ANSWER:
        is_correct = sorted(g.lower() for g in given) == sorted(c.lower() for c in correct)
    elif question.question_type == QuestionType.SHORT_ANSWER:
        is_correct = any(g.strip().lower() == c.strip().lower() for g in given for c in correct)
    else:  # Essay — needs manual grading
        return 0.0, False

    return (question.points if is_correct else 0.0, is_correct)


def grade_attempt(
    db: Session, quiz: Quiz, attempt: QuizAttempt, answers: Dict[str, object]
) -> QuizAttempt:
    total = 0.0
    max_total = 0.0
    detail = {}
    for question in quiz.questions:
        max_total += question.points
        ans = answers.get(str(question.id))
        earned, correct = grade_question(question, ans)
        total += earned
        detail[str(question.id)] = {
            "given": ans,
            "earned": earned,
            "correct": correct,
            "max": question.points,
        }
    attempt.score = round(total, 2)
    attempt.max_score = round(max_total, 2)
    attempt.answers = detail
    attempt.submitted_at = datetime.utcnow()
    attempt.passed = (
        (total / max_total * 100.0) >= quiz.passing_score if max_total > 0 else False
    )
    db.flush()
    return attempt


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


def recompute_progress(db: Session, enrollment: Enrollment) -> Enrollment:
    """Recalculate ``progress_percent`` and ``status`` for an enrollment."""
    total_lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == enrollment.course_id)
        .count()
    )
    if total_lessons == 0:
        enrollment.progress_percent = 0.0
        return enrollment

    completed = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.enrollment_id == enrollment.id,
            LessonProgress.completed.is_(True),
        )
        .count()
    )
    enrollment.progress_percent = round(completed / total_lessons * 100.0, 2)
    if enrollment.progress_percent >= 100.0 and enrollment.status != EnrollmentStatus.COMPLETED:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = datetime.utcnow()
    enrollment.last_accessed_at = datetime.utcnow()
    return enrollment


def compute_final_grade(db: Session, enrollment: Enrollment) -> float:
    """Average of all quiz attempts for the enrollment."""
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.enrollment_id == enrollment.id)
        .all()
    )
    if not attempts:
        return 0.0
    scores = []
    for a in attempts:
        if a.max_score:
            scores.append(a.score / a.max_score * 100.0)
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 2)
