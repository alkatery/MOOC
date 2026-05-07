"""Template-context helpers and Jinja globals for multi-tenant rendering.

Every router that renders HTML calls a small ``base_context()`` builder
that adds the active :class:`~mooc.models.Tenant`, the navbar's
published custom pages, and a ``tenant_label`` helper. The base
template handles missing tenant gracefully (falls back to platform
defaults), so this is best-effort enrichment, not a hard dependency.
"""

from __future__ import annotations

import importlib
from typing import Iterable, Optional

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .models import Tenant, TenantPage
from .services.tenants import tenant_by_slug, tenant_label


def _resolve_tenant(request: Request, db: Session) -> Optional[Tenant]:
    slug = request.headers.get("X-Tenant-Slug")
    if slug:
        t = tenant_by_slug(db, slug)
        if t:
            return t
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if host:
        t = (
            db.query(Tenant)
            .filter(Tenant.custom_domain == host, Tenant.is_active.is_(True))
            .first()
        )
        if t:
            return t
        if host.count(".") >= 2:
            sub = host.split(".")[0]
            if sub not in {"www", "api", "admin"}:
                t = tenant_by_slug(db, sub)
                if t:
                    return t
    cookie = request.cookies.get("mooc_tenant")
    if cookie:
        t = tenant_by_slug(db, cookie)
        if t:
            return t
    qs = request.query_params.get("t")
    if qs:
        t = tenant_by_slug(db, qs)
        if t:
            return t
    return tenant_by_slug(db, "default")


def _nav_pages(db: Session, tenant: Optional[Tenant]) -> Iterable[TenantPage]:
    if not tenant:
        return []
    return (
        db.query(TenantPage)
        .filter(
            TenantPage.tenant_id == tenant.id,
            TenantPage.is_published.is_(True),
            TenantPage.show_in_nav.is_(True),
        )
        .order_by(TenantPage.order_index, TenantPage.created_at)
        .all()
    )


def base_context(request: Request, db: Session, **extra) -> dict:
    """Standard context dict used by HTML routers."""
    tenant = extra.pop("tenant", None) or _resolve_tenant(request, db)
    ctx = {
        "request": request,
        "tenant": tenant,
        "nav_pages": _nav_pages(db, tenant),
    }
    ctx.update(extra)
    return ctx


def install_template_globals(app: FastAPI) -> None:
    """Register ``tenant_label`` as a Jinja global on every router env."""
    from jinja2 import pass_context

    @pass_context
    def _label(ctx, key: str, default: str) -> str:
        t = ctx.get("tenant") if hasattr(ctx, "get") else None
        return tenant_label(t, key, default) if t else default

    router_modules = (
        "mooc.routers.pages",
        "mooc.routers.student",
        "mooc.routers.teacher",
        "mooc.routers.admin",
        "mooc.routers.auth",
        "mooc.routers.saas",
    )
    seen: set[int] = set()
    for mod_name in router_modules:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        jt = getattr(mod, "templates", None)
        if not isinstance(jt, Jinja2Templates) or id(jt) in seen:
            continue
        seen.add(id(jt))
        jt.env.globals["tenant_label"] = _label
