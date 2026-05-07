"""NELC course-system requirements (mandatory / optional / excellence).

The Saudi National eLearning Center (NELC, المركز الوطني للتعليم
الإلكتروني) classifies its course-system regulations into three bands:

* ``MANDATORY``  — متطلبات إلزامية: prerequisites for any licensed online
  course offering. Failing any single mandatory requirement blocks the
  course from being published.
* ``OPTIONAL``   — متطلبات اختيارية: strongly encouraged enhancements
  that improve learner experience but are not blocking.
* ``EXCELLENCE`` — متطلبات التميز: high-bar features that distinguish a
  course as exemplary and contribute to the platform's NELC excellence
  rating.

The ``standards`` module already encodes the K-12 *Rubrics of Criteria*
taxonomy (eight domains, 339 criteria, 3-level rubric). This module is
complementary: it focuses specifically on the *course system*
(catalog → modules → lessons → assessments → certification) and exposes
a flat, auditable checklist that course authors and reviewers can act on
directly.

Each requirement carries:

* ``code``  — stable identifier (``M.NN``, ``O.NN``, ``E.NN``)
* ``level`` — :class:`RequirementLevel`
* ``title_ar`` / ``title_en``
* ``description_ar`` — short rationale shown to course authors
* ``nelc_refs`` — optional list of related K-12 criterion codes
* ``auto_check`` — name of a callable in
  :mod:`mooc.services.course_requirements` that can evaluate the
  requirement automatically against a :class:`~mooc.models.Course`
  instance. ``None`` means the check requires manual evidence upload.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


class RequirementLevel(str, enum.Enum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    EXCELLENCE = "excellence"

    @property
    def title_ar(self) -> str:
        return {
            RequirementLevel.MANDATORY: "إلزامي",
            RequirementLevel.OPTIONAL: "اختياري",
            RequirementLevel.EXCELLENCE: "تميز",
        }[self]

    @property
    def title_en(self) -> str:
        return {
            RequirementLevel.MANDATORY: "Mandatory",
            RequirementLevel.OPTIONAL: "Optional",
            RequirementLevel.EXCELLENCE: "Excellence",
        }[self]


@dataclass(frozen=True)
class CourseRequirement:
    code: str
    level: RequirementLevel
    title_ar: str
    title_en: str
    description_ar: str
    nelc_refs: Tuple[str, ...] = field(default_factory=tuple)
    auto_check: Optional[str] = None

    @property
    def is_mandatory(self) -> bool:
        return self.level is RequirementLevel.MANDATORY

    @property
    def is_optional(self) -> bool:
        return self.level is RequirementLevel.OPTIONAL

    @property
    def is_excellence(self) -> bool:
        return self.level is RequirementLevel.EXCELLENCE


def _r(
    code: str,
    level: RequirementLevel,
    title_ar: str,
    title_en: str,
    description_ar: str,
    *nelc_refs: str,
    auto_check: Optional[str] = None,
) -> CourseRequirement:
    return CourseRequirement(
        code=code,
        level=level,
        title_ar=title_ar,
        title_en=title_en,
        description_ar=description_ar,
        nelc_refs=tuple(nelc_refs),
        auto_check=auto_check,
    )


# ---------------------------------------------------------------------------
# Mandatory — متطلبات إلزامية
# ---------------------------------------------------------------------------

_MANDATORY: Tuple[CourseRequirement, ...] = (
    _r(
        "M.01",
        RequirementLevel.MANDATORY,
        "تعريف واضح للمقرر",
        "Clear course identification",
        "يجب أن يحتوي المقرر على رمز فريد، عنوان عربي، ووصف مختصر وموسع.",
        "K.4.3.1",
        auto_check="has_course_identity",
    ),
    _r(
        "M.02",
        RequirementLevel.MANDATORY,
        "مخرجات تعلم قابلة للقياس",
        "Measurable learning outcomes",
        "تُحدَّد مخرجات التعلم بأفعال قابلة للقياس وفق تصنيف بلوم، ولا تقل عن ثلاث مخرجات.",
        "K.4.3.2",
        "K.4.3.3",
        auto_check="has_learning_outcomes",
    ),
    _r(
        "M.03",
        RequirementLevel.MANDATORY,
        "الجمهور المستهدف",
        "Target audience defined",
        "يُحدِّد المقرر فئته العمرية أو المستوى الأكاديمي والاحتياجات المسبقة.",
        "K.4.3.4",
        auto_check="has_target_audience",
    ),
    _r(
        "M.04",
        RequirementLevel.MANDATORY,
        "متطلبات سابقة",
        "Course prerequisites",
        "يُذكر المعارف أو المهارات السابقة المطلوبة، أو يُصرّح بعدم وجودها.",
        "K.4.3.5",
        auto_check="has_prerequisites_field",
    ),
    _r(
        "M.05",
        RequirementLevel.MANDATORY,
        "مدة المقرر",
        "Course duration",
        "تُذكر مدة المقرر بالساعات التعليمية لتمكين الطالب من التخطيط.",
        "K.4.3.6",
        auto_check="has_duration",
    ),
    _r(
        "M.06",
        RequirementLevel.MANDATORY,
        "بنية وحدات منظمة",
        "Structured modules",
        "يُقسَّم المقرر إلى وحدات تعليمية متسلسلة، وكل وحدة إلى دروس.",
        "K.4.1.3",
        auto_check="has_modules_and_lessons",
    ),
    _r(
        "M.07",
        RequirementLevel.MANDATORY,
        "تنوع الوسائط التعليمية",
        "Multiple media types",
        "يستخدم المقرر نوعين أو أكثر من أنواع الوسائط (نص، فيديو، تفاعلي، PDF…).",
        "K.4.1.5",
        auto_check="has_media_variety",
    ),
    _r(
        "M.08",
        RequirementLevel.MANDATORY,
        "ترجمة نصية للفيديو",
        "Video captions / transcripts",
        "كل درس فيديو يحتوي على ترجمة نصية أو نص مكتوب مكافئ.",
        "K.4.2.2",
        "K.7.4.1",
        auto_check="all_videos_have_transcripts",
    ),
    _r(
        "M.09",
        RequirementLevel.MANDATORY,
        "إتاحة وفق WCAG 2.1 AA",
        "WCAG 2.1 AA accessibility",
        "تلتزم واجهة المقرر بمستوى الإتاحة AA من إرشادات WCAG 2.1 (تباين، ARIA، تنقل بلوحة المفاتيح).",
        "K.4.2.1",
        "K.1.4.4",
        auto_check="has_accessibility_features",
    ),
    _r(
        "M.10",
        RequirementLevel.MANDATORY,
        "واجهة عربية RTL",
        "Arabic RTL interface",
        "اللغة الرئيسية للمقرر هي العربية مع دعم كامل للاتجاه من اليمين إلى اليسار.",
        "K.4.1.1",
        auto_check="is_arabic_first",
    ),
    _r(
        "M.11",
        RequirementLevel.MANDATORY,
        "تقييم نهائي للمقرر",
        "Final assessment",
        "يحتوي المقرر على اختبار نهائي أو واجب نهائي يُحدِّد اجتياز المتعلم.",
        "K.4.5.1",
        auto_check="has_final_assessment",
    ),
    _r(
        "M.12",
        RequirementLevel.MANDATORY,
        "درجة نجاح محددة",
        "Defined passing grade",
        "تُذكر درجة الاجتياز الدنيا للمقرر بوضوح.",
        "K.4.5.2",
        auto_check="has_passing_grade",
    ),
    _r(
        "M.13",
        RequirementLevel.MANDATORY,
        "حد أقصى لمحاولات الاختبار",
        "Quiz attempt limit",
        "يُحدَّد عدد المحاولات المسموحة لكل اختبار لمنع سوء الاستخدام.",
        "K.4.5.4",
        auto_check="has_attempt_limit",
    ),
    _r(
        "M.14",
        RequirementLevel.MANDATORY,
        "تغذية راجعة على الاختبارات",
        "Quiz feedback",
        "يُعطى الطالب تغذية راجعة بعد كل اختبار توضح الإجابات الصحيحة أو ملاحظات المعلم.",
        "K.4.5.5",
        auto_check="quizzes_show_feedback",
    ),
    _r(
        "M.15",
        RequirementLevel.MANDATORY,
        "هوية المعلم وسيرته",
        "Instructor identity and bio",
        "تُعرض هوية المعلم وخبرته الأكاديمية والمهنية على صفحة المقرر.",
        "K.5.4.1",
        auto_check="has_instructor",
    ),
    _r(
        "M.16",
        RequirementLevel.MANDATORY,
        "آلية تواصل مع المعلم",
        "Instructor communication channel",
        "يوجد سبيل واضح للتواصل مع المعلم (منتدى نقاش أو بريد).",
        "K.5.2.1",
        auto_check="has_discussion_or_contact",
    ),
    _r(
        "M.17",
        RequirementLevel.MANDATORY,
        "صورة غلاف المقرر",
        "Course cover image",
        "تتوفر صورة غلاف تعبر عن محتوى المقرر في الفهرس وصفحة التفاصيل.",
        "K.4.1.6",
        auto_check="has_cover_image",
    ),
    _r(
        "M.18",
        RequirementLevel.MANDATORY,
        "سياسة الخصوصية وحماية البيانات",
        "Privacy & data-protection policy",
        "تُعرض سياسة الخصوصية وموافقة صريحة من المتعلم قبل التسجيل.",
        "K.1.5.3",
        "K.4.4.1",
        auto_check="platform_has_privacy_policy",
    ),
    _r(
        "M.19",
        RequirementLevel.MANDATORY,
        "النزاهة الأكاديمية ومنع الانتحال",
        "Academic integrity policy",
        "تتضمن سياسات المقرر بنوداً صريحة حول النزاهة الأكاديمية وعقوبات الانتحال.",
        "K.4.4.2",
        auto_check="declares_integrity_policy",
    ),
    _r(
        "M.20",
        RequirementLevel.MANDATORY,
        "حقوق الملكية الفكرية",
        "Intellectual property compliance",
        "يُصرَّح بمصادر المحتوى وحقوق استخدامه (ترخيص أصلي أو CC أو إذن).",
        "K.1.3.3",
        "K.1.3.4",
        auto_check="declares_ip_compliance",
    ),
    _r(
        "M.21",
        RequirementLevel.MANDATORY,
        "الالتزام بالأنظمة الوطنية والقيم",
        "National compliance and values",
        "يحترم محتوى المقرر الأنظمة السعودية والقيم الوطنية والشريعة الإسلامية.",
        "K.1.3.5",
        auto_check="declares_national_compliance",
    ),
    _r(
        "M.22",
        RequirementLevel.MANDATORY,
        "تتبع تقدم المتعلم",
        "Learner progress tracking",
        "تُسجَّل حالة إنجاز كل درس واختبار للمتعلم بشكل قابل للاستعادة.",
        "K.5.5.4",
        auto_check="platform_tracks_progress",
    ),
    _r(
        "M.23",
        RequirementLevel.MANDATORY,
        "تكامل xAPI / SCORM",
        "xAPI / SCORM interoperability",
        "تُسجَّل تفاعلات المقرر بمعيار xAPI، مع دعم استيراد حزم SCORM.",
        "K.1.5.6",
        auto_check="platform_supports_xapi_scorm",
    ),
    _r(
        "M.24",
        RequirementLevel.MANDATORY,
        "شهادة إنجاز قابلة للتحقق",
        "Verifiable completion certificate",
        "تُصدَر للمتعلم شهادة إنجاز برمز تحقق فريد.",
        "K.4.5.8",
        auto_check="platform_issues_certificates",
    ),
    _r(
        "M.25",
        RequirementLevel.MANDATORY,
        "إقامة البيانات داخل المملكة",
        "Saudi data residency",
        "تُخزَّن بيانات المتعلمين في مراكز بيانات داخل المملكة العربية السعودية.",
        "K.1.5.3",
        auto_check="platform_data_residency_sa",
    ),
    _r(
        "M.26",
        RequirementLevel.MANDATORY,
        "سجل تدقيق للأنشطة الإدارية",
        "Administrative audit log",
        "تُسجَّل عمليات الإنشاء والتعديل والاعتماد للمقرر في سجل تدقيق محفوظ.",
        "K.1.6.8",
        auto_check="platform_has_audit_log",
    ),
    _r(
        "M.27",
        RequirementLevel.MANDATORY,
        "اعتماد المقرر قبل النشر",
        "Quality review before publish",
        "لا يُنشَر المقرر إلا بعد اجتياز مراجعة الجودة وفق معايير NELC.",
        "K.1.6.1",
        "K.4.6.1",
        auto_check="course_passed_review",
    ),
    _r(
        "M.28",
        RequirementLevel.MANDATORY,
        "اللغة العربية الفصحى السليمة",
        "Sound Modern Standard Arabic",
        "تُستخدم العربية الفصحى المراجَعة لغوياً في المحتوى التعليمي.",
        "K.4.1.2",
        auto_check=None,
    ),
    _r(
        "M.29",
        RequirementLevel.MANDATORY,
        "خطة المقرر منشورة (Syllabus)",
        "Published syllabus",
        "يحتوي المقرر على خطة دراسية تُذكر فيها الوحدات والتقييمات والجدول الزمني.",
        "K.4.3.7",
        auto_check="has_syllabus_outline",
    ),
    _r(
        "M.30",
        RequirementLevel.MANDATORY,
        "متصفحات وأجهزة مدعومة",
        "Cross-browser/device support",
        "تعمل واجهة المقرر على المتصفحات الحديثة والأجهزة الجوالة بكفاءة.",
        "K.1.5.1",
        auto_check="platform_responsive",
    ),
)


# ---------------------------------------------------------------------------
# Optional — متطلبات اختيارية
# ---------------------------------------------------------------------------

_OPTIONAL: Tuple[CourseRequirement, ...] = (
    _r(
        "O.01",
        RequirementLevel.OPTIONAL,
        "ترجمة إنجليزية للعنوان والوصف",
        "English title and description",
        "إتاحة عنوان ووصف بالإنجليزية لتوسيع نطاق الجمهور.",
        "K.4.1.1",
        auto_check="has_english_title",
    ),
    _r(
        "O.02",
        RequirementLevel.OPTIONAL,
        "ترجمة بلغة الإشارة",
        "Sign-language translation",
        "إتاحة نسخة موازية بلغة الإشارة السعودية لدروس الفيديو الرئيسية.",
        "K.7.4.3",
        auto_check="has_sign_language",
    ),
    _r(
        "O.03",
        RequirementLevel.OPTIONAL,
        "تذييلات صوتية للنصوص",
        "Audio descriptions",
        "توفير وصف صوتي للعناصر البصرية في الفيديوهات.",
        "K.7.4.4",
        auto_check=None,
    ),
    _r(
        "O.04",
        RequirementLevel.OPTIONAL,
        "تقييم تكويني متعدد",
        "Frequent formative assessment",
        "وجود اختبار قصير في كل وحدة تعليمية إضافة للاختبار النهائي.",
        "K.4.5.3",
        auto_check="has_per_module_quiz",
    ),
    _r(
        "O.05",
        RequirementLevel.OPTIONAL,
        "تقييم الأقران",
        "Peer assessment",
        "إتاحة آلية لتقييم الطلاب لأعمال زملائهم وفق معايير محددة.",
        "K.5.3.4",
        auto_check=None,
    ),
    _r(
        "O.06",
        RequirementLevel.OPTIONAL,
        "تحفيز ومسارات إنجاز",
        "Gamification & badges",
        "وجود شارات أو مستويات إنجاز لتحفيز الطالب.",
        "K.5.5.7",
        auto_check=None,
    ),
    _r(
        "O.07",
        RequirementLevel.OPTIONAL,
        "تقدير الوقت لكل درس",
        "Per-lesson time estimate",
        "يُذكر الوقت التقديري لكل درس لتمكين الطالب من إدارة وقته.",
        "K.4.1.7",
        auto_check="lessons_have_duration",
    ),
    _r(
        "O.08",
        RequirementLevel.OPTIONAL,
        "تنوع أنواع الأسئلة",
        "Variety of question types",
        "استخدام أكثر من نوعين من الأسئلة (اختيار، صح/خطأ، مقالية…).",
        "K.4.5.6",
        auto_check="quiz_question_variety",
    ),
    _r(
        "O.09",
        RequirementLevel.OPTIONAL,
        "نسخة قابلة للتنزيل",
        "Downloadable copy",
        "إتاحة ملفات PDF أو موارد قابلة للتنزيل للدراسة دون اتصال.",
        "K.4.1.8",
        auto_check="has_downloadable_resources",
    ),
    _r(
        "O.10",
        RequirementLevel.OPTIONAL,
        "تواريخ مفتوحة (Self-paced)",
        "Self-paced enrollment",
        "إتاحة التسجيل والإنجاز بوتيرة المتعلم دون قيود زمنية صارمة.",
        "K.4.1.9",
        auto_check=None,
    ),
    _r(
        "O.11",
        RequirementLevel.OPTIONAL,
        "بطاقة أداء للمتعلم",
        "Learner analytics dashboard",
        "لوحة معلومات للمتعلم تعرض تقدمه ودرجاته ومتوسط أدائه.",
        "K.5.5.8",
        auto_check="platform_has_student_dashboard",
    ),
    _r(
        "O.12",
        RequirementLevel.OPTIONAL,
        "منتدى نقاش للمقرر",
        "Course discussion forum",
        "وجود منتدى للأسئلة والمناقشات بين الطلاب والمعلم.",
        "K.5.3.1",
        auto_check="has_discussion_forum",
    ),
    _r(
        "O.13",
        RequirementLevel.OPTIONAL,
        "أمثلة وتطبيقات حية",
        "Real-world examples",
        "تضمين دراسات حالة وأمثلة من الواقع السعودي والمحلي.",
        "K.4.1.10",
        auto_check=None,
    ),
    _r(
        "O.14",
        RequirementLevel.OPTIONAL,
        "تذكيرات وإشعارات",
        "Notifications & reminders",
        "إرسال إشعارات للمتعلم عن المهام والمواعيد المتبقية.",
        "K.5.2.5",
        auto_check=None,
    ),
    _r(
        "O.15",
        RequirementLevel.OPTIONAL,
        "تقييم رضا المتعلمين",
        "Learner satisfaction survey",
        "استطلاع رضا في نهاية المقرر لاستخدام نتائجه في التحسين المستمر.",
        "K.1.6.5",
        "K.4.6.2",
        auto_check=None,
    ),
    _r(
        "O.16",
        RequirementLevel.OPTIONAL,
        "روابط لمصادر إثرائية",
        "Enrichment resources",
        "قائمة مصادر إضافية موثقة (كتب، مقالات، مواقع) لكل وحدة.",
        "K.4.1.11",
        auto_check=None,
    ),
    _r(
        "O.17",
        RequirementLevel.OPTIONAL,
        "ترقيم وتسلسل واضح للدروس",
        "Clear lesson numbering",
        "ترقيم الوحدات والدروس بشكل تسلسلي يسهل التنقل.",
        "K.4.1.12",
        auto_check="lessons_are_ordered",
    ),
    _r(
        "O.18",
        RequirementLevel.OPTIONAL,
        "تنبيه على المحتوى الحساس",
        "Sensitive-content notice",
        "تنبيهات قبل عرض محتوى قد يحتاج تنبيهاً (مثل صور علمية حساسة).",
        "K.4.4.3",
        auto_check=None,
    ),
    _r(
        "O.19",
        RequirementLevel.OPTIONAL,
        "تخصيص مسار التعلم",
        "Adaptive learning paths",
        "إمكان توجيه المتعلم لدروس بديلة بناءً على نتائجه.",
        "K.4.5.7",
        auto_check=None,
    ),
    _r(
        "O.20",
        RequirementLevel.OPTIONAL,
        "بحث داخل المقرر",
        "In-course search",
        "إتاحة البحث في عناوين الدروس ومحتواها النصي.",
        "K.4.1.13",
        auto_check=None,
    ),
)


# ---------------------------------------------------------------------------
# Excellence — متطلبات التميز
# ---------------------------------------------------------------------------

_EXCELLENCE: Tuple[CourseRequirement, ...] = (
    _r(
        "E.01",
        RequirementLevel.EXCELLENCE,
        "اعتماد دولي إضافي",
        "Additional international accreditation",
        "حصول المقرر على اعتماد دولي معترف به (Quality Matters / iNACOL / OpenupEd).",
        "K.4.6.4",
        auto_check=None,
    ),
    _r(
        "E.02",
        RequirementLevel.EXCELLENCE,
        "مشروع نهائي تطبيقي",
        "Capstone project",
        "وجود مشروع تطبيقي نهائي يُقيَّم وفق رُبريك متعدد المعايير.",
        "K.4.5.9",
        auto_check="has_capstone_assignment",
    ),
    _r(
        "E.03",
        RequirementLevel.EXCELLENCE,
        "محاضرات تفاعلية مباشرة",
        "Live interactive sessions",
        "وجود جلسات حية متزامنة مع المعلم على فترات منتظمة.",
        "K.8.1.1",
        auto_check="has_live_sessions",
    ),
    _r(
        "E.04",
        RequirementLevel.EXCELLENCE,
        "مختبرات افتراضية أو محاكاة",
        "Virtual labs or simulations",
        "تضمين محاكيات أو مختبرات افتراضية تتيح للمتعلم التجريب الآمن.",
        "K.4.1.14",
        auto_check="has_interactive_labs",
    ),
    _r(
        "E.05",
        RequirementLevel.EXCELLENCE,
        "تجارب AR / VR",
        "AR/VR experiences",
        "إتاحة وحدة تعليمية أو أكثر بتقنية الواقع المعزز/الافتراضي.",
        "K.4.1.15",
        auto_check=None,
    ),
    _r(
        "E.06",
        RequirementLevel.EXCELLENCE,
        "ترجمة تلقائية لأكثر من لغة",
        "Multilingual translations",
        "إتاحة الترجمة لأكثر من لغة إضافة للعربية والإنجليزية.",
        "K.4.2.5",
        auto_check=None,
    ),
    _r(
        "E.07",
        RequirementLevel.EXCELLENCE,
        "اعتماد ساعات تدريبية رسمية",
        "Formal CEU/CPD credit",
        "اعتماد المقرر لساعات تطوير مهني (CPD) من جهة معترف بها.",
        "K.4.6.5",
        auto_check=None,
    ),
    _r(
        "E.08",
        RequirementLevel.EXCELLENCE,
        "ذكاء اصطناعي مساعد",
        "AI tutoring assistant",
        "وجود مساعد ذكي يجيب أسئلة المتعلمين على مدار الساعة.",
        "K.5.5.9",
        auto_check=None,
    ),
    _r(
        "E.09",
        RequirementLevel.EXCELLENCE,
        "تحليلات تنبؤية للنجاح",
        "Predictive success analytics",
        "تحليلات تنبؤية تنبه المعلم بالطلاب المعرضين للتعثر.",
        "K.1.6.7",
        auto_check=None,
    ),
    _r(
        "E.10",
        RequirementLevel.EXCELLENCE,
        "مجتمع خريجين نشط",
        "Active alumni community",
        "وجود مجتمع للخريجين يستمر بعد إكمال المقرر.",
        "K.5.3.6",
        auto_check=None,
    ),
    _r(
        "E.11",
        RequirementLevel.EXCELLENCE,
        "محتوى مفتوح المصدر (OER)",
        "Open educational resources",
        "نشر محتوى المقرر بترخيص Creative Commons.",
        "K.1.3.3",
        auto_check=None,
    ),
    _r(
        "E.12",
        RequirementLevel.EXCELLENCE,
        "مقابلات مع خبراء",
        "Expert interviews",
        "تضمين مقابلات حصرية مع خبراء في مجال المقرر.",
        "K.7.2.5",
        auto_check=None,
    ),
    _r(
        "E.13",
        RequirementLevel.EXCELLENCE,
        "قياس الأثر الوظيفي",
        "Job-placement impact measurement",
        "قياس أثر المقرر على المسار الوظيفي للخريجين.",
        "K.1.6.6",
        auto_check=None,
    ),
    _r(
        "E.14",
        RequirementLevel.EXCELLENCE,
        "شراكات مؤسسية",
        "Institutional partnerships",
        "شراكات مع جامعات أو جهات حكومية أو شركات لاعتماد المقرر.",
        "K.6.6.2",
        auto_check=None,
    ),
    _r(
        "E.15",
        RequirementLevel.EXCELLENCE,
        "شهادات رقمية موقعة (Verifiable Credentials)",
        "Digitally signed credentials",
        "إصدار الشهادات بتوقيع رقمي/PKI ومعيار W3C VC قابل للتحقق آلياً.",
        "K.1.5.3",
        auto_check=None,
    ),
)


# ---------------------------------------------------------------------------
# Public catalog
# ---------------------------------------------------------------------------


COURSE_REQUIREMENTS: Tuple[CourseRequirement, ...] = (
    _MANDATORY + _OPTIONAL + _EXCELLENCE
)


_BY_CODE: Dict[str, CourseRequirement] = {r.code: r for r in COURSE_REQUIREMENTS}


def all_requirements() -> Iterable[CourseRequirement]:
    return COURSE_REQUIREMENTS


def requirements_by_level(
    level: RequirementLevel,
) -> Tuple[CourseRequirement, ...]:
    return tuple(r for r in COURSE_REQUIREMENTS if r.level is level)


def mandatory_requirements() -> Tuple[CourseRequirement, ...]:
    return _MANDATORY


def optional_requirements() -> Tuple[CourseRequirement, ...]:
    return _OPTIONAL


def excellence_requirements() -> Tuple[CourseRequirement, ...]:
    return _EXCELLENCE


def requirement_by_code(code: str) -> Optional[CourseRequirement]:
    return _BY_CODE.get(code)


def requirements_summary() -> Dict[str, int]:
    return {
        "mandatory": len(_MANDATORY),
        "optional": len(_OPTIONAL),
        "excellence": len(_EXCELLENCE),
        "total": len(COURSE_REQUIREMENTS),
    }


__all__ = [
    "COURSE_REQUIREMENTS",
    "CourseRequirement",
    "RequirementLevel",
    "all_requirements",
    "excellence_requirements",
    "mandatory_requirements",
    "optional_requirements",
    "requirement_by_code",
    "requirements_by_level",
    "requirements_summary",
]
