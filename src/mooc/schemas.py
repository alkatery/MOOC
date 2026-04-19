"""Pydantic schemas for request/response serialization."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import (
    CourseLevel,
    CourseStatus,
    EnrollmentStatus,
    LessonType,
    QuestionType,
    ReviewState,
    UserRole,
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    full_name_ar: str = Field(..., min_length=2, max_length=255)
    full_name_en: Optional[str] = None
    national_id: Optional[str] = Field(None, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.STUDENT
    phone: Optional[str] = None
    preferred_language: str = "ar"
    consent_privacy: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    email: str
    full_name_ar: str
    full_name_en: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name_ar: str
    name_en: Optional[str]
    icon: Optional[str]


class LessonIn(BaseModel):
    title_ar: str
    lesson_type: LessonType = LessonType.TEXT
    content: Optional[str] = None
    resource_url: Optional[str] = None
    duration_minutes: int = 0
    order_index: int = 0
    is_free_preview: bool = False
    has_transcript: bool = False
    transcript_text: Optional[str] = None
    has_sign_language: bool = False
    captions_url: Optional[str] = None


class LessonOut(LessonIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int


class ModuleIn(BaseModel):
    title_ar: str
    description_ar: Optional[str] = None
    order_index: int = 0


class ModuleOut(ModuleIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    lessons: List[LessonOut] = []


class CourseIn(BaseModel):
    code: str
    title_ar: str
    title_en: Optional[str] = None
    short_description_ar: str
    description_ar: str
    category_id: Optional[int] = None
    level: CourseLevel = CourseLevel.BEGINNER
    language: str = "ar"
    duration_hours: float = 0.0
    price: float = 0.0
    is_free: bool = True
    passing_grade: int = 60
    max_attempts: int = 3
    learning_outcomes: List[str] = []
    target_audience: Optional[str] = None
    prerequisites: Optional[str] = None
    accessibility_features: List[str] = []


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    code: str
    title_ar: str
    short_description_ar: str
    level: CourseLevel
    language: str
    duration_hours: float
    status: CourseStatus
    price: float
    is_free: bool
    passing_grade: int
    instructor_id: int
    category_id: Optional[int]
    created_at: datetime
    published_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------


class QuestionIn(BaseModel):
    question_type: QuestionType
    text_ar: str
    choices: List[str] = []
    correct_answer: List[str] = []
    explanation_ar: Optional[str] = None
    points: float = 1.0
    order_index: int = 0


class QuestionOut(QuestionIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int


class QuizIn(BaseModel):
    title_ar: str
    instructions_ar: Optional[str] = None
    time_limit_minutes: int = 0
    passing_score: int = 60
    max_attempts: int = 3
    shuffle_questions: bool = True
    show_correct_answers: bool = True


class QuizOut(QuizIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int
    questions: List[QuestionOut] = []


class QuizAttemptIn(BaseModel):
    answers: dict


class QuizAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    score: float
    max_score: float
    passed: bool
    submitted_at: Optional[datetime]


class AssignmentIn(BaseModel):
    title_ar: str
    instructions_ar: str
    due_at: Optional[datetime] = None
    max_score: float = 100.0
    rubric: List[dict] = []


class AssignmentOut(AssignmentIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int


class SubmissionIn(BaseModel):
    content: str
    attachment_url: Optional[str] = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    user_id: int
    submitted_at: datetime
    score: Optional[float]
    feedback_ar: Optional[str]


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    course_id: int
    status: EnrollmentStatus
    progress_percent: float
    final_grade: Optional[float]
    enrolled_at: datetime
    completed_at: Optional[datetime]


# ---------------------------------------------------------------------------
# NELC quality review
# ---------------------------------------------------------------------------


class ReviewItem(BaseModel):
    criterion_code: str
    score: int = Field(..., ge=1, le=3)
    evidence: Optional[str] = None
    note: Optional[str] = None


class ReviewIn(BaseModel):
    items: List[ReviewItem]
    comments_ar: Optional[str] = None
    state: ReviewState = ReviewState.PENDING


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    reviewer_id: int
    state: ReviewState
    score: float
    comments_ar: Optional[str]
    reviewed_at: datetime
