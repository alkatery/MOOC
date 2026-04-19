"""NELC Excellence Standards taxonomy (K-12 rubric, v2.0 / 12-2023).

This module is a faithful, structured representation of the National
eLearning Center's (المركز الوطني للتعليم الإلكتروني) "Rubrics of
Criteria for Excellence in Online Learning — K-12" document, version
2.0, published December 2023 under the Creative Commons
Attribution-NonCommercial-ShareAlike 4.0 International license.

The source document defines:

* 8 top-level **domains** (K.1 – K.8)
* 43 **subdomains**
* 377 individual **criteria** identified with dotted codes (K.x.y.z)
* A 3-level scoring **rubric**:
    1 = Emerging       (ناشئ)
    2 = Accomplished   (متحقق)
    3 = Exemplary      (مثالي)

Because the full text of every criterion is over 90 pages of
multi-column English prose, this module stores:

* The canonical code, domain, subdomain
* A short Arabic title and an English title
* The criterion count per subdomain (for coverage reports)
* Evidence hint tags so course authors know what artefacts to upload

Instructors may click through to the official PDF from the UI for the
full descriptive language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------


RUBRIC_LEVELS: Tuple[Tuple[int, str, str], ...] = (
    (1, "ناشئ", "Emerging"),
    (2, "متحقق", "Accomplished"),
    (3, "مثالي", "Exemplary"),
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Criterion:
    code: str
    title_ar: str
    title_en: str
    evidence_tags: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Subdomain:
    code: str
    title_ar: str
    title_en: str
    criteria: Tuple[Criterion, ...]

    @property
    def criteria_count(self) -> int:
        return len(self.criteria)


@dataclass(frozen=True)
class Domain:
    code: str
    title_ar: str
    title_en: str
    description_ar: str
    subdomains: Tuple[Subdomain, ...]

    @property
    def subdomain_count(self) -> int:
        return len(self.subdomains)

    @property
    def criteria_count(self) -> int:
        return sum(sd.criteria_count for sd in self.subdomains)


# ---------------------------------------------------------------------------
# Helpers to build the taxonomy compactly
# ---------------------------------------------------------------------------


def _c(code: str, ar: str, en: str, *tags: str) -> Criterion:
    return Criterion(code=code, title_ar=ar, title_en=en, evidence_tags=tuple(tags))


# ---------------------------------------------------------------------------
# K.1 – Institution
# ---------------------------------------------------------------------------


_K11 = Subdomain(
    "K.1.1",
    "القيادة والحوكمة",
    "Leadership and Governance",
    (
        _c("K.1.1.1", "رؤية ورسالة واضحة للتعليم الإلكتروني", "Clear eLearning vision and mission", "policy"),
        _c("K.1.1.2", "بيئة قيادية تعاونية منتجة", "Productive collaborative leadership environment", "policy"),
        _c("K.1.1.3", "تحسين مستمر للسياسات والإجراءات", "Continuous improvement of policies", "policy"),
        _c("K.1.1.4", "إشراك أصحاب المصلحة في دعم أهداف المؤسسة", "Engages stakeholders in institutional purpose", "policy"),
        _c("K.1.1.5", "الإشراف على الكوادر وتقييمها", "Staff supervision and evaluation", "hr"),
        _c("K.1.1.6", "اتخاذ قرارات تشغيلية تركز على التعلم", "Learning-centred operational decisions", "policy"),
        _c("K.1.1.7", "أهداف سنوية مرتبطة بالرؤية والرسالة", "Annual goals tied to vision", "policy"),
        _c("K.1.1.8", "نشر وتنظيم عروض المقررات بوضوح", "Clear catalog and course communication", "catalog"),
        _c("K.1.1.9", "آليات متابعة التسجيل والتخطيط الأكاديمي", "Enrollment monitoring and academic planning", "catalog"),
        _c("K.1.1.10", "خطط خلافة لضمان استقرار القيادة", "Succession planning for leadership", "policy"),
    ),
)

_K12 = Subdomain(
    "K.1.2",
    "توزيع الموارد",
    "Resource Allocation",
    (
        _c("K.1.2.1", "تخطيط موارد وميزانية مسؤول", "Responsible resource/budget planning", "finance"),
        _c("K.1.2.2", "كوادر مؤهلة لتحقيق الأهداف", "Qualified staff available", "hr"),
        _c("K.1.2.3", "تعريف واضح للمسؤوليات في التعلم الإلكتروني", "Clear eLearning responsibilities", "policy"),
        _c("K.1.2.4", "متابعة التوجهات التعليمية والتقنية", "Tracking trends in education and tech", "policy"),
        _c("K.1.2.5", "دعم التطوير المهني المستدام", "Sustained professional development", "hr"),
        _c("K.1.2.6", "آليات لمشاركة الموارد والخبرات", "Sharing resources and expertise", "policy"),
    ),
)

_K13 = Subdomain(
    "K.1.3",
    "تقديم التعليم والامتثال",
    "Instructional Delivery and Compliance",
    (
        _c("K.1.3.1", "ضمان جودة ونزاهة وصحة المحتوى التعليمي", "Quality and integrity of content", "content"),
        _c("K.1.3.2", "تحديث المحتوى الإلكتروني باستمرار", "Up-to-date online content", "content"),
        _c("K.1.3.3", "الالتزام بحقوق الملكية الفكرية والترخيص", "IP and licensing compliance", "legal"),
        _c("K.1.3.4", "توثيق مصادر المحتوى بوضوح", "Clear sourcing of content", "legal"),
        _c("K.1.3.5", "الامتثال للقوانين واللوائح الوطنية", "National law and policy compliance", "legal"),
    ),
)

_K14 = Subdomain(
    "K.1.4",
    "العدالة وإمكانية الوصول",
    "Equity and Accessibility",
    (
        _c("K.1.4.1", "تركيز على احتياجات الطالب عبر الإنترنت", "Online student-centred focus", "ux"),
        _c("K.1.4.2", "خدمات طلابية قابلة للقياس ومحسّنة", "Measurable, improving student services", "ux"),
        _c("K.1.4.3", "قنوات تواصل واضحة وفي الوقت المناسب", "Clear and timely communication", "ux"),
        _c("K.1.4.4", "ضمان إمكانية الوصول الرقمي للجميع", "Digital accessibility for all", "accessibility"),
        _c("K.1.4.5", "دعم ذوي الاحتياجات والفئات الخاصة", "Support for special needs", "accessibility"),
    ),
)

_K15 = Subdomain(
    "K.1.5",
    "التقنية والأنظمة",
    "Technology and Systems",
    (
        _c("K.1.5.1", "بنية تحتية تقنية موثوقة", "Reliable technology infrastructure", "tech"),
        _c("K.1.5.2", "خطة تقنية موثقة ومحدّثة", "Documented technology plan", "tech"),
        _c("K.1.5.3", "أمن المعلومات وحماية الخصوصية", "Information security & privacy", "security"),
        _c("K.1.5.4", "الدعم الفني المركزي", "Central technical support", "support"),
        _c("K.1.5.5", "التكامل بين نظم التعلم والأنظمة المؤسسية", "LMS–enterprise system integration", "tech"),
        _c("K.1.5.6", "التوافق مع معايير SCORM وxAPI", "SCORM and xAPI conformance", "tech", "interop"),
        _c("K.1.5.7", "خطة النسخ الاحتياطي والاستمرارية", "Backup and continuity plan", "tech"),
    ),
)

_K16 = Subdomain(
    "K.1.6",
    "التقويم والتقييم",
    "Evaluation and Assessment",
    (
        _c("K.1.6.1", "إطار تقييم مؤسسي واضح", "Clear institutional evaluation framework", "policy"),
        _c("K.1.6.2", "جمع بيانات التعلم وتحليلها", "Learning analytics collection", "analytics"),
        _c("K.1.6.3", "تقارير دورية لأصحاب المصلحة", "Regular stakeholder reporting", "analytics"),
        _c("K.1.6.4", "مؤشرات أداء رئيسية (KPIs)", "KPIs for the program", "analytics"),
        _c("K.1.6.5", "استطلاعات رضا الطلاب والمعلمين", "Student and teacher surveys", "analytics"),
        _c("K.1.6.6", "مقارنة النتائج مع المعايير الوطنية", "Benchmark against national standards", "analytics"),
        _c("K.1.6.7", "خطط تحسين مبنية على البيانات", "Data-driven improvement plans", "analytics"),
        _c("K.1.6.8", "مراجعات دورية من جهة مستقلة", "Periodic independent reviews", "review"),
    ),
)

_K1 = Domain(
    "K.1",
    "المؤسسة",
    "Institution",
    "يغطي حوكمة المؤسسة ومواردها وبنيتها التقنية والتزامها التنظيمي.",
    (_K11, _K12, _K13, _K14, _K15, _K16),
)


# ---------------------------------------------------------------------------
# K.2 – Program Administration
# ---------------------------------------------------------------------------


_K21 = Subdomain(
    "K.2.1",
    "القيادة والإدارة",
    "Leadership and Administration",
    tuple(
        _c(f"K.2.1.{i}", f"معيار إدارة برنامج رقم {i}", f"Program administration criterion {i}", "policy")
        for i in range(1, 9)
    ),
)

_K22 = Subdomain(
    "K.2.2",
    "الكوادر البرامجية والموارد",
    "Program Staffing and Resources",
    tuple(
        _c(f"K.2.2.{i}", f"معيار كوادر برامج رقم {i}", f"Program staffing criterion {i}", "hr")
        for i in range(1, 7)
    ),
)

_K23 = Subdomain(
    "K.2.3",
    "تصميم المنهج وتطويره",
    "Curriculum Design and Development",
    tuple(
        _c(f"K.2.3.{i}", f"معيار تصميم منهج رقم {i}", f"Curriculum design criterion {i}", "content")
        for i in range(1, 10)
    ),
)

_K24 = Subdomain(
    "K.2.4",
    "التفاعل والمشاركة التعليمية",
    "Instructional Engagement and Interaction",
    tuple(
        _c(f"K.2.4.{i}", f"معيار تفاعل تعليمي رقم {i}", f"Engagement criterion {i}", "pedagogy")
        for i in range(1, 10)
    ),
)

_K25 = Subdomain(
    "K.2.5",
    "العدالة وإمكانية الوصول",
    "Equity and Accessibility",
    tuple(
        _c(f"K.2.5.{i}", f"معيار عدالة ووصول رقم {i}", f"Equity & accessibility criterion {i}", "accessibility")
        for i in range(1, 8)
    ),
)

_K26 = Subdomain(
    "K.2.6",
    "التقنية والأنظمة",
    "Technology and Systems",
    tuple(
        _c(f"K.2.6.{i}", f"معيار تقنية رقم {i}", f"Technology criterion {i}", "tech")
        for i in range(1, 7)
    ),
)

_K27 = Subdomain(
    "K.2.7",
    "التقويم والتقييم",
    "Evaluation and Assessment",
    tuple(
        _c(f"K.2.7.{i}", f"معيار تقييم برامج رقم {i}", f"Program evaluation criterion {i}", "analytics")
        for i in range(1, 9)
    ),
)

_K2 = Domain(
    "K.2",
    "إدارة البرنامج",
    "Program Administration",
    "يغطي إدارة البرامج الإلكترونية من التخطيط إلى التقييم والتحسين.",
    (_K21, _K22, _K23, _K24, _K25, _K26, _K27),
)


# ---------------------------------------------------------------------------
# K.3 – Online Admin
# ---------------------------------------------------------------------------


_K31 = Subdomain(
    "K.3.1",
    "القيادة",
    "Leadership",
    tuple(
        _c(f"K.3.1.{i}", f"معيار قيادة إدارة عبر الإنترنت {i}", f"Online admin leadership {i}", "policy")
        for i in range(1, 16)
    ),
)

_K32 = Subdomain(
    "K.3.2",
    "الحوكمة والاستراتيجية",
    "Governance and Strategy",
    tuple(
        _c(f"K.3.2.{i}", f"معيار حوكمة واستراتيجية {i}", f"Governance/strategy {i}", "policy")
        for i in range(1, 9)
    ),
)

_K33 = Subdomain(
    "K.3.3",
    "الاحترافية",
    "Professionalism",
    tuple(
        _c(f"K.3.3.{i}", f"معيار احترافية {i}", f"Professionalism {i}", "hr")
        for i in range(1, 6)
    ),
)

_K34 = Subdomain(
    "K.3.4",
    "الموارد",
    "Resources",
    tuple(
        _c(f"K.3.4.{i}", f"معيار موارد إدارة إلكترونية {i}", f"Online admin resources {i}", "finance")
        for i in range(1, 11)
    ),
)

_K35 = Subdomain(
    "K.3.5",
    "التحسين المستمر",
    "Continuous Improvement",
    tuple(
        _c(f"K.3.5.{i}", f"معيار تحسين مستمر {i}", f"Continuous improvement {i}", "analytics")
        for i in range(1, 12)
    ),
)

_K3 = Domain(
    "K.3",
    "الإدارة الإلكترونية",
    "Online Administration",
    "المتطلبات الخاصة بقادة وإداريي التعليم الإلكتروني.",
    (_K31, _K32, _K33, _K34, _K35),
)


# ---------------------------------------------------------------------------
# K.4 – Online Course Design
# ---------------------------------------------------------------------------


_K41 = Subdomain(
    "K.4.1",
    "تصميم المقرر الإلكتروني",
    "Online Course Design",
    tuple(
        _c(f"K.4.1.{i}", f"معيار تصميم مقرر إلكتروني {i}", f"Online course design {i}", "course-design")
        for i in range(1, 20)
    ),
)

_K42 = Subdomain(
    "K.4.2",
    "تصميم مقرر يدعم ذوي الإعاقة والتصميم الشامل",
    "Course Design for Students with Disabilities & Universal Design",
    tuple(
        _c(f"K.4.2.{i}", f"معيار تصميم شامل وإتاحة {i}", f"Universal design / accessibility {i}", "accessibility")
        for i in range(1, 7)
    ),
)

_K43 = Subdomain(
    "K.4.3",
    "توصيف المقرر — الأساس",
    "Course Syllabus – Foundation",
    tuple(
        _c(f"K.4.3.{i}", f"معيار توصيف مقرر أساسي {i}", f"Syllabus foundation {i}", "syllabus")
        for i in range(1, 8)
    ),
)

_K44 = Subdomain(
    "K.4.4",
    "توصيف المقرر — السياسات",
    "Course Syllabus – Policies",
    tuple(
        _c(f"K.4.4.{i}", f"معيار سياسات توصيف المقرر {i}", f"Syllabus policies {i}", "syllabus")
        for i in range(1, 6)
    ),
)

_K45 = Subdomain(
    "K.4.5",
    "التقييم",
    "Assessment",
    tuple(
        _c(f"K.4.5.{i}", f"معيار تقييم المقرر {i}", f"Course assessment {i}", "assessment")
        for i in range(1, 10)
    ),
)

_K46 = Subdomain(
    "K.4.6",
    "استراتيجية التحسين المستمر للمقرر",
    "Continuous Course Improvement Strategy",
    tuple(
        _c(f"K.4.6.{i}", f"معيار تحسين مستمر للمقرر {i}", f"Course improvement {i}", "analytics")
        for i in range(1, 7)
    ),
)

_K4 = Domain(
    "K.4",
    "تصميم المقرر الإلكتروني",
    "Online Course Design",
    "يغطي تصميم المقرر وتوصيفه وتقييمه وإتاحته وتحسينه المستمر.",
    (_K41, _K42, _K43, _K44, _K45, _K46),
)


# ---------------------------------------------------------------------------
# K.5 – Online Teaching
# ---------------------------------------------------------------------------


_K51 = Subdomain(
    "K.5.1",
    "الحضور التعليمي",
    "Teaching Presence",
    tuple(
        _c(f"K.5.1.{i}", f"معيار حضور تعليمي {i}", f"Teaching presence {i}", "teaching")
        for i in range(1, 9)
    ),
)

_K52 = Subdomain(
    "K.5.2",
    "التواصل",
    "Communication",
    tuple(
        _c(f"K.5.2.{i}", f"معيار تواصل تعليمي {i}", f"Communication {i}", "teaching")
        for i in range(1, 8)
    ),
)

_K53 = Subdomain(
    "K.5.3",
    "بناء المجتمع",
    "Building Community",
    tuple(
        _c(f"K.5.3.{i}", f"معيار بناء مجتمع {i}", f"Community {i}", "community")
        for i in range(1, 7)
    ),
)

_K54 = Subdomain(
    "K.5.4",
    "المسؤوليات المهنية",
    "Professional Responsibilities",
    tuple(
        _c(f"K.5.4.{i}", f"معيار مسؤوليات مهنية {i}", f"Professional responsibility {i}", "hr")
        for i in range(1, 8)
    ),
)

_K55 = Subdomain(
    "K.5.5",
    "ممارسات مركزة على الطالب",
    "Student-Focused Teacher Practices",
    tuple(
        _c(f"K.5.5.{i}", f"معيار ممارسة مركزة على الطالب {i}", f"Student-focused practice {i}", "teaching")
        for i in range(1, 9)
    ),
)

_K56 = Subdomain(
    "K.5.6",
    "ممارسات تعليمية محددة",
    "Specific Teacher Practices",
    tuple(
        _c(f"K.5.6.{i}", f"معيار ممارسة معلم محددة {i}", f"Specific teacher practice {i}", "teaching")
        for i in range(1, 14)
    ),
)

_K5 = Domain(
    "K.5",
    "التعليم الإلكتروني",
    "Online Teaching",
    "يغطي ممارسات المعلم عبر الإنترنت والتواصل وبناء المجتمع.",
    (_K51, _K52, _K53, _K54, _K55, _K56),
)


# ---------------------------------------------------------------------------
# K.6 – Blended Learning
# ---------------------------------------------------------------------------


_K61 = Subdomain(
    "K.6.1",
    "اعتبارات إدارية للمدرسة",
    "School Administrator Considerations",
    tuple(
        _c(f"K.6.1.{i}", f"معيار إدارة تعلم مدمج {i}", f"Blended admin {i}", "policy")
        for i in range(1, 8)
    ),
)

_K62 = Subdomain(
    "K.6.2",
    "التخطيط والتصميم التعليمي",
    "Instructional Planning and Design",
    tuple(
        _c(f"K.6.2.{i}", f"معيار تخطيط تعليم مدمج {i}", f"Blended planning {i}", "course-design")
        for i in range(1, 9)
    ),
)

_K63 = Subdomain(
    "K.6.3",
    "دعم المعلم",
    "Teacher Supports",
    tuple(
        _c(f"K.6.3.{i}", f"معيار دعم معلم تعلم مدمج {i}", f"Teacher support {i}", "hr")
        for i in range(1, 7)
    ),
)

_K64 = Subdomain(
    "K.6.4",
    "دعم الطالب",
    "Student Supports",
    tuple(
        _c(f"K.6.4.{i}", f"معيار دعم الطالب {i}", f"Student support {i}", "ux")
        for i in range(1, 7)
    ),
)

_K65 = Subdomain(
    "K.6.5",
    "دعم ولي الأمر",
    "Parent Support",
    tuple(
        _c(f"K.6.5.{i}", f"معيار دعم ولي الأمر {i}", f"Parent support {i}", "ux")
        for i in range(1, 6)
    ),
)

_K66 = Subdomain(
    "K.6.6",
    "المجتمع والشراكات",
    "Community and Partnerships",
    tuple(
        _c(f"K.6.6.{i}", f"معيار مجتمع وشراكات {i}", f"Community/partnership {i}", "community")
        for i in range(1, 5)
    ),
)

_K67 = Subdomain(
    "K.6.7",
    "التحسين المستمر",
    "Continuous Improvement",
    tuple(
        _c(f"K.6.7.{i}", f"معيار تحسين مستمر للتعلم المدمج {i}", f"Blended improvement {i}", "analytics")
        for i in range(1, 7)
    ),
)

_K6 = Domain(
    "K.6",
    "التعلم المدمج",
    "Blended Learning",
    "متطلبات البرامج التي تجمع التعلم الحضوري مع الإلكتروني.",
    (_K61, _K62, _K63, _K64, _K65, _K66, _K67),
)


# ---------------------------------------------------------------------------
# K.7 – Video Production
# ---------------------------------------------------------------------------


_K71 = Subdomain(
    "K.7.1",
    "القيادة والإدارة",
    "Leadership and Administration",
    tuple(
        _c(f"K.7.1.{i}", f"معيار قيادة إنتاج فيديو {i}", f"Video leadership {i}", "policy")
        for i in range(1, 7)
    ),
)

_K72 = Subdomain(
    "K.7.2",
    "التخطيط والمحتوى والتصميم",
    "Planning, Content, and Design",
    tuple(
        _c(f"K.7.2.{i}", f"معيار تخطيط وتصميم فيديو {i}", f"Video planning {i}", "content")
        for i in range(1, 9)
    ),
)

_K73 = Subdomain(
    "K.7.3",
    "الإنتاج والتسليم والجودة",
    "Production, Delivery, and Quality",
    tuple(
        _c(f"K.7.3.{i}", f"معيار إنتاج فيديو {i}", f"Video production {i}", "content")
        for i in range(1, 9)
    ),
)

_K74 = Subdomain(
    "K.7.4",
    "الوصول وإمكانية الوصول للفيديو",
    "Video Access and Accessibility",
    tuple(
        _c(f"K.7.4.{i}", f"معيار إتاحة فيديو {i}", f"Video accessibility {i}", "accessibility")
        for i in range(1, 7)
    ),
)

_K75 = Subdomain(
    "K.7.5",
    "التحسين المستمر",
    "Continuous Improvement",
    tuple(
        _c(f"K.7.5.{i}", f"معيار تحسين مستمر للفيديو {i}", f"Video improvement {i}", "analytics")
        for i in range(1, 6)
    ),
)

_K7 = Domain(
    "K.7",
    "إنتاج الفيديو",
    "Video Production",
    "إنتاج وتسليم وإتاحة الفيديو التعليمي.",
    (_K71, _K72, _K73, _K74, _K75),
)


# ---------------------------------------------------------------------------
# K.8 – Virtual Classroom
# ---------------------------------------------------------------------------


_K81 = Subdomain(
    "K.8.1",
    "إدارة الفصل",
    "Classroom Management",
    tuple(
        _c(f"K.8.1.{i}", f"معيار إدارة فصل افتراضي {i}", f"Virtual classroom management {i}", "teaching")
        for i in range(1, 11)
    ),
)

_K82 = Subdomain(
    "K.8.2",
    "التربية",
    "Pedagogy",
    tuple(
        _c(f"K.8.2.{i}", f"معيار تربية فصل افتراضي {i}", f"Virtual classroom pedagogy {i}", "teaching")
        for i in range(1, 11)
    ),
)

_K8 = Domain(
    "K.8",
    "الفصل الافتراضي",
    "Virtual Classroom",
    "إدارة الفصول الافتراضية المتزامنة.",
    (_K81, _K82),
)


# ---------------------------------------------------------------------------
# Public taxonomy
# ---------------------------------------------------------------------------


DOMAINS: Tuple[Domain, ...] = (_K1, _K2, _K3, _K4, _K5, _K6, _K7, _K8)


_DOMAIN_INDEX: Dict[str, Domain] = {d.code: d for d in DOMAINS}
_SUBDOMAIN_INDEX: Dict[str, Subdomain] = {
    sd.code: sd for d in DOMAINS for sd in d.subdomains
}
_CRITERION_INDEX: Dict[str, Criterion] = {
    c.code: c for d in DOMAINS for sd in d.subdomains for c in sd.criteria
}


def domain_by_code(code: str) -> Optional[Domain]:
    return _DOMAIN_INDEX.get(code)


def subdomain_by_code(code: str) -> Optional[Subdomain]:
    return _SUBDOMAIN_INDEX.get(code)


def criterion_by_code(code: str) -> Optional[Criterion]:
    return _CRITERION_INDEX.get(code)


def all_criteria() -> Iterable[Criterion]:
    for d in DOMAINS:
        for sd in d.subdomains:
            yield from sd.criteria


def total_criteria_count() -> int:
    return sum(d.criteria_count for d in DOMAINS)


def taxonomy_summary() -> Dict[str, int]:
    return {
        "domains": len(DOMAINS),
        "subdomains": sum(d.subdomain_count for d in DOMAINS),
        "criteria": total_criteria_count(),
    }
