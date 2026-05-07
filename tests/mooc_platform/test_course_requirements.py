"""Tests for the NELC course-system requirements catalog and evaluator."""

from __future__ import annotations

from mooc.models import (
    Course,
    CourseLevel,
    CourseStatus,
    DiscussionThread,
    Lesson,
    LessonType,
    Module,
    Question,
    QuestionType,
    Quiz,
    User,
    UserRole,
)
from mooc.nelc import (
    COURSE_REQUIREMENTS,
    RequirementLevel,
    excellence_requirements,
    mandatory_requirements,
    optional_requirements,
    requirement_by_code,
    requirements_summary,
)
from mooc.services.course_requirements import (
    compliance_report,
    evaluate_course,
    evaluate_requirement,
)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


def test_three_requirement_levels_present():
    levels = {r.level for r in COURSE_REQUIREMENTS}
    assert levels == {
        RequirementLevel.MANDATORY,
        RequirementLevel.OPTIONAL,
        RequirementLevel.EXCELLENCE,
    }


def test_requirement_codes_unique():
    codes = [r.code for r in COURSE_REQUIREMENTS]
    assert len(codes) == len(set(codes))


def test_requirements_summary_totals():
    summary = requirements_summary()
    assert summary["mandatory"] == len(mandatory_requirements())
    assert summary["optional"] == len(optional_requirements())
    assert summary["excellence"] == len(excellence_requirements())
    assert summary["total"] == (
        summary["mandatory"] + summary["optional"] + summary["excellence"]
    )


def test_mandatory_band_is_substantial():
    # NELC's mandatory band for course systems must cover a meaningful set.
    assert len(mandatory_requirements()) >= 25


def test_requirement_by_code():
    r = requirement_by_code("M.01")
    assert r is not None
    assert r.is_mandatory


def test_arabic_titles_for_each_requirement():
    for r in COURSE_REQUIREMENTS:
        assert r.title_ar
        assert r.title_en
        assert r.description_ar


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def _empty_course() -> Course:
    """Build an unsaved Course with no modules / lessons."""
    return Course(
        code="EMPTY",
        title_ar="مقرر فارغ",
        short_description_ar="",
        description_ar="",
        level=CourseLevel.BEGINNER,
        language="ar",
        duration_hours=0.0,
        passing_grade=60,
        max_attempts=3,
        learning_outcomes=[],
        accessibility_features=[],
        nelc_metadata={},
        instructor_id=1,
        status=CourseStatus.DRAFT,
    )


def _good_course() -> Course:
    instructor = User(
        id=1,
        email="t@x.sa",
        full_name_ar="معلم تجريبي",
        password_hash="x",
        role=UserRole.INSTRUCTOR,
    )
    course = Course(
        code="DEMO",
        title_ar="مقرر تجريبي شامل",
        title_en="Demo Course",
        short_description_ar="وصف مختصر",
        description_ar="وصف موسع للمقرر",
        target_audience="المبتدئون",
        prerequisites="لا يوجد",
        level=CourseLevel.BEGINNER,
        language="ar",
        duration_hours=10.0,
        passing_grade=60,
        max_attempts=3,
        cover_image="/img/cover.jpg",
        learning_outcomes=["مخرج 1", "مخرج 2", "مخرج 3"],
        accessibility_features=["WCAG 2.1 AA", "تباين عالٍ"],
        nelc_metadata={
            "integrity_policy": True,
            "ip_compliance": "CC BY 4.0",
            "national_compliance": True,
            "syllabus_url": "/syllabus.pdf",
        },
        instructor_id=1,
        status=CourseStatus.APPROVED,
    )
    course.instructor = instructor
    module = Module(course_id=1, title_ar="الوحدة الأولى", order_index=1)
    lesson_video = Lesson(
        module_id=1,
        title_ar="درس فيديو",
        lesson_type=LessonType.VIDEO,
        duration_minutes=10,
        has_transcript=True,
        transcript_text="نص",
        order_index=1,
    )
    lesson_text = Lesson(
        module_id=1,
        title_ar="درس نصي",
        lesson_type=LessonType.TEXT,
        duration_minutes=5,
        order_index=2,
    )
    lesson_quiz_host = Lesson(
        module_id=1,
        title_ar="اختبار الوحدة",
        lesson_type=LessonType.TEXT,
        duration_minutes=5,
        order_index=3,
    )
    quiz = Quiz(
        lesson_id=3,
        title_ar="اختبار",
        passing_score=60,
        max_attempts=3,
        show_correct_answers=True,
    )
    quiz.questions = [
        Question(
            quiz_id=1,
            question_type=QuestionType.MULTIPLE_CHOICE,
            text_ar="س",
            choices=["أ", "ب"],
            correct_answer=["أ"],
            order_index=1,
        ),
        Question(
            quiz_id=1,
            question_type=QuestionType.TRUE_FALSE,
            text_ar="س",
            choices=["نعم", "لا"],
            correct_answer=["نعم"],
            order_index=2,
        ),
    ]
    lesson_quiz_host.quiz = quiz
    module.lessons = [lesson_video, lesson_text, lesson_quiz_host]
    course.modules = [module]
    course.discussions = [
        DiscussionThread(
            course_id=1,
            author_id=1,
            title_ar="ترحيب",
            body_ar="مرحباً بكم في المقرر",
        )
    ]
    course.assignments = []
    course.reviews = []
    return course


def test_empty_course_fails_mandatory_checks():
    course = _empty_course()
    course.modules = []
    course.discussions = []
    course.assignments = []
    course.reviews = []
    course.instructor = None
    report = compliance_report(course)
    assert report["can_publish"] is False
    assert report["by_level"]["mandatory"]["fail"] > 0


def test_good_course_passes_all_mandatory_auto_checks():
    course = _good_course()
    results = evaluate_course(course)
    failed_mandatory = [
        r for r in results
        if r.level == RequirementLevel.MANDATORY.value and r.verdict == "fail"
    ]
    assert failed_mandatory == [], (
        "expected no mandatory auto-check to fail for a complete demo course; "
        f"failed: {[(r.code, r.detail_ar) for r in failed_mandatory]}"
    )


def test_individual_requirement_evaluation_returns_full_metadata():
    course = _good_course()
    req = requirement_by_code("M.01")
    result = evaluate_requirement(req, course)
    assert result.code == "M.01"
    assert result.title_ar
    assert result.verdict in {"pass", "fail", "manual"}


def test_requirements_page_renders(client):
    response = client.get("/nelc/course-requirements")
    assert response.status_code == 200
    assert "متطلبات" in response.text
    assert "إلزامي" in response.text
    assert "اختياري" in response.text
    assert "تميز" in response.text
