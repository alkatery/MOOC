"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .config import get_settings
from .database import get_db, init_db
from .nelc import DOMAINS, total_criteria_count
from .routers import (
    admin,
    assignments,
    auth,
    certificates,
    courses,
    discussions,
    enrollments,
    lessons,
    pages,
    quizzes,
    student,
    teacher,
    xapi,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.platform_name_ar} — {settings.platform_name_en}",
        description=(
            "منصة مساقات إلكترونية مفتوحة متوافقة مع معايير "
            "المركز الوطني للتعليم الإلكتروني (NELC)."
        ),
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # API routers (JSON)
    app.include_router(auth.router)
    app.include_router(courses.router)
    app.include_router(lessons.router)
    app.include_router(quizzes.router)
    app.include_router(assignments.router)
    app.include_router(enrollments.router)
    app.include_router(certificates.router)
    app.include_router(discussions.router)
    app.include_router(xapi.router)

    # Portal routers (HTML)
    app.include_router(pages.router)
    app.include_router(student.router)
    app.include_router(teacher.router)
    app.include_router(admin.router)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "nelc_mode": settings.nelc_compliance_mode,
            "nelc_criteria": total_criteria_count(),
            "nelc_domains": len(DOMAINS),
        }

    return app


app = create_app()
