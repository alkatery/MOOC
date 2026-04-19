"""NELC quality-review scoring."""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from ..models import Course, CourseStatus, QualityReview, ReviewState, User
from ..nelc import DOMAINS, criterion_by_code, total_criteria_count


def blank_checklist() -> Dict[str, Dict[str, object]]:
    """Return an empty evaluation map keyed by criterion code."""
    data: Dict[str, Dict[str, object]] = {}
    for domain in DOMAINS:
        for sd in domain.subdomains:
            for criterion in sd.criteria:
                data[criterion.code] = {
                    "domain": domain.code,
                    "subdomain": sd.code,
                    "score": 0,
                    "evidence": "",
                    "note": "",
                }
    return data


def apply_review_items(
    checklist: Dict[str, Dict[str, object]], items: List[dict]
) -> Dict[str, Dict[str, object]]:
    for item in items:
        code = item.get("criterion_code")
        if not code or code not in checklist:
            continue
        checklist[code]["score"] = int(item.get("score") or 0)
        checklist[code]["evidence"] = item.get("evidence") or ""
        checklist[code]["note"] = item.get("note") or ""
    return checklist


def compute_score(checklist: Dict[str, Dict[str, object]]) -> float:
    """Aggregate rubric scores into a 0–100% compliance percentage."""
    total_criteria = len(checklist)
    if total_criteria == 0:
        return 0.0
    sum_scores = sum(int(v.get("score") or 0) for v in checklist.values())
    max_scores = total_criteria * 3
    return round(sum_scores / max_scores * 100.0, 2)


def domain_breakdown(checklist: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[str, List[int]] = {d.code: [] for d in DOMAINS}
    for code, entry in checklist.items():
        domain = entry.get("domain")
        if domain in grouped:
            grouped[domain].append(int(entry.get("score") or 0))
    rows = []
    for d in DOMAINS:
        scores = grouped[d.code]
        answered = sum(1 for s in scores if s > 0)
        total = len(scores)
        avg = round(sum(scores) / (answered or 1), 2) if answered else 0.0
        rows.append(
            {
                "code": d.code,
                "title_ar": d.title_ar,
                "title_en": d.title_en,
                "answered": answered,
                "total": total,
                "average": avg,
                "percent": round(sum(scores) / (total * 3) * 100.0, 2) if total else 0.0,
            }
        )
    return rows


def save_review(
    db: Session,
    course: Course,
    reviewer: User,
    items: List[dict],
    comments_ar: str = "",
    state: ReviewState = ReviewState.PENDING,
) -> QualityReview:
    checklist = blank_checklist()
    apply_review_items(checklist, items)
    score = compute_score(checklist)

    review = QualityReview(
        course_id=course.id,
        reviewer_id=reviewer.id,
        state=state,
        checklist=checklist,
        score=score,
        comments_ar=comments_ar,
    )
    db.add(review)

    # Sync the course status based on review outcome
    if state == ReviewState.PASSED:
        course.status = CourseStatus.APPROVED
    elif state == ReviewState.FAILED:
        course.status = CourseStatus.REJECTED
    elif state == ReviewState.NEEDS_REVISION:
        course.status = CourseStatus.DRAFT
    db.flush()
    return review


def current_standards_stats() -> Dict[str, int]:
    return {
        "domains": len(DOMAINS),
        "subdomains": sum(d.subdomain_count for d in DOMAINS),
        "criteria": total_criteria_count(),
    }
