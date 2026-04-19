"""Password hashing, token generation, role-based access helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User, UserRole


# ---------------------------------------------------------------------------
# Password hashing (pbkdf2-sha256 — no external deps needed)
# ---------------------------------------------------------------------------


_PBKDF2_ITERATIONS = 260_000
_PBKDF2_ALGO = "sha256"
_SALT_BYTES = 16


class JWTError(Exception):
    pass


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Return a ``pbkdf2_sha256$<iter>$<salt>$<hash>`` style string."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return (
        f"pbkdf2_{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, iters, salt_b64, hash_b64 = password_hash.split("$")
    except ValueError:
        return False
    if not algo.startswith("pbkdf2_"):
        return False
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    digest = hashlib.pbkdf2_hmac(
        algo.replace("pbkdf2_", ""),
        password.encode("utf-8"),
        salt,
        int(iters),
    )
    return hmac.compare_digest(digest, expected)


# ---------------------------------------------------------------------------
# Minimal JWT-like HS256 implementation
# ---------------------------------------------------------------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding and padding < 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("ascii"))


def _jwt_encode(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b = _b64url(
        json.dumps(payload, separators=(",", ":"), default=str).encode()
    )
    signing_input = f"{header_b}.{payload_b}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header_b}.{payload_b}.{_b64url(sig)}"


def _jwt_decode(token: str, secret: str) -> dict:
    try:
        header_b, payload_b, sig_b = token.split(".")
    except ValueError as exc:
        raise JWTError("Malformed token") from exc
    signing_input = f"{header_b}.{payload_b}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_decode(sig_b), expected_sig):
        raise JWTError("Invalid signature")
    payload = json.loads(_b64url_decode(payload_b))
    exp = payload.get("exp")
    if exp and datetime.utcnow().timestamp() > float(exp):
        raise JWTError("Token expired")
    return payload


def validate_password_strength(password: str) -> Optional[str]:
    settings = get_settings()
    if len(password) < settings.password_min_length:
        return f"كلمة المرور يجب أن تكون {settings.password_min_length} أحرف على الأقل"
    if settings.password_require_complexity:
        has_alpha = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        if not (has_alpha and has_digit):
            return "كلمة المرور يجب أن تحتوي على أحرف وأرقام"
    return None


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------


def create_access_token(subject: str, role: str, extra: dict | None = None) -> str:
    settings = get_settings()
    now = datetime.utcnow()
    expire = now + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire.timestamp(),
        "iat": now.timestamp(),
    }
    if extra:
        payload.update(extra)
    return _jwt_encode(payload, settings.secret_key)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return _jwt_decode(token, settings.secret_key)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# Session cookies (for the server-rendered web UI)
# ---------------------------------------------------------------------------

COOKIE_NAME = "mooc_session"


def issue_session_cookie(user: User) -> str:
    return create_access_token(
        subject=user.public_id,
        role=user.role.value,
        extra={"uid": user.id, "name": user.display_name},
    )


def _current_user_from_token(token: str, db: Session) -> User:
    payload = decode_token(token)
    user_pid = payload.get("sub")
    if not user_pid:
        raise HTTPException(status_code=401, detail="Invalid session token")
    user = db.query(User).filter(User.public_id == user_pid).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    return user


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="جلسة غير موجودة — يرجى تسجيل الدخول",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _current_user_from_token(token, db)


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return _current_user_from_token(token, db)
    except HTTPException:
        return None


def require_roles(*roles: UserRole):
    allowed = set(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="غير مصرح لك بالوصول إلى هذه الصفحة",
            )
        return user

    return dependency


require_student = require_roles(UserRole.STUDENT, UserRole.INSTRUCTOR, UserRole.ADMIN)
require_instructor = require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)
require_reviewer = require_roles(UserRole.REVIEWER, UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)


# ---------------------------------------------------------------------------
# Verification codes for certificates
# ---------------------------------------------------------------------------


def hmac_signature(message: str) -> str:
    settings = get_settings()
    mac = hmac.new(settings.secret_key.encode(), message.encode(), hashlib.sha256)
    return mac.hexdigest()[:16]


def random_token(nbytes: int = 16) -> str:
    return secrets.token_urlsafe(nbytes)
