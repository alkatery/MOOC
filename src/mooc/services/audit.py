"""Audit log helper."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..models import AuditLog, User


def log(
    db: Session,
    actor: Optional[User],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        metadata_json=metadata or {},
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry
