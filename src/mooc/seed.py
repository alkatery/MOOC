"""Seed the database with demo users, categories, and courses."""

from __future__ import annotations

from datetime import datetime, timedelta

from .database import session_scope
from .models import (
    BillingPeriod,
    Category,
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
    Subscription,
    SubscriptionPlan,
    SubscriptionPlanCode,
    SubscriptionStatus,
    Tenant,
    TenantPage,
    User,
    UserRole,
)
from .security import hash_password


DEMO_USERS = [
    {
        "email": "admin@mooc.sa",
        "full_name_ar": "مدير النظام",
        "password": "Admin1234",
        "role": UserRole.ADMIN,
    },
    {
        "email": "reviewer@mooc.sa",
        "full_name_ar": "مراجع الجودة",
        "password": "Review1234",
        "role": UserRole.REVIEWER,
    },
    {
        "email": "teacher@mooc.sa",
        "full_name_ar": "أ. فاطمة الزهراني",
        "password": "Teach1234",
        "role": UserRole.INSTRUCTOR,
    },
    {
        "email": "student@mooc.sa",
        "full_name_ar": "محمد عبدالله",
        "password": "Study1234",
        "role": UserRole.STUDENT,
    },
]

CATEGORIES = [
    ("cs", "علوم الحاسب", "Computer Science", "💻"),
    ("math", "الرياضيات", "Mathematics", "📐"),
    ("lang", "اللغات", "Languages", "🗣️"),
    ("business", "إدارة الأعمال", "Business", "📊"),
    ("health", "الصحة العامة", "Health", "🩺"),
    ("edu", "التربية والتعليم", "Education", "🎓"),
]


def _ensure_user(db, email, full_name_ar, password, role):
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        full_name_ar=full_name_ar,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        is_verified=True,
        consent_privacy=True,
        consent_timestamp=datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    return user


def _ensure_category(db, slug, ar, en, icon):
    cat = db.query(Category).filter(Category.slug == slug).first()
    if cat:
        return cat
    cat = Category(slug=slug, name_ar=ar, name_en=en, icon=icon)
    db.add(cat)
    db.flush()
    return cat


def _ensure_plans(db) -> dict:
    plans_def = [
        {
            "code": SubscriptionPlanCode.FREE,
            "name_ar": "تجريبي",
            "name_en": "Free Trial",
            "description_ar": "ابدأ بـ ٥٠ طالباً ومقررين، بدون الذكاء الاصطناعي.",
            "price_monthly_sar": 0.0,
            "price_yearly_sar": 0.0,
            "max_courses": 2,
            "max_students": 50,
            "max_admins": 1,
            "features": ["دعم بريدي", "شهادات قابلة للتحقق", "تكامل xAPI/SCORM"],
            "is_default": False,
        },
        {
            "code": SubscriptionPlanCode.STANDARD,
            "name_ar": "قياسي",
            "name_en": "Standard",
            "description_ar": "للأكاديميات النامية — مقررات ومتعلمون بلا حدود فعلية.",
            "price_monthly_sar": 499.0,
            "price_yearly_sar": 4791.0,
            "max_courses": 50,
            "max_students": 1000,
            "max_admins": 5,
            "features": [
                "مساعد ذكاء اصطناعي للطلاب",
                "تحليلات إدارية ذكية",
                "تخصيص كامل للهوية",
                "صفحات مخصصة بلا حدود",
                "دعم خلال ساعات العمل",
            ],
            "is_default": True,
        },
        {
            "code": SubscriptionPlanCode.PREMIUM,
            "name_ar": "متميّز",
            "name_en": "Premium",
            "description_ar": "للمؤسسات الكبيرة — استخدام بلا حدود ودعم مخصص.",
            "price_monthly_sar": 1999.0,
            "price_yearly_sar": 19191.0,
            "max_courses": 0,
            "max_students": 0,
            "max_admins": 25,
            "features": [
                "كل ميزات الباقة القياسية",
                "نطاق مخصص (Custom domain)",
                "تكامل SSO",
                "اعتماد NELC مرافق",
                "مدير حساب مخصص",
                "اتفاقية مستوى الخدمة (SLA)",
            ],
            "is_default": False,
        },
    ]
    plans = {}
    for d in plans_def:
        existing = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.code == d["code"])
            .first()
        )
        if existing:
            plans[d["code"].value] = existing
            continue
        plan = SubscriptionPlan(**d)
        db.add(plan)
        db.flush()
        plans[d["code"].value] = plan
    return plans


def _ensure_default_tenant(db, plans: dict) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if tenant:
        return tenant
    tenant = Tenant(
        slug="default",
        name_ar="منصة المساقات المفتوحة",
        name_en="Open MOOC Platform",
        tagline_ar="تعليم إلكتروني عربي متكامل",
        about_ar=(
            "منصة تعليم إلكترونية عربية مفتوحة المصدر، متوافقة مع معايير "
            "المركز الوطني للتعليم الإلكتروني (NELC)، تساعد المؤسسات على "
            "إطلاق مقررات احترافية بسرعة."
        ),
        contact_email="hello@mooc.sa",
        primary_color="#006c35",
        accent_color="#c8a85a",
        background_color="#fafafa",
        text_color="#1a1a1a",
        social_links={
            "twitter": "https://x.com/saudi_nelc",
            "website": "https://nelc.gov.sa",
        },
        policies={"privacy": "تُحفظ بيانات الطلاب داخل المملكة وتُحذف عند الطلب."},
        custom_labels={},
    )
    db.add(tenant)
    db.flush()

    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=plans["premium"].id,
        period=BillingPeriod.YEARLY,
        status=SubscriptionStatus.ACTIVE,
        starts_at=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=365),
    )
    db.add(sub)

    # Sample custom pages
    for slug, title, body in (
        (
            "about",
            "عن المنصة",
            "<p>منصة عربية مفتوحة لإطلاق دوراتك الإلكترونية وفق أعلى المعايير.</p>",
        ),
        (
            "terms",
            "شروط الاستخدام",
            "<p>باستخدامك للمنصة، توافق على الالتزام بسياسات النزاهة الأكاديمية وحقوق الملكية الفكرية.</p>",
        ),
        (
            "faq",
            "الأسئلة الشائعة",
            "<h3>هل المحتوى متاح بالعربية؟</h3><p>نعم، جميع الواجهات والمحتوى الافتراضي بالعربية الفصحى.</p>",
        ),
    ):
        db.add(
            TenantPage(
                tenant_id=tenant.id,
                slug=slug,
                title_ar=title,
                body_html=body,
                is_published=True,
                show_in_nav=(slug != "terms"),
            )
        )
    return tenant


def run_seed() -> None:
    with session_scope() as db:
        plans = _ensure_plans(db)
        tenant = _ensure_default_tenant(db, plans)
        users = {
            u["email"]: _ensure_user(db, **u) for u in DEMO_USERS
        }
        # Tag demo users with the default tenant
        for u in users.values():
            if u.tenant_id is None:
                u.tenant_id = tenant.id

        categories = {
            slug: _ensure_category(db, slug, ar, en, icon)
            for slug, ar, en, icon in CATEGORIES
        }
        for c in categories.values():
            if c.tenant_id is None:
                c.tenant_id = tenant.id

        instructor = users["teacher@mooc.sa"]

        if db.query(Course).filter(Course.code == "CS101").first() is None:
            course = Course(
                tenant_id=tenant.id,
                code="CS101",
                title_ar="مقدمة في علوم الحاسب",
                title_en="Introduction to Computer Science",
                short_description_ar="رحلة مبسطة في مفاهيم الحاسب والبرمجة.",
                description_ar=(
                    "يغطي هذا المقرر المبادئ الأساسية للحاسب والخوارزميات والبرمجة "
                    "بلغة بايثون، ويُعدّك لبدء رحلتك في عالم التقنية."
                ),
                level=CourseLevel.BEGINNER,
                language="ar",
                duration_hours=12.0,
                is_free=True,
                passing_grade=60,
                learning_outcomes=[
                    "فهم مبادئ التفكير الحاسوبي",
                    "كتابة برامج بسيطة بلغة بايثون",
                    "تحليل الخوارزميات الأساسية",
                ],
                target_audience="المبتدئون في علوم الحاسب.",
                prerequisites="لا يتطلب خبرة سابقة.",
                accessibility_features=["نصوص مكتوبة", "ترجمة إشارية", "تباين عالٍ"],
                cover_image="/static/img/cs101-cover.jpg",
                category_id=categories["cs"].id,
                instructor_id=instructor.id,
                status=CourseStatus.PUBLISHED,
                published_at=datetime.utcnow(),
                nelc_metadata={
                    "track": "general-education",
                    "integrity_policy": True,
                    "ip_compliance": "CC BY 4.0",
                    "national_compliance": True,
                    "syllabus_url": "/static/cs101-syllabus.pdf",
                },
            )
            db.add(course)
            db.flush()

            mod1 = Module(
                course_id=course.id,
                title_ar="الوحدة الأولى: التفكير الحاسوبي",
                description_ar="مقدمة إلى مفاهيم التفكير الحاسوبي وحل المشكلات.",
                order_index=1,
            )
            mod2 = Module(
                course_id=course.id,
                title_ar="الوحدة الثانية: البرمجة ببايثون",
                description_ar="أساسيات بايثون والمتغيرات والدوال.",
                order_index=2,
            )
            db.add_all([mod1, mod2])
            db.flush()

            lessons = [
                Lesson(
                    module_id=mod1.id,
                    title_ar="ما هو التفكير الحاسوبي؟",
                    lesson_type=LessonType.VIDEO,
                    resource_url="https://example.com/cs101-intro.mp4",
                    duration_minutes=10,
                    has_transcript=True,
                    transcript_text="نص مكتوب للفيديو التعريفي...",
                    order_index=1,
                    is_free_preview=True,
                ),
                Lesson(
                    module_id=mod1.id,
                    title_ar="الخوارزمية والبرنامج",
                    lesson_type=LessonType.TEXT,
                    content="الخوارزمية هي سلسلة من الخطوات المحددة لحل مشكلة معينة...",
                    duration_minutes=15,
                    order_index=2,
                ),
                Lesson(
                    module_id=mod2.id,
                    title_ar="تنصيب بيئة العمل",
                    lesson_type=LessonType.VIDEO,
                    resource_url="https://example.com/cs101-setup.mp4",
                    duration_minutes=8,
                    has_transcript=True,
                    order_index=1,
                ),
                Lesson(
                    module_id=mod2.id,
                    title_ar="أول برنامج: Hello World",
                    lesson_type=LessonType.INTERACTIVE,
                    content="اكتب البرنامج التالي وقم بتشغيله:\n\nprint('أهلاً بالعالم!')",
                    duration_minutes=10,
                    order_index=2,
                ),
                Lesson(
                    module_id=mod2.id,
                    title_ar="اختبار الوحدة الثانية",
                    lesson_type=LessonType.TEXT,
                    content="استعد للاختبار القصير التالي لقياس فهمك.",
                    duration_minutes=5,
                    order_index=3,
                ),
            ]
            db.add_all(lessons)
            db.flush()

            quiz = Quiz(
                lesson_id=lessons[-1].id,
                title_ar="اختبار الوحدة الثانية",
                instructions_ar="أجب على الأسئلة التالية خلال 10 دقائق.",
                time_limit_minutes=10,
                passing_score=60,
                max_attempts=3,
            )
            db.add(quiz)
            db.flush()

            db.add_all(
                [
                    Question(
                        quiz_id=quiz.id,
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        text_ar="ما هي اللغة التي ندرسها في هذا المقرر؟",
                        choices=["Python", "Java", "C++", "Ruby"],
                        correct_answer=["Python"],
                        points=1.0,
                        order_index=1,
                    ),
                    Question(
                        quiz_id=quiz.id,
                        question_type=QuestionType.TRUE_FALSE,
                        text_ar="الخوارزمية هي سلسلة من الخطوات لحل مشكلة.",
                        choices=["صح", "خطأ"],
                        correct_answer=["صح"],
                        points=1.0,
                        order_index=2,
                    ),
                    Question(
                        quiz_id=quiz.id,
                        question_type=QuestionType.SHORT_ANSWER,
                        text_ar="ما اسم الدالة التي تطبع النص على الشاشة في بايثون؟",
                        choices=[],
                        correct_answer=["print"],
                        points=2.0,
                        order_index=3,
                    ),
                ]
            )

            # Enroll demo student
            student = users["student@mooc.sa"]
            enrollment = Enrollment(user_id=student.id, course_id=course.id)
            db.add(enrollment)

    print("تم إدخال البيانات التجريبية بنجاح.")
    print("يمكنك تسجيل الدخول باستخدام:")
    for u in DEMO_USERS:
        print(f"  {u['role'].value:10s}  {u['email']:25s}  كلمة المرور: {u['password']}")
