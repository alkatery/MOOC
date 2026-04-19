"""Assignment routes."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Assignment,
    AssignmentSubmission,
    Course,
    Enrollment,
    User,
    UserRole,
)
from ..schemas import AssignmentIn, AssignmentOut, SubmissionIn, SubmissionOut
from ..security import get_current_user, require_instructor
from ..services.audit import log as audit_log

router = APIRouter(prefix="/api", tags=["assignments"])


@router.post(
    "/courses/{course_id}/assignments",
    response_model=AssignmentOut,
    status_code=201,
)
def create_assignment(
    course_id: int,
    payload: AssignmentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")
    assignment = Assignment(
        course_id=course_id,
        title_ar=payload.title_ar,
        instructions_ar=payload.instructions_ar,
        due_at=payload.due_at,
        max_score=payload.max_score,
        rubric=payload.rubric,
    )
    db.add(assignment)
    db.flush()
    audit_log(db, user, "assignment.create", "assignment", assignment.id)
    db.commit()
    return assignment


@router.get("/courses/{course_id}/assignments", response_model=List[AssignmentOut])
def list_assignments(course_id: int, db: Session = Depends(get_db)):
    return db.query(Assignment).filter(Assignment.course_id == course_id).all()


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=SubmissionOut,
    status_code=201,
)
def submit_assignment(
    assignment_id: int,
    payload: SubmissionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="التكليف غير موجود")
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.course_id == assignment.course_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=400, detail="أنت غير مسجّل في هذا المقرر")

    submission = AssignmentSubmission(
        assignment_id=assignment_id,
        user_id=user.id,
        content=payload.content,
        attachment_url=payload.attachment_url,
    )
    db.add(submission)
    db.flush()
    audit_log(db, user, "submission.create", "submission", submission.id)
    db.commit()
    return submission


@router.post("/submissions/{submission_id}/grade", response_model=SubmissionOut)
def grade_submission(
    submission_id: int,
    score: float,
    feedback_ar: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(require_instructor),
):
    submission = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="التسليم غير موجود")
    submission.score = score
    submission.feedback_ar = feedback_ar
    submission.graded_at = datetime.utcnow()
    submission.graded_by_id = user.id
    audit_log(db, user, "submission.grade", "submission", submission.id)
    db.commit()
    return submission
