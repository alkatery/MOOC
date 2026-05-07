"""Automated grading for quizzes + progress recomputation helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from ..models import (
    Assignment,
    AssignmentSubmission,
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


def regrade_attempt_with_manual(
    db: Session, attempt: QuizAttempt, manual_scores: Dict[str, float]
) -> QuizAttempt:
    """Apply manually-entered essay scores to an existing attempt.

    ``manual_scores`` maps question_id (str) → earned points. The
    attempt's stored ``answers`` dict is updated in place so the
    student sees the new totals on `/student` and certificates use the
    correct final grade.
    """
    detail = dict(attempt.answers or {})
    auto_total = 0.0
    max_total = 0.0
    for question in attempt.quiz.questions:
        max_total += question.points
        qid = str(question.id)
        entry = detail.get(qid) or {"given": None, "earned": 0.0, "correct": False, "max": question.points}
        if question.question_type == QuestionType.ESSAY and qid in manual_scores:
            earned = max(0.0, min(float(manual_scores[qid]), question.points))
            entry["earned"] = earned
            entry["correct"] = earned >= question.points
            entry["manual"] = True
        detail[qid] = entry
        auto_total += float(entry.get("earned") or 0.0)
    attempt.answers = detail
    attempt.score = round(auto_total, 2)
    attempt.max_score = round(max_total, 2)
    if max_total > 0:
        attempt.passed = (auto_total / max_total * 100.0) >= attempt.quiz.passing_score
    db.flush()
    return attempt


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
    """Weighted average of quiz attempts and assignment submissions.

    Defaults to 50/50 between the two components. If the course only has
    quizzes (or only has assignments), the present component takes 100%.
    Missing assignments count as zeros so a student cannot earn a
    certificate without submitting.
    """
    quiz_pct = _quiz_average_percent(db, enrollment)
    assignment_pct = _assignment_average_percent(db, enrollment)

    quiz_weight = 0.5 if quiz_pct is not None else 0.0
    assignment_weight = 0.5 if assignment_pct is not None else 0.0
    if quiz_weight == 0.0 and assignment_weight == 0.0:
        return 0.0
    if quiz_weight == 0.0:
        return round(assignment_pct or 0.0, 2)
    if assignment_weight == 0.0:
        return round(quiz_pct or 0.0, 2)

    total_weight = quiz_weight + assignment_weight
    weighted = (
        (quiz_pct or 0.0) * quiz_weight + (assignment_pct or 0.0) * assignment_weight
    ) / total_weight
    return round(weighted, 2)


def _quiz_average_percent(db: Session, enrollment: Enrollment):
    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.enrollment_id == enrollment.id,
            QuizAttempt.submitted_at.isnot(None),
        )
        .all()
    )
    if not attempts:
        return None
    scores = [a.score / a.max_score * 100.0 for a in attempts if a.max_score]
    if not scores:
        return None
    return sum(scores) / len(scores)


def _assignment_average_percent(db: Session, enrollment: Enrollment):
    """Average graded-assignment percentage for the enrollment's course.

    Unsubmitted or ungraded assignments count as 0 so the student must
    actually do the work.
    """
    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == enrollment.course_id)
        .all()
    )
    if not assignments:
        return None
    total = 0.0
    for a in assignments:
        if not a.max_score:
            continue
        sub = (
            db.query(AssignmentSubmission)
            .filter(
                AssignmentSubmission.assignment_id == a.id,
                AssignmentSubmission.user_id == enrollment.user_id,
                AssignmentSubmission.score.isnot(None),
            )
            .order_by(AssignmentSubmission.graded_at.desc())
            .first()
        )
        if sub:
            total += (sub.score or 0.0) / a.max_score * 100.0
    return total / len(assignments)
