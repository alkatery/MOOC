"""Tests for the automatic quiz grader."""

from __future__ import annotations

import uuid
from datetime import datetime

from mooc.database import session_scope
from mooc.models import (
    Assignment,
    AssignmentSubmission,
    Course,
    CourseStatus,
    Enrollment,
    Module,
    Lesson,
    LessonType,
    Question,
    QuestionType,
    Quiz,
    QuizAttempt,
    User,
    UserRole,
)
from mooc.security import hash_password
from mooc.services.grading import (
    compute_final_grade,
    grade_question,
    regrade_attempt_with_manual,
)


def _make(qtype, correct, **kw):
    return Question(
        quiz_id=1,
        question_type=qtype,
        text_ar="س",
        choices=kw.get("choices", []),
        correct_answer=correct,
        points=kw.get("points", 1.0),
        order_index=1,
    )


def test_multiple_choice():
    q = _make(QuestionType.MULTIPLE_CHOICE, ["Python"], choices=["Python", "Java"])
    assert grade_question(q, "Python") == (1.0, True)
    assert grade_question(q, "Java") == (0.0, False)


def test_true_false():
    q = _make(QuestionType.TRUE_FALSE, ["صح"], choices=["صح", "خطأ"])
    assert grade_question(q, "صح")[1] is True
    assert grade_question(q, "خطأ")[1] is False


def test_multiple_answer_requires_exact_set():
    q = _make(
        QuestionType.MULTIPLE_ANSWER,
        ["A", "B"],
        choices=["A", "B", "C"],
    )
    assert grade_question(q, ["A", "B"])[1] is True
    assert grade_question(q, ["A"])[1] is False
    assert grade_question(q, ["A", "B", "C"])[1] is False


def test_short_answer_case_insensitive():
    q = _make(QuestionType.SHORT_ANSWER, ["print"])
    assert grade_question(q, "PRINT")[1] is True
    assert grade_question(q, "printf")[1] is False


def test_essay_is_not_auto_graded():
    q = _make(QuestionType.ESSAY, [])
    assert grade_question(q, "some answer") == (0.0, False)


# ---------------------------------------------------------------------------
# compute_final_grade with assignments
# ---------------------------------------------------------------------------


def _build_course_with_one_assignment(db, *, with_quiz=False):
    suffix = uuid.uuid4().hex[:6]
    instructor = User(
        email=f"i-{suffix}@x.sa",
        full_name_ar="معلم",
        password_hash=hash_password("X1234567"),
        role=UserRole.INSTRUCTOR,
    )
    student = User(
        email=f"s-{suffix}@x.sa",
        full_name_ar="طالب",
        password_hash=hash_password("X1234567"),
        role=UserRole.STUDENT,
    )
    db.add_all([instructor, student])
    db.flush()
    course = Course(
        code=f"C{suffix}",
        title_ar="مقرر",
        short_description_ar="x",
        description_ar="x",
        instructor_id=instructor.id,
        status=CourseStatus.PUBLISHED,
    )
    db.add(course)
    db.flush()
    enrollment = Enrollment(user_id=student.id, course_id=course.id)
    assignment = Assignment(
        course_id=course.id,
        title_ar="واجب",
        instructions_ar="افعل كذا",
        max_score=100.0,
    )
    db.add_all([enrollment, assignment])
    db.flush()
    quiz = None
    if with_quiz:
        module = Module(course_id=course.id, title_ar="و", order_index=1)
        db.add(module)
        db.flush()
        lesson = Lesson(module_id=module.id, title_ar="د", lesson_type=LessonType.TEXT, order_index=1)
        db.add(lesson)
        db.flush()
        quiz = Quiz(lesson_id=lesson.id, title_ar="ا", passing_score=60, max_attempts=3)
        db.add(quiz)
        db.flush()
    return enrollment, assignment, quiz, student


def test_unsubmitted_assignment_drops_grade_to_zero():
    with session_scope() as db:
        enrollment, _a, _q, _s = _build_course_with_one_assignment(db)
        assert compute_final_grade(db, enrollment) == 0.0


def test_graded_assignment_lifts_grade():
    with session_scope() as db:
        enrollment, assignment, _q, student = _build_course_with_one_assignment(db)
        sub = AssignmentSubmission(
            assignment_id=assignment.id,
            user_id=student.id,
            content="answer",
            score=80.0,
            graded_at=datetime.utcnow(),
        )
        db.add(sub)
        db.flush()
        assert compute_final_grade(db, enrollment) == 80.0


def test_quiz_and_assignment_weighted_50_50():
    with session_scope() as db:
        enrollment, assignment, quiz, student = _build_course_with_one_assignment(
            db, with_quiz=True
        )
        # Perfect quiz attempt
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=student.id,
            enrollment_id=enrollment.id,
            score=10.0,
            max_score=10.0,
            submitted_at=datetime.utcnow(),
            passed=True,
        )
        # 60% assignment
        sub = AssignmentSubmission(
            assignment_id=assignment.id,
            user_id=student.id,
            content="x",
            score=60.0,
            graded_at=datetime.utcnow(),
        )
        db.add_all([attempt, sub])
        db.flush()
        assert compute_final_grade(db, enrollment) == 80.0


# ---------------------------------------------------------------------------
# Manual essay regrading
# ---------------------------------------------------------------------------


def test_regrade_attempt_with_manual_scores():
    with session_scope() as db:
        enrollment, _a, _q, student = _build_course_with_one_assignment(
            db, with_quiz=True
        )
        # Add an essay question to the quiz
        quiz = db.query(Quiz).filter(Quiz.lesson.has()).first()
        essay = Question(
            quiz_id=quiz.id,
            question_type=QuestionType.ESSAY,
            text_ar="اشرح",
            choices=[],
            correct_answer=[],
            points=10.0,
            order_index=1,
        )
        db.add(essay)
        db.flush()
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=student.id,
            enrollment_id=enrollment.id,
            score=0.0,
            max_score=10.0,
            answers={str(essay.id): {"given": "إجابة الطالب", "earned": 0.0, "max": 10.0}},
            submitted_at=datetime.utcnow(),
            passed=False,
        )
        db.add(attempt)
        db.flush()

        regrade_attempt_with_manual(db, attempt, {str(essay.id): 7.0})
        assert attempt.score == 7.0
        assert attempt.answers[str(essay.id)]["earned"] == 7.0
        assert attempt.answers[str(essay.id)]["manual"] is True
