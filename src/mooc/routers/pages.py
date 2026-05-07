"""Public HTML pages: home, catalog, course detail, about."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Category, Course, CourseStatus
from ..nelc import (
    DOMAINS,
    excellence_requirements,
    mandatory_requirements,
    optional_requirements,
    requirements_summary,
    total_criteria_count,
)
from ..security import get_current_user_optional

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _context(request: Request, user, db: Session = None, **kwargs):
    from ..templating import base_context

    settings = get_settings()
    base = {
        "user": user,
        "settings": settings,
        "nelc_domains": DOMAINS,
        "nelc_total_criteria": total_criteria_count(),
    }
    base.update(kwargs)
    if db is not None:
        base = base_context(request, db, **base)
    else:
        base["request"] = request
    return base


def _scope_to_tenant(query, request, db, model):
    """Filter a query to courses owned by the current tenant (if any).

    Falls back to global rows (``tenant_id IS NULL``) so legacy seed
    data still appears when no tenant is selected.
    """
    from ..templating import _resolve_tenant

    tenant = _resolve_tenant(request, db)
    if tenant:
        return query.filter(
            (model.tenant_id == tenant.id) | (model.tenant_id.is_(None))
        )
    return query


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    courses_q = db.query(Course).filter(Course.status == CourseStatus.PUBLISHED)
    courses_q = _scope_to_tenant(courses_q, request, db, Course)
    courses = courses_q.order_by(Course.published_at.desc().nullslast()).limit(6).all()
    categories = db.query(Category).order_by(Category.name_ar).all()
    stats = {
        "courses": _scope_to_tenant(
            db.query(Course).filter(Course.status == CourseStatus.PUBLISHED),
            request, db, Course,
        ).count(),
        "categories": len(categories),
    }
    return templates.TemplateResponse(
        request,
        "home.html",
        _context(request, user, db, courses=courses, categories=categories, stats=stats),
    )


@router.get("/catalog", response_class=HTMLResponse)
def catalog(
    request: Request,
    q: str | None = None,
    category: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    query = db.query(Course).filter(Course.status == CourseStatus.PUBLISHED)
    query = _scope_to_tenant(query, request, db, Course)
    if q:
        query = query.filter(Course.title_ar.ilike(f"%{q}%"))
    if category:
        query = query.filter(Course.category_id == category)
    courses = query.order_by(Course.published_at.desc().nullslast()).all()
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        request,
        "catalog.html",
        _context(
            request, user, db,
            courses=courses, categories=categories, q=q or "", selected=category,
        ),
    )


@router.get("/courses/{course_id}", response_class=HTMLResponse)
def course_detail(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates.TemplateResponse(
            request, "404.html", _context(request, user, db), status_code=404
        )
    return templates.TemplateResponse(
        request, "course_detail.html", _context(request, user, db, course=course)
    )


@router.get("/about", response_class=HTMLResponse)
def about(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        request, "about.html", _context(request, user, db)
    )


@router.get("/privacy", response_class=HTMLResponse)
def privacy(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        request, "privacy.html", _context(request, user, db)
    )


@router.get("/nelc-standards", response_class=HTMLResponse)
def nelc_standards(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        request, "nelc_standards.html", _context(request, user, db)
    )


@router.get("/nelc/course-requirements", response_class=HTMLResponse)
def nelc_course_requirements(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        request,
        "nelc_course_requirements.html",
        _context(
            request, user, db,
            mandatory=mandatory_requirements(),
            optional=optional_requirements(),
            excellence=excellence_requirements(),
            req_summary=requirements_summary(),
        ),
    )


@router.get("/verify-certificate", response_class=HTMLResponse)
def verify_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        request, "verify_certificate.html",
        _context(request, user, db, result=None),
    )
