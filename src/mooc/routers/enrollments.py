"""Enrollment routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Course, CourseStatus, Enrollment, User
from ..schemas import EnrollmentOut
from ..security import get_current_user
from ..services import xapi
from ..services.audit import log as audit_log
from ..services.certificates import issue_certificate
from ..services.grading import compute_final_grade

router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])


@router.post("/{course_id}", response_model=EnrollmentOut, status_code=201)
def enroll(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course.status != CourseStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="المقرر غير متاح للتسجيل")
    existing = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        .first()
    )
    if existing:
        return existing

    enrollment = Enrollment(user_id=user.id, course_id=course_id)
    db.add(enrollment)
    db.flush()
    xapi.record_statement(
        db,
        actor=user,
        verb="registered",
        object_type="course",
        object_id=course.id,
    )
    audit_log(db, user, "enrollment.create", "enrollment", enrollment.id)
    db.commit()
    return enrollment


@router.get("", response_model=List[EnrollmentOut])
def list_my_enrollments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Enrollment).filter(Enrollment.user_id == user.id).all()


@router.post("/{enrollment_id}/finalize")
def finalize(
    enrollment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.id == enrollment_id, Enrollment.user_id == user.id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="التسجيل غير موجود")

    grade = compute_final_grade(db, enrollment)
    enrollment.final_grade = grade

    certificate = None
    course = enrollment.course
    if enrollment.progress_percent >= 100.0 and grade >= course.passing_grade:
        certificate = issue_certificate(db, enrollment, grade)
        xapi.record_statement(
            db,
            actor=user,
            verb="earned",
            object_type="certificate",
            object_id=certificate.verification_code,
            result={"score": {"raw": grade, "max": 100}},
        )

    audit_log(db, user, "enrollment.finalize", "enrollment", enrollment.id)
    db.commit()
    return {
        "status": "ok",
        "final_grade": grade,
        "certificate_code": certificate.verification_code if certificate else None,
    }
