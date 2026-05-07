"""Evaluator for NELC course-system requirements.

Given a :class:`~mooc.models.Course` (or just its metadata), this module
returns a per-requirement compliance verdict:

* ``"pass"``    — the requirement is satisfied
* ``"fail"``    — the requirement is not satisfied
* ``"manual"``  — automatic check is not possible; a reviewer must verify
                  manually using uploaded evidence

The catalog is defined in :mod:`mooc.nelc.course_requirements`.

The evaluator deliberately favours conservative auto-detection: when an
artefact (e.g. an English title) is partially present, the auto check is
treated as failing so course authors are nudged to fill it in.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional

from ..config import get_settings
from ..models import Course, CourseStatus, LessonType, QuestionType, ReviewState
from ..nelc.course_requirements import (
    COURSE_REQUIREMENTS,
    CourseRequirement,
    RequirementLevel,
    excellence_requirements,
    mandatory_requirements,
    optional_requirements,
)


_VERDICT_PASS = "pass"
_VERDICT_FAIL = "fail"
_VERDICT_MANUAL = "manual"


@dataclass
class RequirementResult:
    code: str
    level: str
    title_ar: str
    title_en: str
    description_ar: str
    nelc_refs: List[str]
    auto_check: Optional[str]
    verdict: str
    detail_ar: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _course_lessons(course: Course):
    for module in course.modules or []:
        for lesson in module.lessons or []:
            yield lesson


def _course_quizzes(course: Course):
    for lesson in _course_lessons(course):
        if lesson.quiz is not None:
            yield lesson.quiz


# ---------------------------------------------------------------------------
# Auto-check implementations
# ---------------------------------------------------------------------------


def has_course_identity(course: Course) -> RequirementResult:
    ok = bool(course.code and course.title_ar and course.short_description_ar and course.description_ar)
    return _verdict(ok, "اكتمال الرمز والعنوان والوصف", "بعض الحقول الأساسية ناقصة")


def has_learning_outcomes(course: Course) -> RequirementResult:
    outcomes = course.learning_outcomes or []
    ok = isinstance(outcomes, list) and len(outcomes) >= 3
    return _verdict(
        ok,
        f"يوجد {len(outcomes)} مخرجات تعلم محددة",
        "يجب توفر ثلاث مخرجات تعلم على الأقل",
    )


def has_target_audience(course: Course) -> RequirementResult:
    ok = bool((course.target_audience or "").strip())
    return _verdict(ok, "تم تحديد الجمهور المستهدف", "حقل الجمهور المستهدف فارغ")


def has_prerequisites_field(course: Course) -> RequirementResult:
    ok = course.prerequisites is not None
    return _verdict(ok, "حقل المتطلبات السابقة موثَّق", "حقل المتطلبات السابقة غير موثق")


def has_duration(course: Course) -> RequirementResult:
    ok = (course.duration_hours or 0) > 0
    return _verdict(ok, f"المدة: {course.duration_hours} ساعة", "لم تُحدَّد مدة المقرر")


def has_modules_and_lessons(course: Course) -> RequirementResult:
    modules = course.modules or []
    lessons_total = sum(len(m.lessons or []) for m in modules)
    ok = len(modules) >= 1 and lessons_total >= 3
    return _verdict(
        ok,
        f"{len(modules)} وحدة و{lessons_total} درس",
        "يجب وجود وحدة واحدة على الأقل بثلاثة دروس",
    )


def has_media_variety(course: Course) -> RequirementResult:
    types = {l.lesson_type for l in _course_lessons(course)}
    ok = len(types) >= 2
    return _verdict(
        ok,
        f"تم استخدام {len(types)} نوع/أنواع وسائط",
        "يجب التنويع بين نوعين على الأقل من أنواع الدروس",
    )


def all_videos_have_transcripts(course: Course) -> RequirementResult:
    videos = [l for l in _course_lessons(course) if l.lesson_type == LessonType.VIDEO]
    if not videos:
        return RequirementResult(
            code="", level="", title_ar="", title_en="", description_ar="",
            nelc_refs=[], auto_check=None,
            verdict=_VERDICT_PASS,
            detail_ar="لا توجد دروس فيديو",
        )
    missing = [l for l in videos if not (l.has_transcript or l.transcript_text or l.captions_url)]
    ok = len(missing) == 0
    return _verdict(
        ok,
        f"جميع الفيديوهات ({len(videos)}) لها ترجمة نصية",
        f"عدد {len(missing)} درس فيديو بدون ترجمة نصية",
    )


def has_accessibility_features(course: Course) -> RequirementResult:
    features = course.accessibility_features or []
    ok = bool(features)
    return _verdict(
        ok,
        f"خصائص الإتاحة: {', '.join(features) or '—'}",
        "لم تُسجَّل خصائص إتاحة للمقرر",
    )


def is_arabic_first(course: Course) -> RequirementResult:
    ok = (course.language or "ar") == "ar" and bool(course.title_ar)
    return _verdict(ok, "اللغة الأساسية عربية", "اللغة الأساسية ليست العربية")


def has_final_assessment(course: Course) -> RequirementResult:
    quiz_count = sum(1 for _ in _course_quizzes(course))
    has_assignment = False
    # Avoid loading via attribute that may not be populated; courses route
    # exposes `assignments` only when loaded — this helper accepts either.
    assignments = getattr(course, "assignments", None)
    if assignments is not None:
        has_assignment = len(list(assignments)) > 0
    ok = quiz_count >= 1 or has_assignment
    return _verdict(
        ok,
        f"{quiz_count} اختبار/اختبارات للمقرر",
        "لا يوجد اختبار نهائي أو واجب نهائي",
    )


def has_passing_grade(course: Course) -> RequirementResult:
    ok = (course.passing_grade or 0) > 0
    return _verdict(ok, f"درجة النجاح: {course.passing_grade}", "درجة النجاح غير محددة")


def has_attempt_limit(course: Course) -> RequirementResult:
    ok = (course.max_attempts or 0) > 0
    return _verdict(
        ok,
        f"الحد الأقصى للمحاولات: {course.max_attempts}",
        "لم يُحدَّد عدد محاولات الاختبار",
    )


def quizzes_show_feedback(course: Course) -> RequirementResult:
    quizzes = list(_course_quizzes(course))
    if not quizzes:
        return _verdict(False, "", "لا يوجد اختبارات لتقييم التغذية الراجعة")
    bad = [q for q in quizzes if not q.show_correct_answers]
    ok = len(bad) == 0
    return _verdict(
        ok,
        "جميع الاختبارات تُظهر تغذية راجعة للطالب",
        f"{len(bad)} اختبار/اختبارات لا تُظهر إجابات صحيحة",
    )


def has_instructor(course: Course) -> RequirementResult:
    ok = bool(course.instructor_id and course.instructor)
    return _verdict(
        ok,
        f"المعلم: {course.instructor.display_name if course.instructor else '—'}",
        "لم يُربَط المقرر بمعلم",
    )


def has_discussion_or_contact(course: Course) -> RequirementResult:
    discussions = course.discussions or []
    ok = len(discussions) > 0
    return _verdict(
        ok,
        f"{len(discussions)} موضوع/مواضيع نقاش",
        "لا يوجد منتدى نقاش لهذا المقرر — أنشئ موضوع ترحيب",
    )


def has_cover_image(course: Course) -> RequirementResult:
    ok = bool((course.cover_image or "").strip())
    return _verdict(ok, "صورة الغلاف موجودة", "لم تُرفَع صورة غلاف")


def platform_has_privacy_policy(course: Course) -> RequirementResult:
    return _verdict(
        True,
        "تتوفر سياسة الخصوصية في /privacy وتُطلب الموافقة عند التسجيل",
        "",
    )


def declares_integrity_policy(course: Course) -> RequirementResult:
    metadata = course.nelc_metadata or {}
    ok = bool(metadata.get("integrity_policy"))
    return _verdict(
        ok,
        "تم الإقرار بسياسة النزاهة الأكاديمية",
        "لم يتم تأكيد سياسة النزاهة الأكاديمية في بيانات المقرر",
    )


def declares_ip_compliance(course: Course) -> RequirementResult:
    metadata = course.nelc_metadata or {}
    ok = bool(metadata.get("ip_compliance"))
    return _verdict(
        ok,
        "تم الإقرار بحقوق الملكية الفكرية",
        "لم يُذكر مصدر الحقوق الفكرية في بيانات المقرر",
    )


def declares_national_compliance(course: Course) -> RequirementResult:
    metadata = course.nelc_metadata or {}
    ok = bool(metadata.get("national_compliance"))
    return _verdict(
        ok,
        "تم تأكيد التوافق مع الأنظمة الوطنية",
        "لم يُؤكَّد التوافق مع الأنظمة الوطنية والقيم",
    )


def platform_tracks_progress(course: Course) -> RequirementResult:
    return _verdict(True, "جدول lesson_progress يسجل تقدم كل طالب", "")


def platform_supports_xapi_scorm(course: Course) -> RequirementResult:
    return _verdict(
        True,
        "المنصة تستوعب xAPI وSCORM (راجع /xapi/* وحزم الدروس)",
        "",
    )


def platform_issues_certificates(course: Course) -> RequirementResult:
    return _verdict(
        True,
        "تُصدَر شهادات بكود تحقق فريد على /verify-certificate",
        "",
    )


def platform_data_residency_sa(course: Course) -> RequirementResult:
    region = (get_settings().data_residency_region or "").lower()
    ok = region.startswith("sa")
    return _verdict(
        ok,
        f"إقامة البيانات: {region}",
        f"إقامة البيانات الحالية ({region}) خارج المملكة",
    )


def platform_has_audit_log(course: Course) -> RequirementResult:
    return _verdict(True, "جدول audit_log يسجل الأحداث الإدارية", "")


def course_passed_review(course: Course) -> RequirementResult:
    if course.status in {CourseStatus.PUBLISHED, CourseStatus.APPROVED}:
        return _verdict(True, "اعتُمد المقرر بعد مراجعة الجودة", "")
    reviews = course.reviews or []
    passed = [r for r in reviews if r.state == ReviewState.PASSED]
    if passed:
        return _verdict(True, "توجد مراجعة جودة ناجحة", "")
    return _verdict(False, "", "لا توجد مراجعة جودة ناجحة بعد")


def has_syllabus_outline(course: Course) -> RequirementResult:
    metadata = course.nelc_metadata or {}
    has_syllabus = bool(metadata.get("syllabus_url") or metadata.get("syllabus"))
    has_modules = bool(course.modules)
    ok = has_syllabus or has_modules
    return _verdict(
        ok,
        "بنية الوحدات تُمثل خطة المقرر" if has_modules else "تم رفع خطة المقرر",
        "لا توجد خطة مقرر منشورة (syllabus) ولا وحدات تعليمية",
    )


def platform_responsive(course: Course) -> RequirementResult:
    return _verdict(
        True,
        "تستخدم القوالب CSS متجاوب ومتوافق مع الأجهزة الصغيرة",
        "",
    )


def has_english_title(course: Course) -> RequirementResult:
    ok = bool((course.title_en or "").strip())
    return _verdict(ok, "العنوان الإنجليزي متوفر", "لم يُضف العنوان الإنجليزي")


def has_sign_language(course: Course) -> RequirementResult:
    videos = [l for l in _course_lessons(course) if l.lesson_type == LessonType.VIDEO]
    if not videos:
        return _verdict(False, "", "لا يوجد فيديوهات يمكن إضافة لغة الإشارة لها")
    with_sign = [l for l in videos if l.has_sign_language]
    ok = len(with_sign) > 0
    return _verdict(
        ok,
        f"{len(with_sign)} درس فيديو مزود بترجمة لغة الإشارة",
        "لا يوجد ترجمة بلغة الإشارة لأي درس فيديو",
    )


def has_per_module_quiz(course: Course) -> RequirementResult:
    modules = course.modules or []
    if not modules:
        return _verdict(False, "", "لا توجد وحدات لتقييمها")
    missing = []
    for m in modules:
        has_q = any(l.quiz for l in (m.lessons or []))
        if not has_q:
            missing.append(m.title_ar)
    ok = len(missing) == 0
    return _verdict(
        ok,
        "كل وحدة تعليمية تحتوي اختباراً تكوينياً",
        f"وحدات بدون اختبار: {'، '.join(missing[:3])}{'…' if len(missing) > 3 else ''}",
    )


def lessons_have_duration(course: Course) -> RequirementResult:
    lessons = list(_course_lessons(course))
    if not lessons:
        return _verdict(False, "", "لا توجد دروس")
    missing = [l for l in lessons if (l.duration_minutes or 0) <= 0]
    ok = len(missing) == 0
    return _verdict(
        ok,
        "كل الدروس تحمل تقدير مدة",
        f"{len(missing)} درس بدون تقدير وقت",
    )


def quiz_question_variety(course: Course) -> RequirementResult:
    types = set()
    for q in _course_quizzes(course):
        for question in q.questions or []:
            types.add(question.question_type)
    ok = len(types) >= 2
    return _verdict(
        ok,
        f"{len(types)} نوع/أنواع أسئلة مستخدمة",
        "يجب التنويع باستخدام نوعين على الأقل من الأسئلة",
    )


def has_downloadable_resources(course: Course) -> RequirementResult:
    has_pdf = any(l.lesson_type == LessonType.PDF for l in _course_lessons(course))
    return _verdict(
        has_pdf,
        "يوجد دروس PDF قابلة للتنزيل",
        "لا يوجد موارد PDF قابلة للتنزيل",
    )


def platform_has_student_dashboard(course: Course) -> RequirementResult:
    return _verdict(True, "لوحة الطالب متاحة على /student", "")


def has_discussion_forum(course: Course) -> RequirementResult:
    threads = course.discussions or []
    ok = len(threads) > 0
    return _verdict(
        ok,
        f"{len(threads)} موضوع نقاش",
        "لم تُنشَأ أي مواضيع نقاش بعد",
    )


def lessons_are_ordered(course: Course) -> RequirementResult:
    for module in course.modules or []:
        indices = [l.order_index for l in (module.lessons or [])]
        if indices != sorted(set(indices)):
            return _verdict(False, "", f"ترتيب الدروس غير سليم في وحدة: {module.title_ar}")
    return _verdict(True, "ترقيم الدروس متسلسل", "")


def has_capstone_assignment(course: Course) -> RequirementResult:
    assignments = getattr(course, "assignments", None) or []
    has_capstone = any("مشروع" in (a.title_ar or "") or "نهائي" in (a.title_ar or "") for a in assignments)
    return _verdict(
        has_capstone,
        "يوجد واجب نهائي / مشروع تخرج",
        "لا يوجد مشروع نهائي/تخرج معرف",
    )


def has_live_sessions(course: Course) -> RequirementResult:
    has_live = any(l.lesson_type == LessonType.LIVE for l in _course_lessons(course))
    return _verdict(has_live, "يوجد جلسات حية مجدولة", "لا توجد جلسات مباشرة (LIVE)")


def has_interactive_labs(course: Course) -> RequirementResult:
    has_int = any(l.lesson_type == LessonType.INTERACTIVE for l in _course_lessons(course))
    return _verdict(has_int, "يوجد دروس تفاعلية", "لا توجد دروس تفاعلية / محاكاة")


def _verdict(ok: bool, ok_detail: str, fail_detail: str) -> RequirementResult:
    """Build a partial RequirementResult; the caller fills code/level/etc."""
    return RequirementResult(
        code="",
        level="",
        title_ar="",
        title_en="",
        description_ar="",
        nelc_refs=[],
        auto_check=None,
        verdict=_VERDICT_PASS if ok else _VERDICT_FAIL,
        detail_ar=ok_detail if ok else fail_detail,
    )


_AUTO_CHECKS = {
    "has_course_identity": has_course_identity,
    "has_learning_outcomes": has_learning_outcomes,
    "has_target_audience": has_target_audience,
    "has_prerequisites_field": has_prerequisites_field,
    "has_duration": has_duration,
    "has_modules_and_lessons": has_modules_and_lessons,
    "has_media_variety": has_media_variety,
    "all_videos_have_transcripts": all_videos_have_transcripts,
    "has_accessibility_features": has_accessibility_features,
    "is_arabic_first": is_arabic_first,
    "has_final_assessment": has_final_assessment,
    "has_passing_grade": has_passing_grade,
    "has_attempt_limit": has_attempt_limit,
    "quizzes_show_feedback": quizzes_show_feedback,
    "has_instructor": has_instructor,
    "has_discussion_or_contact": has_discussion_or_contact,
    "has_cover_image": has_cover_image,
    "platform_has_privacy_policy": platform_has_privacy_policy,
    "declares_integrity_policy": declares_integrity_policy,
    "declares_ip_compliance": declares_ip_compliance,
    "declares_national_compliance": declares_national_compliance,
    "platform_tracks_progress": platform_tracks_progress,
    "platform_supports_xapi_scorm": platform_supports_xapi_scorm,
    "platform_issues_certificates": platform_issues_certificates,
    "platform_data_residency_sa": platform_data_residency_sa,
    "platform_has_audit_log": platform_has_audit_log,
    "course_passed_review": course_passed_review,
    "has_syllabus_outline": has_syllabus_outline,
    "platform_responsive": platform_responsive,
    "has_english_title": has_english_title,
    "has_sign_language": has_sign_language,
    "has_per_module_quiz": has_per_module_quiz,
    "lessons_have_duration": lessons_have_duration,
    "quiz_question_variety": quiz_question_variety,
    "has_downloadable_resources": has_downloadable_resources,
    "platform_has_student_dashboard": platform_has_student_dashboard,
    "has_discussion_forum": has_discussion_forum,
    "lessons_are_ordered": lessons_are_ordered,
    "has_capstone_assignment": has_capstone_assignment,
    "has_live_sessions": has_live_sessions,
    "has_interactive_labs": has_interactive_labs,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_requirement(
    requirement: CourseRequirement, course: Course
) -> RequirementResult:
    if requirement.auto_check and requirement.auto_check in _AUTO_CHECKS:
        partial = _AUTO_CHECKS[requirement.auto_check](course)
    else:
        partial = RequirementResult(
            code="",
            level="",
            title_ar="",
            title_en="",
            description_ar="",
            nelc_refs=[],
            auto_check=None,
            verdict=_VERDICT_MANUAL,
            detail_ar="يحتاج هذا المعيار مراجعة يدوية ورفع دليل",
        )
    return RequirementResult(
        code=requirement.code,
        level=requirement.level.value,
        title_ar=requirement.title_ar,
        title_en=requirement.title_en,
        description_ar=requirement.description_ar,
        nelc_refs=list(requirement.nelc_refs),
        auto_check=requirement.auto_check,
        verdict=partial.verdict,
        detail_ar=partial.detail_ar,
    )


def evaluate_course(course: Course) -> List[RequirementResult]:
    return [evaluate_requirement(r, course) for r in COURSE_REQUIREMENTS]


def compliance_report(course: Course) -> Dict[str, object]:
    """Aggregate verdicts into a per-level report."""
    results = evaluate_course(course)
    by_level: Dict[str, Dict[str, int]] = {
        RequirementLevel.MANDATORY.value: _empty_counters(len(mandatory_requirements())),
        RequirementLevel.OPTIONAL.value: _empty_counters(len(optional_requirements())),
        RequirementLevel.EXCELLENCE.value: _empty_counters(len(excellence_requirements())),
    }
    for r in results:
        bucket = by_level[r.level]
        bucket[r.verdict] = bucket.get(r.verdict, 0) + 1

    mandatory = by_level[RequirementLevel.MANDATORY.value]
    can_publish = mandatory.get(_VERDICT_FAIL, 0) == 0

    def _percent(bucket: Dict[str, int]) -> float:
        total = bucket["total"]
        if total == 0:
            return 0.0
        passed = bucket.get(_VERDICT_PASS, 0)
        manual = bucket.get(_VERDICT_MANUAL, 0)
        # Manual checks count as half until a reviewer signs them off.
        return round((passed + manual * 0.5) / total * 100.0, 2)

    return {
        "results": [r.to_dict() for r in results],
        "by_level": {
            level: {
                **counts,
                "percent": _percent(counts),
            }
            for level, counts in by_level.items()
        },
        "can_publish": can_publish,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.verdict == _VERDICT_PASS),
            "failed": sum(1 for r in results if r.verdict == _VERDICT_FAIL),
            "manual": sum(1 for r in results if r.verdict == _VERDICT_MANUAL),
        },
    }


def _empty_counters(total: int) -> Dict[str, int]:
    return {
        _VERDICT_PASS: 0,
        _VERDICT_FAIL: 0,
        _VERDICT_MANUAL: 0,
        "total": total,
    }


__all__ = [
    "RequirementResult",
    "compliance_report",
    "evaluate_course",
    "evaluate_requirement",
]
