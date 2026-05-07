"""Admin learning analytics + AI-generated narrative.

Computes deterministic statistics from the database (no LLM involved
in the numbers — those must be auditable), then optionally calls the
local AI service to produce an Arabic management summary that an admin
can read in 30 seconds.

Outputs four signal categories matching what NELC dashboards typically
expose:

* ``top_students``        — متميّزون
* ``at_risk_students``    — متعثّرون
* ``bottleneck_lessons``  — نقاط اختناق (دروس يتوقف عندها كثيرون)
* ``confusing_questions`` — أسئلة كثيرة الخطأ
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy.orm import Session

from ..models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    Lesson,
    LessonProgress,
    Module,
    Question,
    QuizAttempt,
    User,
    UserRole,
)
from . import ai


def compute_insights(db: Session, *, top_n: int = 5) -> Dict[str, object]:
    now = datetime.utcnow()
    enrollments = (
        db.query(Enrollment)
        .join(User, Enrollment.user_id == User.id)
        .filter(User.role == UserRole.STUDENT)
        .all()
    )

    top: List[dict] = []
    at_risk: List[dict] = []
    for e in enrollments:
        student = db.query(User).filter(User.id == e.user_id).first()
        if not student:
            continue
        course = db.query(Course).filter(Course.id == e.course_id).first()
        record = {
            "student_id": student.id,
            "student_name": student.display_name,
            "course_title": course.title_ar if course else "—",
            "progress": e.progress_percent,
            "grade": e.final_grade or 0.0,
            "last_active": e.last_accessed_at,
        }
        if (e.final_grade or 0.0) >= 85.0 and e.progress_percent >= 80.0:
            top.append(record)
        # at-risk = stalled (no activity 14+ days) OR low progress after 30 days enrolled
        last_active = e.last_accessed_at or e.enrolled_at
        days_since = (now - last_active).days if last_active else 0
        days_enrolled = (now - e.enrolled_at).days if e.enrolled_at else 0
        if e.status == EnrollmentStatus.ACTIVE and (
            days_since >= 14 or (days_enrolled >= 30 and e.progress_percent < 20.0)
        ):
            record["days_inactive"] = days_since
            at_risk.append(record)

    top.sort(key=lambda r: r["grade"], reverse=True)
    at_risk.sort(key=lambda r: r.get("days_inactive", 0), reverse=True)

    bottleneck = _bottleneck_lessons(db, top_n=top_n)
    confusing = _confusing_questions(db, top_n=top_n)

    return {
        "top_students": top[:top_n],
        "at_risk_students": at_risk[:top_n],
        "bottleneck_lessons": bottleneck,
        "confusing_questions": confusing,
        "totals": {
            "students": db.query(User).filter(User.role == UserRole.STUDENT).count(),
            "active_enrollments": db.query(Enrollment)
            .filter(Enrollment.status == EnrollmentStatus.ACTIVE)
            .count(),
            "completed_enrollments": db.query(Enrollment)
            .filter(Enrollment.status == EnrollmentStatus.COMPLETED)
            .count(),
        },
    }


def _bottleneck_lessons(db: Session, *, top_n: int) -> List[dict]:
    """Lessons where many students started but few completed."""
    lessons = db.query(Lesson).all()
    rows: List[dict] = []
    for lesson in lessons:
        progresses = (
            db.query(LessonProgress)
            .filter(LessonProgress.lesson_id == lesson.id)
            .all()
        )
        started = len(progresses)
        completed = sum(1 for p in progresses if p.completed)
        if started < 3:  # noise floor
            continue
        completion_rate = completed / started * 100.0
        if completion_rate >= 80.0:
            continue
        rows.append(
            {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title_ar,
                "course_title": lesson.module.course.title_ar if lesson.module else "—",
                "started": started,
                "completed": completed,
                "completion_rate": round(completion_rate, 1),
            }
        )
    rows.sort(key=lambda r: r["completion_rate"])
    return rows[:top_n]


def _confusing_questions(db: Session, *, top_n: int) -> List[dict]:
    """Questions where most students got it wrong."""
    counts: Dict[int, Dict[str, int]] = defaultdict(lambda: {"wrong": 0, "total": 0})
    attempts = db.query(QuizAttempt).filter(QuizAttempt.submitted_at.isnot(None)).all()
    for a in attempts:
        for qid_s, entry in (a.answers or {}).items():
            try:
                qid = int(qid_s)
            except (TypeError, ValueError):
                continue
            counts[qid]["total"] += 1
            if not entry.get("correct"):
                counts[qid]["wrong"] += 1

    rows: List[dict] = []
    for qid, c in counts.items():
        if c["total"] < 3:
            continue
        wrong_rate = c["wrong"] / c["total"] * 100.0
        if wrong_rate < 60.0:
            continue
        q = db.query(Question).filter(Question.id == qid).first()
        if not q:
            continue
        rows.append(
            {
                "question_id": qid,
                "text": q.text_ar[:140],
                "wrong_rate": round(wrong_rate, 1),
                "total_attempts": c["total"],
            }
        )
    rows.sort(key=lambda r: r["wrong_rate"], reverse=True)
    return rows[:top_n]


def generate_admin_summary_ar(insights: Dict[str, object]) -> str:
    """Ask the local LLM to produce a short Arabic management summary."""
    prompt = (
        "أنت محلل بيانات تعليمية. اقرأ الإحصاءات التالية واكتب ملخصاً "
        "إدارياً عربياً موجزاً (3-5 أسطر) للمدير، يبرز أهم نقطة تحتاج "
        "تدخّلاً، والإيجابيات، وتوصية واحدة قابلة للتنفيذ.\n\n"
        f"الإحصاءات:\n{insights}"
    )
    return ai.chat([{"role": "user", "content": prompt}])
