"""Authentication routes (JSON API + HTML login/register)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import User, UserRole
from ..schemas import TokenOut, UserCreate, UserLogin, UserOut
from ..security import (
    COOKIE_NAME,
    get_current_user_optional,
    hash_password,
    issue_session_cookie,
    validate_password_strength,
    verify_password,
)
from ..services.audit import log as audit_log

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _auth_ctx(request: Request, **kwargs):
    return {"request": request, "user": None, "settings": get_settings(), **kwargs}


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------


@router.post("/api/auth/register", response_model=TokenOut, status_code=201)
def api_register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="هذا البريد الإلكتروني مستخدم بالفعل")

    pwd_err = validate_password_strength(payload.password)
    if pwd_err:
        raise HTTPException(status_code=400, detail=pwd_err)

    if not payload.consent_privacy:
        raise HTTPException(
            status_code=400,
            detail="يجب الموافقة على سياسة الخصوصية لاستخدام المنصة",
        )

    user = User(
        email=payload.email,
        full_name_ar=payload.full_name_ar,
        full_name_en=payload.full_name_en,
        national_id=payload.national_id,
        password_hash=hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
        preferred_language=payload.preferred_language,
        consent_privacy=payload.consent_privacy,
        consent_timestamp=datetime.utcnow(),
    )
    db.add(user)
    db.flush()

    audit_log(
        db,
        actor=user,
        action="user.register",
        entity_type="user",
        entity_id=user.public_id,
        metadata={"role": user.role.value},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    token = issue_session_cookie(user)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/api/auth/login", response_model=TokenOut)
def api_login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="الحساب معطّل — يرجى التواصل مع الإدارة")

    user.last_login_at = datetime.utcnow()
    audit_log(
        db,
        actor=user,
        action="user.login",
        entity_type="user",
        entity_id=user.public_id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    token = issue_session_cookie(user)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


# ---------------------------------------------------------------------------
# HTML forms
# ---------------------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "auth/login.html", _auth_ctx(request, error=None))


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            _auth_ctx(request, error="بيانات الدخول غير صحيحة"),
            status_code=401,
        )
    if not user.is_active:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            _auth_ctx(request, error="الحساب معطّل"),
            status_code=403,
        )
    user.last_login_at = datetime.utcnow()
    audit_log(
        db,
        actor=user,
        action="user.login.web",
        entity_type="user",
        entity_id=user.public_id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    target = "/"
    if user.role == UserRole.ADMIN:
        target = "/admin"
    elif user.role == UserRole.INSTRUCTOR:
        target = "/teacher"
    elif user.role == UserRole.STUDENT:
        target = "/student"
    response = RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        COOKIE_NAME,
        issue_session_cookie(user),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request, "auth/register.html", _auth_ctx(request, error=None)
    )


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(...),
    full_name_ar: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    role: str = Form("student"),
    consent: str = Form("off"),
    db: Session = Depends(get_db),
):
    def error(msg: str, code: int = 400):
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            _auth_ctx(request, error=msg),
            status_code=code,
        )

    if password != password_confirm:
        return error("كلمتا المرور غير متطابقتين")
    pwd_err = validate_password_strength(password)
    if pwd_err:
        return error(pwd_err)
    if consent != "on":
        return error("يجب الموافقة على سياسة الخصوصية")
    if db.query(User).filter(User.email == email).first():
        return error("هذا البريد مستخدم من قبل")

    role_enum = UserRole.STUDENT if role not in {r.value for r in UserRole} else UserRole(role)
    if role_enum == UserRole.ADMIN:
        role_enum = UserRole.STUDENT  # Block self-service admin

    user = User(
        email=email,
        full_name_ar=full_name_ar,
        password_hash=hash_password(password),
        role=role_enum,
        consent_privacy=True,
        consent_timestamp=datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    audit_log(
        db,
        actor=user,
        action="user.register.web",
        entity_type="user",
        entity_id=user.public_id,
        metadata={"role": user.role.value},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    target = "/student" if user.role == UserRole.STUDENT else "/teacher"
    response = RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        COOKIE_NAME,
        issue_session_cookie(user),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE_NAME)
    return response
