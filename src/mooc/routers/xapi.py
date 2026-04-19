"""xAPI (Tin Can) statement endpoint — lightweight LRS subset."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, XAPIStatement
from ..security import get_current_user
from ..services import xapi as xapi_service

router = APIRouter(prefix="/api/xapi", tags=["xapi"])


class StatementIn(BaseModel):
    verb: str
    object_type: str
    object_id: str
    result: dict | None = None
    context: dict | None = None


@router.post("/statements", status_code=201)
def post_statement(
    payload: StatementIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = xapi_service.record_statement(
        db,
        actor=user,
        verb=payload.verb,
        object_type=payload.object_type,
        object_id=payload.object_id,
        result=payload.result,
        context=payload.context,
    )
    db.commit()
    return {"id": stmt.statement_id}


@router.get("/statements")
def list_statements(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmts = (
        db.query(XAPIStatement)
        .filter(XAPIStatement.actor_id == user.id)
        .order_by(XAPIStatement.stored_at.desc())
        .limit(limit)
        .all()
    )
    return [
        xapi_service.statement_to_dict(s, user.email) for s in stmts
    ]
