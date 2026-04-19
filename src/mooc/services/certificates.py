"""Certificate issuance and verification."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Certificate, Course, Enrollment, User
from ..security import hmac_signature, random_token


def _build_verification_code(enrollment: Enrollment) -> str:
    base = f"{enrollment.user_id}-{enrollment.course_id}-{enrollment.id}-{random_token(6)}"
    sig = hmac_signature(base)
    return f"MOOC-{sig}".upper()


def issue_certificate(
    db: Session, enrollment: Enrollment, grade: float
) -> Certificate:
    """Create (or fetch) a certificate for a completed enrollment."""
    existing = (
        db.query(Certificate)
        .filter(Certificate.enrollment_id == enrollment.id, Certificate.revoked.is_(False))
        .first()
    )
    if existing:
        return existing

    settings = get_settings()
    expires = None
    if settings.certificate_valid_years > 0:
        expires = datetime.utcnow() + timedelta(days=365 * settings.certificate_valid_years)

    cert = Certificate(
        verification_code=_build_verification_code(enrollment),
        user_id=enrollment.user_id,
        course_id=enrollment.course_id,
        enrollment_id=enrollment.id,
        grade=grade,
        expires_at=expires,
    )
    db.add(cert)
    db.flush()
    return cert


def verify_code(db: Session, code: str) -> Optional[Certificate]:
    return (
        db.query(Certificate)
        .filter(Certificate.verification_code == code.upper().strip())
        .first()
    )
