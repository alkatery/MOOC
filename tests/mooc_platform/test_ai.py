"""Tests for the local AI provider, student tutor, and admin insights.

These tests run with no Ollama instance available, so they verify the
graceful-fallback path and the deterministic statistics. They do NOT
exercise actual model output.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta

import pytest

from mooc.database import session_scope
from mooc.models import (
    Course,
    CourseStatus,
    Enrollment,
    EnrollmentStatus,
    Lesson,
    LessonProgress,
    LessonType,
    Module,
    Question,
    QuestionType,
    Quiz,
    QuizAttempt,
    User,
    UserRole,
)
from mooc.security import hash_password
from mooc.services import ai
from mooc.services.admin_insights import (
    _bottleneck_lessons,
    _confusing_questions,
    compute_insights,
    generate_admin_summary_ar,
)


@pytest.fixture(autouse=True)
def _force_unreachable_ollama(monkeypatch):
    monkeypatch.setenv("MOOC_OLLAMA_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("MOOC_AI_TIMEOUT", "1")


def test_chat_returns_arabic_fallback_when_ollama_unreachable():
    text = ai.chat([{"role": "user", "content": "مرحبا"}])
    assert "تعذّر" in text


def test_is_available_returns_false_when_ollama_unreachable():
    assert ai.is_available() is False


def test_admin_summary_falls_back_gracefully():
    text = generate_admin_summary_ar({"top_students": [], "at_risk_students": []})
    assert isinstance(text, str)
    assert text  # non-empty (fallback string)


# ---------------------------------------------------------------------------
# Insights computation (no AI involved)
# ---------------------------------------------------------------------------


def _seed_minimal_course(db):
    suffix = uuid.uuid4().hex[:6]
    instructor = User(
        email=f"i-{suffix}@x.sa",
        full_name_ar="معلم",
        password_hash=hash_password("X1234567"),
        role=UserRole.INSTRUCTOR,
    )
    db.add(instructor)
    db.flush()
    course = Course(
        code=f"C{suffix}",
        title_ar="مقرر إحصاءات",
        short_description_ar="x",
        description_ar="x",
        instructor_id=instructor.id,
        status=CourseStatus.PUBLISHED,
    )
    db.add(course)
    db.flush()
    module = Module(course_id=course.id, title_ar="و", order_index=1)
    db.add(module)
    db.flush()
    lesson = Lesson(
        module_id=module.id,
        title_ar="درس مشكل",
        lesson_type=LessonType.TEXT,
        order_index=1,
    )
    db.add(lesson)
    db.flush()
    return course, lesson


def test_bottleneck_lessons_flags_low_completion():
    with session_scope() as db:
        course, lesson = _seed_minimal_course(db)
        # 5 students start, only 1 completes
        for i in range(5):
            student = User(
                email=f"st{i}-{uuid.uuid4().hex[:4]}@x.sa",
                full_name_ar=f"طالب {i}",
                password_hash=hash_password("X1234567"),
                role=UserRole.STUDENT,
            )
            db.add(student)
            db.flush()
            enrollment = Enrollment(user_id=student.id, course_id=course.id)
            db.add(enrollment)
            db.flush()
            progress = LessonProgress(
                enrollment_id=enrollment.id,
                lesson_id=lesson.id,
                completed=(i == 0),
            )
            db.add(progress)
        db.flush()
        rows = _bottleneck_lessons(db, top_n=5)
        assert any(r["lesson_id"] == lesson.id for r in rows)
        target = next(r for r in rows if r["lesson_id"] == lesson.id)
        assert target["started"] == 5
        assert target["completed"] == 1
        assert target["completion_rate"] == 20.0


def test_compute_insights_returns_expected_shape():
    with session_scope() as db:
        insights = compute_insights(db)
        for key in (
            "top_students",
            "at_risk_students",
            "bottleneck_lessons",
            "confusing_questions",
            "totals",
        ):
            assert key in insights
        assert {"students", "active_enrollments", "completed_enrollments"} <= set(
            insights["totals"]
        )
