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
from ..nelc import DOMAINS, total_criteria_count
from ..security import get_current_user_optional

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _context(request: Request, user, **kwargs):
    settings = get_settings()
    base = {
        "request": request,
        "user": user,
        "settings": settings,
        "nelc_domains": DOMAINS,
        "nelc_total_criteria": total_criteria_count(),
    }
    base.update(kwargs)
    return base


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    courses = (
        db.query(Course)
        .filter(Course.status == CourseStatus.PUBLISHED)
        .order_by(Course.published_at.desc().nullslast())
        .limit(6)
        .all()
    )
    categories = db.query(Category).order_by(Category.name_ar).all()
    stats = {
        "courses": db.query(Course).filter(Course.status == CourseStatus.PUBLISHED).count(),
        "categories": len(categories),
    }
    return templates.TemplateResponse(request, "home.html",
        _context(request, user, courses=courses, categories=categories, stats=stats),
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
    if q:
        query = query.filter(Course.title_ar.ilike(f"%{q}%"))
    if category:
        query = query.filter(Course.category_id == category)
    courses = query.order_by(Course.published_at.desc().nullslast()).all()
    categories = db.query(Category).all()
    return templates.TemplateResponse(request, "catalog.html",
        _context(
            request, user, courses=courses, categories=categories, q=q or "", selected=category
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
        return templates.TemplateResponse(request, "404.html", _context(request, user), status_code=404
        )
    return templates.TemplateResponse(request, "course_detail.html", _context(request, user, course=course)
    )


@router.get("/about", response_class=HTMLResponse)
def about(request: Request, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(request, "about.html", _context(request, user))


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(request, "privacy.html", _context(request, user))


@router.get("/nelc-standards", response_class=HTMLResponse)
def nelc_standards(request: Request, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(request, "nelc_standards.html", _context(request, user)
    )


@router.get("/verify-certificate", response_class=HTMLResponse)
def verify_page(request: Request, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(request, "verify_certificate.html", _context(request, user, result=None)
    )
