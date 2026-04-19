"""Tests for the NELC quality-review scoring service."""

from __future__ import annotations

from mooc.nelc import all_criteria
from mooc.services.review import (
    apply_review_items,
    blank_checklist,
    compute_score,
    current_standards_stats,
    domain_breakdown,
)


def test_blank_checklist_covers_all_criteria():
    checklist = blank_checklist()
    assert len(checklist) == sum(1 for _ in all_criteria())
    for entry in checklist.values():
        assert entry["score"] == 0


def test_compute_score_blank_is_zero():
    checklist = blank_checklist()
    assert compute_score(checklist) == 0.0


def test_apply_and_compute_perfect_score():
    checklist = blank_checklist()
    items = [{"criterion_code": code, "score": 3} for code in checklist.keys()]
    apply_review_items(checklist, items)
    assert compute_score(checklist) == 100.0


def test_domain_breakdown_returns_rows_for_each_domain():
    checklist = blank_checklist()
    rows = domain_breakdown(checklist)
    assert len(rows) == 8


def test_current_standards_stats_matches_taxonomy():
    stats = current_standards_stats()
    assert stats["domains"] == 8
