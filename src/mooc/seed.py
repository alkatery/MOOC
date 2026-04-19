"""Seed the database with demo users, categories, and courses."""

from __future__ import annotations

from datetime import datetime

from .database import session_scope
from .models import (
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


def run_seed() -> None:
    with session_scope() as db:
        users = {
            u["email"]: _ensure_user(db, **u) for u in DEMO_USERS
        }
        categories = {
            slug: _ensure_category(db, slug, ar, en, icon)
            for slug, ar, en, icon in CATEGORIES
        }

        instructor = users["teacher@mooc.sa"]

        if db.query(Course).filter(Course.code == "CS101").first() is None:
            course = Course(
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
                category_id=categories["cs"].id,
                instructor_id=instructor.id,
                status=CourseStatus.PUBLISHED,
                published_at=datetime.utcnow(),
                nelc_metadata={"track": "general-education"},
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
