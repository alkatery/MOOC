"""Certificate verification and viewing."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Certificate, Course, User
from ..services.certificates import verify_code

router = APIRouter(tags=["certificates"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/api/certificates/verify/{code}")
def api_verify(code: str, db: Session = Depends(get_db)):
    cert = verify_code(db, code)
    if not cert or cert.revoked:
        raise HTTPException(status_code=404, detail="شهادة غير صالحة أو مُلغاة")
    course = db.query(Course).filter(Course.id == cert.course_id).first()
    user = db.query(User).filter(User.id == cert.user_id).first()
    return {
        "verification_code": cert.verification_code,
        "issued_at": cert.issued_at,
        "expires_at": cert.expires_at,
        "grade": cert.grade,
        "holder": user.display_name if user else "",
        "course_title": course.title_ar if course else "",
        "course_code": course.code if course else "",
    }


@router.get("/certificates/{code}", response_class=HTMLResponse)
def view_certificate(code: str, request: Request, db: Session = Depends(get_db)):
    cert = verify_code(db, code)
    if not cert or cert.revoked:
        raise HTTPException(status_code=404, detail="شهادة غير صالحة")
    course = db.query(Course).filter(Course.id == cert.course_id).first()
    holder = db.query(User).filter(User.id == cert.user_id).first()
    return templates.TemplateResponse(request, "certificate.html",
        {
            "request": request,
            "certificate": cert,
            "course": course,
            "holder": holder,
        },
    )
