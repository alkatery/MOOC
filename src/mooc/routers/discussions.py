"""Discussion forum routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Course, DiscussionPost, DiscussionThread, Enrollment, User
from ..security import get_current_user
from ..services.audit import log as audit_log

router = APIRouter(prefix="/api/discussions", tags=["discussions"])


class ThreadIn(BaseModel):
    title_ar: str
    body_ar: str


class PostIn(BaseModel):
    body_ar: str


@router.post("/course/{course_id}/threads", status_code=201)
def create_thread(
    course_id: int,
    payload: ThreadIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not db.query(Course).filter(Course.id == course_id).first():
        raise HTTPException(status_code=404, detail="المقرر غير موجود")
    thread = DiscussionThread(
        course_id=course_id,
        author_id=user.id,
        title_ar=payload.title_ar,
        body_ar=payload.body_ar,
    )
    db.add(thread)
    db.flush()
    audit_log(db, user, "thread.create", "thread", thread.id)
    db.commit()
    return {"id": thread.id, "title_ar": thread.title_ar}


@router.post("/threads/{thread_id}/posts", status_code=201)
def reply(
    thread_id: int,
    payload: PostIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    thread = db.query(DiscussionThread).filter(DiscussionThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="الموضوع غير موجود")
    if thread.is_locked:
        raise HTTPException(status_code=400, detail="الموضوع مغلق")
    post = DiscussionPost(thread_id=thread_id, author_id=user.id, body_ar=payload.body_ar)
    db.add(post)
    db.flush()
    audit_log(db, user, "post.create", "post", post.id)
    db.commit()
    return {"id": post.id}


@router.get("/course/{course_id}/threads")
def list_threads(course_id: int, db: Session = Depends(get_db)):
    threads = (
        db.query(DiscussionThread)
        .filter(DiscussionThread.course_id == course_id)
        .order_by(DiscussionThread.is_pinned.desc(), DiscussionThread.created_at.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "title_ar": t.title_ar,
            "author_id": t.author_id,
            "created_at": t.created_at,
            "is_pinned": t.is_pinned,
            "is_locked": t.is_locked,
            "posts_count": len(t.posts),
        }
        for t in threads
    ]
