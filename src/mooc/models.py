"""SQLAlchemy ORM models for the MOOC platform.

The schema is designed to cover the feature-set required by Saudi Arabia's
National eLearning Center (NELC) quality standards while staying
straightforward enough to run on SQLite for local development.

Key entity groups:

* Users & roles (student, instructor, reviewer, admin)
* Catalog: categories, courses, course versions, modules, lessons
* Delivery: enrollments, lesson progress, xAPI statements
* Assessments: quizzes, questions, attempts, assignments, submissions
* Community: discussion threads and posts
* Certification: issued certificates with verifiable codes
* Quality: NELC review checklist & audit log
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class UserRole(str, enum.Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class CourseStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class CourseLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LessonType(str, enum.Enum):
    VIDEO = "video"
    TEXT = "text"
    PDF = "pdf"
    SCORM = "scorm"
    EXTERNAL = "external"
    INTERACTIVE = "interactive"
    LIVE = "live"


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    SUSPENDED = "suspended"


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    MULTIPLE_ANSWER = "multiple_answer"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"


class ReviewState(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"


class SubscriptionPlanCode(str, enum.Enum):
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"


class BillingPeriod(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Tenant (SaaS workspace)
# ---------------------------------------------------------------------------


class Tenant(Base):
    """A SaaS workspace — each subscriber gets their own."""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, default=_uuid, index=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name_ar: Mapped[str] = mapped_column(String(160), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    tagline_ar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    about_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(16), default="#0a7d3a", nullable=False)
    accent_color: Mapped[str] = mapped_column(String(16), default="#1f5fbf", nullable=False)
    background_color: Mapped[str] = mapped_column(String(16), default="#ffffff", nullable=False)
    text_color: Mapped[str] = mapped_column(String(16), default="#1a1a1a", nullable=False)
    custom_labels: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    social_links: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    policies: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    custom_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )
    pages: Mapped[List["TenantPage"]] = relationship(
        "TenantPage", back_populates="tenant", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        return self.name_ar or self.name_en or self.slug


class SubscriptionPlan(Base):
    """Pricing plan — Free / Standard / Premium."""

    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[SubscriptionPlanCode] = mapped_column(
        Enum(SubscriptionPlanCode, native_enum=False, length=16),
        unique=True,
        nullable=False,
    )
    name_ar: Mapped[str] = mapped_column(String(80), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    description_ar: Mapped[str] = mapped_column(Text, nullable=False)
    price_monthly_sar: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    price_yearly_sar: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_courses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_students: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_admins: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    features: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Subscription(Base):
    """A tenant's active subscription (one row per tenant)."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), unique=True, nullable=False
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    period: Mapped[BillingPeriod] = mapped_column(
        Enum(BillingPeriod, native_enum=False, length=16),
        default=BillingPeriod.MONTHLY,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, length=16),
        default=SubscriptionStatus.TRIAL,
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_payment_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_payment_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="subscription")
    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan")

    @property
    def is_usable(self) -> bool:
        return self.status in {SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE}


class TenantPage(Base):
    """Custom CMS page authored by a tenant (about, FAQ, etc.)."""

    __tablename__ = "tenant_pages"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_tenant_page_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_in_nav: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="pages")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(Base):
    """Learner / instructor / admin account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, default=_uuid, index=True)
    tenant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    national_id: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    full_name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=16), default=UserRole.STUDENT, nullable=False
    )
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(5), default="ar", nullable=False)
    accessibility_profile: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_privacy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    taught_courses: Mapped[List["Course"]] = relationship(
        "Course", back_populates="instructor", foreign_keys="Course.instructor_id"
    )
    enrollments: Mapped[List["Enrollment"]] = relationship(
        "Enrollment", back_populates="user", cascade="all, delete-orphan"
    )
    certificates: Mapped[List["Certificate"]] = relationship(
        "Certificate", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        return self.full_name_ar or self.full_name_en or self.email


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    description_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    courses: Mapped[List["Course"]] = relationship("Course", back_populates="category")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, default=_uuid, index=True)
    tenant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    short_description_ar: Mapped[str] = mapped_column(String(500), nullable=False)
    description_ar: Mapped[str] = mapped_column(Text, nullable=False)
    learning_outcomes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prerequisites: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    level: Mapped[CourseLevel] = mapped_column(
        Enum(CourseLevel, native_enum=False, length=16),
        default=CourseLevel.BEGINNER,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(5), default="ar", nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cover_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trailer_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, native_enum=False, length=20),
        default=CourseStatus.DRAFT,
        nullable=False,
    )
    passing_grade: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    accessibility_features: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    nelc_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="courses")
    instructor: Mapped["User"] = relationship(
        "User", back_populates="taught_courses", foreign_keys=[instructor_id]
    )
    modules: Mapped[List["Module"]] = relationship(
        "Module",
        back_populates="course",
        order_by="Module.order_index",
        cascade="all, delete-orphan",
    )
    enrollments: Mapped[List["Enrollment"]] = relationship(
        "Enrollment", back_populates="course", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["QualityReview"]] = relationship(
        "QualityReview", back_populates="course", cascade="all, delete-orphan"
    )
    discussions: Mapped[List["DiscussionThread"]] = relationship(
        "DiscussionThread", back_populates="course", cascade="all, delete-orphan"
    )
    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment", back_populates="course", cascade="all, delete-orphan"
    )


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    description_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    course: Mapped["Course"] = relationship("Course", back_populates="modules")
    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson",
        back_populates="module",
        order_by="Lesson.order_index",
        cascade="all, delete-orphan",
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    lesson_type: Mapped[LessonType] = mapped_column(
        Enum(LessonType, native_enum=False, length=20),
        default=LessonType.TEXT,
        nullable=False,
    )
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_free_preview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_transcript: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transcript_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_sign_language: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    captions_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    module: Mapped["Module"] = relationship("Module", back_populates="lessons")
    quiz: Mapped[Optional["Quiz"]] = relationship(
        "Quiz", back_populates="lesson", uselist=False, cascade="all, delete-orphan"
    )
    progresses: Mapped[List["LessonProgress"]] = relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Enrollments & progress
# ---------------------------------------------------------------------------


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, native_enum=False, length=16),
        default=EnrollmentStatus.ACTIVE,
        nullable=False,
    )
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_grade: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="enrollments")
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")
    lesson_progresses: Mapped[List["LessonProgress"]] = relationship(
        "LessonProgress", back_populates="enrollment", cascade="all, delete-orphan"
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "lesson_id", name="uq_enrollment_lesson"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="lesson_progresses")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="progresses")


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), unique=True, nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passing_score: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_correct_answers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="quiz")
    questions: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="quiz",
        order_by="Question.order_index",
        cascade="all, delete-orphan",
    )
    attempts: Mapped[List["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, native_enum=False, length=20),
        default=QuestionType.MULTIPLE_CHOICE,
        nullable=False,
    )
    text_ar: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    correct_answer: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    explanation_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions_ar: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    max_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    rubric: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    course: Mapped["Course"] = relationship("Course", back_populates="assignments")
    submissions: Mapped[List["AssignmentSubmission"]] = relationship(
        "AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan"
    )


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feedback_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    graded_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    assignment: Mapped["Assignment"] = relationship("Assignment", back_populates="submissions")


# ---------------------------------------------------------------------------
# Community
# ---------------------------------------------------------------------------


class DiscussionThread(Base):
    __tablename__ = "discussion_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    body_ar: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    course: Mapped["Course"] = relationship("Course", back_populates="discussions")
    posts: Mapped[List["DiscussionPost"]] = relationship(
        "DiscussionPost",
        back_populates="thread",
        order_by="DiscussionPost.created_at",
        cascade="all, delete-orphan",
    )


class DiscussionPost(Base):
    __tablename__ = "discussion_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("discussion_threads.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body_ar: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    thread: Mapped["DiscussionThread"] = relationship("DiscussionThread", back_populates="posts")


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verification_code: Mapped[str] = mapped_column(
        String(32), unique=True, default=_uuid, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id"), nullable=False)
    grade: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="certificates")


# ---------------------------------------------------------------------------
# NELC quality review + audit
# ---------------------------------------------------------------------------


class QualityReview(Base):
    __tablename__ = "quality_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    state: Mapped[ReviewState] = mapped_column(
        Enum(ReviewState, native_enum=False, length=20),
        default=ReviewState.PENDING,
        nullable=False,
    )
    checklist: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    comments_ar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    course: Mapped["Course"] = relationship("Course", back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class XAPIStatement(Base):
    """Stored xAPI statement for NELC tracking & interoperability."""

    __tablename__ = "xapi_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    statement_id: Mapped[str] = mapped_column(String(36), unique=True, default=_uuid, nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    verb: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    stored_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
