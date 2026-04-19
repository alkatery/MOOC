"""xAPI (Experience API / Tin Can) statement recording.

Implements a subset of the xAPI specification that covers the common
learning verbs NELC compliance expects to be traceable:

* http://adlnet.gov/expapi/verbs/registered  (course enrollment)
* http://adlnet.gov/expapi/verbs/launched    (lesson start)
* http://adlnet.gov/expapi/verbs/experienced (lesson view)
* http://adlnet.gov/expapi/verbs/completed   (lesson/course completion)
* http://adlnet.gov/expapi/verbs/attempted   (quiz start)
* http://adlnet.gov/expapi/verbs/answered    (question answer)
* http://adlnet.gov/expapi/verbs/scored      (quiz score)
* http://adlnet.gov/expapi/verbs/passed / failed
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..models import User, XAPIStatement


VERBS = {
    "registered": "http://adlnet.gov/expapi/verbs/registered",
    "launched": "http://adlnet.gov/expapi/verbs/launched",
    "experienced": "http://adlnet.gov/expapi/verbs/experienced",
    "completed": "http://adlnet.gov/expapi/verbs/completed",
    "attempted": "http://adlnet.gov/expapi/verbs/attempted",
    "answered": "http://adlnet.gov/expapi/verbs/answered",
    "scored": "http://adlnet.gov/expapi/verbs/scored",
    "passed": "http://adlnet.gov/expapi/verbs/passed",
    "failed": "http://adlnet.gov/expapi/verbs/failed",
    "earned": "http://id.tincanapi.com/verb/earned",
}


def record_statement(
    db: Session,
    actor: User,
    verb: str,
    object_type: str,
    object_id: str,
    *,
    result: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    commit: bool = False,
) -> XAPIStatement:
    """Persist a new xAPI statement.

    ``verb`` can be a short key (``"completed"``) or a full IRI.
    """
    verb_iri = VERBS.get(verb, verb)
    stmt = XAPIStatement(
        actor_id=actor.id,
        verb=verb_iri,
        object_type=object_type,
        object_id=str(object_id),
        result=result or {},
        context=context or {},
    )
    db.add(stmt)
    if commit:
        db.commit()
    else:
        db.flush()
    return stmt


def statement_to_dict(stmt: XAPIStatement, actor_email: str) -> Dict[str, Any]:
    """Render a statement in the standard xAPI 1.0.3 JSON shape."""
    return {
        "id": stmt.statement_id,
        "actor": {
            "objectType": "Agent",
            "mbox": f"mailto:{actor_email}",
        },
        "verb": {"id": stmt.verb},
        "object": {
            "id": f"urn:mooc:{stmt.object_type}:{stmt.object_id}",
            "definition": {"type": f"http://adlnet.gov/expapi/activities/{stmt.object_type}"},
        },
        "result": stmt.result or None,
        "context": stmt.context or None,
        "stored": stmt.stored_at.isoformat() if stmt.stored_at else datetime.utcnow().isoformat(),
    }
