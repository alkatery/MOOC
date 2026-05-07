"""Tenant resolution + helpers (multi-tenant SaaS).

Each request belongs to exactly one :class:`~mooc.models.Tenant`. The
resolution order is:

1. ``X-Tenant-Slug`` HTTP header (used by API clients and tests)
2. ``Host`` header subdomain — e.g. ``acme.mooc.sa`` → slug ``acme``
3. ``custom_domain`` — full Host matched against ``Tenant.custom_domain``
4. ``mooc_tenant`` cookie (sticky after explicit selection)
5. ``?t=slug`` query parameter (manual override / dev convenience)
6. The default tenant marked ``slug='default'`` (created by the seed)

If nothing matches we return ``None`` and route handlers can decide
whether to redirect to ``/signup`` or render a generic landing.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Tenant


_DEFAULT_SLUG = "default"
_RESERVED_SUBDOMAINS = {"www", "api", "admin", "static", "assets", "cdn"}


def _slug_from_host(host: str) -> Optional[str]:
    if not host:
        return None
    bare = host.split(":")[0].lower()
    parts = bare.split(".")
    if len(parts) < 3:  # bare domain or localhost
        return None
    sub = parts[0]
    if sub in _RESERVED_SUBDOMAINS:
        return None
    return sub


def resolve_tenant(
    request: Request, db: Session = Depends(get_db)
) -> Optional[Tenant]:
    """FastAPI dependency: pick the active tenant for this request."""
    # 1) explicit header
    slug = request.headers.get("X-Tenant-Slug")
    if slug:
        tenant = _by_slug(db, slug)
        if tenant:
            return tenant

    host = (request.headers.get("host") or "").split(":")[0].lower()

    # 2) custom domain match
    if host:
        custom = (
            db.query(Tenant)
            .filter(Tenant.custom_domain == host, Tenant.is_active.is_(True))
            .first()
        )
        if custom:
            return custom

    # 3) subdomain
    sub = _slug_from_host(host)
    if sub:
        tenant = _by_slug(db, sub)
        if tenant:
            return tenant

    # 4) cookie
    cookie_slug = request.cookies.get("mooc_tenant")
    if cookie_slug:
        tenant = _by_slug(db, cookie_slug)
        if tenant:
            return tenant

    # 5) query param
    qs_slug = request.query_params.get("t")
    if qs_slug:
        tenant = _by_slug(db, qs_slug)
        if tenant:
            return tenant

    # 6) default
    return _by_slug(db, _DEFAULT_SLUG)


def require_tenant(tenant: Tenant = Depends(resolve_tenant)) -> Tenant:
    if not tenant:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=(
                "لا توجد منصة مطابقة. أنشئ منصة جديدة عبر /signup أو اختر "
                "منصة موجودة."
            ),
        )
    return tenant


def _by_slug(db: Session, slug: str) -> Optional[Tenant]:
    return (
        db.query(Tenant)
        .filter(Tenant.slug == slug.lower(), Tenant.is_active.is_(True))
        .first()
    )


def tenant_by_slug(db: Session, slug: str) -> Optional[Tenant]:
    """Public lookup helper used by routers."""
    return _by_slug(db, slug)


def tenant_branding_css(tenant: Tenant) -> str:
    """Inline CSS variables for a tenant's theme — injected into base.html."""
    return (
        f":root{{--brand-primary:{tenant.primary_color};"
        f"--brand-accent:{tenant.accent_color};"
        f"--brand-bg:{tenant.background_color};"
        f"--brand-text:{tenant.text_color};}}"
    )


def tenant_label(tenant: Tenant, key: str, default: str) -> str:
    """Look up a tenant-customized label, falling back to default."""
    labels = tenant.custom_labels or {}
    return labels.get(key) or default
