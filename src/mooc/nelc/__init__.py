"""NELC (المركز الوطني للتعليم الإلكتروني) compliance package.

This package encodes Saudi Arabia's National eLearning Center (NELC)
"Criteria for Excellence in Online Learning" (K-12 rubric v2.0, 2023)
and provides helpers to evaluate a course against those standards.

Source: https://nelc.gov.sa/ — Rubrics of Criteria for Excellence, K-12,
version 2.0, published 12/2023. Licensed under CC BY-NC-SA 4.0.

The platform implements three complementary NELC-aligned layers:

1. ``standards`` — the canonical domain / subdomain / criterion taxonomy
2. ``scoring``   — the 3-level rubric (Emerging / Accomplished / Exemplary)
3. ``checklist`` — an evaluation session that reviewers use to certify a
   course before it can be published.
"""

from .standards import (
    DOMAINS,
    RUBRIC_LEVELS,
    all_criteria,
    criterion_by_code,
    domain_by_code,
    subdomain_by_code,
    taxonomy_summary,
    total_criteria_count,
)

__all__ = [
    "DOMAINS",
    "RUBRIC_LEVELS",
    "all_criteria",
    "criterion_by_code",
    "domain_by_code",
    "subdomain_by_code",
    "taxonomy_summary",
    "total_criteria_count",
]
