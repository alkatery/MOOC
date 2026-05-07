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

from .course_requirements import (
    COURSE_REQUIREMENTS,
    CourseRequirement,
    RequirementLevel,
    all_requirements,
    excellence_requirements,
    mandatory_requirements,
    optional_requirements,
    requirement_by_code,
    requirements_by_level,
    requirements_summary,
)
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
    "COURSE_REQUIREMENTS",
    "CourseRequirement",
    "DOMAINS",
    "RUBRIC_LEVELS",
    "RequirementLevel",
    "all_criteria",
    "all_requirements",
    "criterion_by_code",
    "domain_by_code",
    "excellence_requirements",
    "mandatory_requirements",
    "optional_requirements",
    "requirement_by_code",
    "requirements_by_level",
    "requirements_summary",
    "subdomain_by_code",
    "taxonomy_summary",
    "total_criteria_count",
]
