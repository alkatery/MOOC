"""منصة المساقات المفتوحة (MOOC Platform).

نظام تعليمي مفتوح المصدر مبني على مبدأ MOOC ومتوافق مع متطلبات
المركز الوطني للتعليم الإلكتروني (NELC) بالمملكة العربية السعودية.

This package implements a full-stack MOOC platform that covers the key
requirements outlined by Saudi Arabia's National eLearning Center (NELC):

* Interoperability (SCORM 1.2/2004 import + xAPI statement pipeline)
* Learner tracking, progress, and analytics
* Accessible Arabic-first RTL experience (WCAG 2.1 AA)
* Role-based authentication (student / instructor / admin / reviewer)
* Structured courses, lessons, quizzes, assignments, and discussions
* Certification with verifiable IDs
* Course quality review workflow aligned with NELC checklist
* Data-privacy friendly audit log

The package is intentionally self-contained so it can run with only Python
standard libraries plus the FastAPI/SQLAlchemy stack declared in
``pyproject.toml``.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
