"""Admin portal (لوحة تحكم الإدارة) + NELC quality review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import (
    AuditLog,
    Certificate,
    Course,
    CourseStatus,
    Enrollment,
    QualityReview,
    ReviewState,
    User,
    UserRole,
    XAPIStatement,
)
from ..nelc import DOMAINS, total_criteria_count
from ..security import require_admin, require_reviewer
from ..services.audit import log as audit_log
from ..services.review import (
    blank_checklist,
    compute_score,
    domain_breakdown,
    save_review,
)

router = APIRouter(prefix="/admin", tags=["admin-portal"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _ctx(request, user, **kwargs):
    return {"request": request, "user": user, "settings": get_settings(), **kwargs}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    stats = {
        "users": db.query(User).count(),
        "students": db.query(User).filter(User.role == UserRole.STUDENT).count(),
        "instructors": db.query(User).filter(User.role == UserRole.INSTRUCTOR).count(),
        "courses_total": db.query(Course).count(),
        "courses_published": db.query(Course).filter(Course.status == CourseStatus.PUBLISHED).count(),
        "courses_draft": db.query(Course).filter(Course.status == CourseStatus.DRAFT).count(),
        "courses_review": db.query(Course).filter(Course.status == CourseStatus.UNDER_REVIEW).count(),
        "enrollments": db.query(Enrollment).count(),
        "certificates": db.query(Certificate).count(),
        "xapi_statements": db.query(XAPIStatement).count(),
        "nelc_domains": len(DOMAINS),
        "nelc_criteria": total_criteria_count(),
    }
    pending_reviews = (
        db.query(Course)
        .filter(Course.status == CourseStatus.UNDER_REVIEW)
        .order_by(Course.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(request, "admin/dashboard.html",
        _ctx(request, user, stats=stats, pending_reviews=pending_reviews),
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users", response_class=HTMLResponse)
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(request, "admin/users.html", _ctx(request, user, users=users, roles=list(UserRole))
    )


@router.post("/users/{user_id}/role")
def change_role(
    user_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    if role not in {r.value for r in UserRole}:
        raise HTTPException(status_code=400, detail="دور غير معروف")
    target.role = UserRole(role)
    audit_log(db, user, "user.change_role", "user", target.public_id, {"role": role})
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-active")
def toggle_active(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    target.is_active = not target.is_active
    audit_log(
        db,
        user,
        "user.toggle_active",
        "user",
        target.public_id,
        {"active": target.is_active},
    )
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------


@router.get("/courses", response_class=HTMLResponse)
def list_courses(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    courses = db.query(Course).order_by(Course.created_at.desc()).all()
    return templates.TemplateResponse(request, "admin/courses.html", _ctx(request, user, courses=courses)
    )


@router.post("/courses/{course_id}/publish")
def publish_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    if course.status != CourseStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="يجب اعتماد المقرر عبر مراجعة الجودة (NELC) قبل النشر",
        )
    from datetime import datetime

    course.status = CourseStatus.PUBLISHED
    course.published_at = datetime.utcnow()
    audit_log(db, user, "course.publish", "course", course.public_id)
    db.commit()
    return RedirectResponse("/admin/courses", status_code=303)


@router.post("/courses/{course_id}/archive")
def archive_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    course.status = CourseStatus.ARCHIVED
    audit_log(db, user, "course.archive", "course", course.public_id)
    db.commit()
    return RedirectResponse("/admin/courses", status_code=303)


# ---------------------------------------------------------------------------
# NELC quality reviews
# ---------------------------------------------------------------------------


@router.get("/reviews", response_class=HTMLResponse)
def list_reviews(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_reviewer),
):
    courses = (
        db.query(Course)
        .filter(Course.status.in_([CourseStatus.UNDER_REVIEW, CourseStatus.APPROVED]))
        .order_by(Course.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(request, "admin/reviews.html", _ctx(request, user, courses=courses)
    )


@router.get("/reviews/{course_id}", response_class=HTMLResponse)
def review_course(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_reviewer),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    latest = (
        db.query(QualityReview)
        .filter(QualityReview.course_id == course_id)
        .order_by(QualityReview.reviewed_at.desc())
        .first()
    )
    checklist = latest.checklist if latest else blank_checklist()
    breakdown = domain_breakdown(checklist)
    return templates.TemplateResponse(request, "admin/review_form.html",
        _ctx(
            request,
            user,
            course=course,
            domains=DOMAINS,
            checklist=checklist,
            latest=latest,
            breakdown=breakdown,
            total_score=compute_score(checklist),
        ),
    )


@router.post("/reviews/{course_id}", response_class=HTMLResponse)
async def submit_review(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_reviewer),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")

    form = await request.form()
    state = form.get("state") or ReviewState.PENDING.value
    comments_ar = form.get("comments_ar") or ""

    items = []
    for key, value in form.multi_items():
        if key.startswith("score_"):
            code = key[len("score_") :]
            try:
                score = int(value)
            except ValueError:
                continue
            if 1 <= score <= 3:
                items.append(
                    {
                        "criterion_code": code,
                        "score": score,
                        "evidence": form.get(f"ev_{code}") or "",
                        "note": form.get(f"note_{code}") or "",
                    }
                )

    review = save_review(
        db,
        course=course,
        reviewer=user,
        items=items,
        comments_ar=comments_ar,
        state=ReviewState(state) if state in {s.value for s in ReviewState} else ReviewState.PENDING,
    )
    audit_log(
        db,
        user,
        "course.review",
        "course",
        course.public_id,
        {"state": review.state.value, "score": review.score},
    )
    db.commit()
    return RedirectResponse(f"/admin/reviews/{course_id}", status_code=303)


# ---------------------------------------------------------------------------
# Audit log + reports
# ---------------------------------------------------------------------------


@router.get("/audit", response_class=HTMLResponse)
def audit_view(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    rows = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
    return templates.TemplateResponse(request, "admin/audit.html", _ctx(request, user, rows=rows)
    )


@router.get("/reports/compliance", response_class=HTMLResponse)
def compliance_report(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    courses = db.query(Course).all()
    summary = []
    for course in courses:
        review = (
            db.query(QualityReview)
            .filter(QualityReview.course_id == course.id)
            .order_by(QualityReview.reviewed_at.desc())
            .first()
        )
        summary.append(
            {
                "course": course,
                "score": review.score if review else 0.0,
                "state": review.state.value if review else "—",
            }
        )
    return templates.TemplateResponse(request, "admin/compliance.html", _ctx(request, user, summary=summary)
    )
