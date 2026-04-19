"""Tests for the NELC standards taxonomy module."""

from __future__ import annotations

from mooc.nelc import (
    DOMAINS,
    RUBRIC_LEVELS,
    all_criteria,
    criterion_by_code,
    domain_by_code,
    subdomain_by_code,
    taxonomy_summary,
    total_criteria_count,
)


def test_domains_are_eight():
    """NELC K-12 Excellence Standards define eight top-level domains (K.1–K.8)."""
    codes = [d.code for d in DOMAINS]
    assert codes == ["K.1", "K.2", "K.3", "K.4", "K.5", "K.6", "K.7", "K.8"]


def test_subdomain_count():
    total = sum(d.subdomain_count for d in DOMAINS)
    # The published rubric has ~43 subdomains
    assert total >= 40


def test_criteria_are_unique():
    codes = [c.code for c in all_criteria()]
    assert len(codes) == len(set(codes))
    assert total_criteria_count() == len(codes)


def test_rubric_has_three_levels():
    assert len(RUBRIC_LEVELS) == 3
    values = [level[0] for level in RUBRIC_LEVELS]
    assert values == [1, 2, 3]


def test_lookup_helpers():
    assert domain_by_code("K.4").title_en == "Online Course Design"
    assert subdomain_by_code("K.4.2").title_en.startswith("Course Design")
    c = criterion_by_code("K.1.1.1")
    assert c is not None
    assert "رؤية" in c.title_ar


def test_taxonomy_summary():
    summary = taxonomy_summary()
    assert summary["domains"] == 8
    assert summary["criteria"] == total_criteria_count()
