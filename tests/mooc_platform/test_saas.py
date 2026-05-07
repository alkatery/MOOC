"""SaaS / multi-tenant tests."""

from __future__ import annotations

import uuid

import pytest

from mooc.database import session_scope
from mooc.models import (
    BillingPeriod,
    Subscription,
    SubscriptionPlan,
    SubscriptionPlanCode,
    SubscriptionStatus,
    Tenant,
    TenantPage,
    User,
    UserRole,
)
from mooc.security import hash_password
from mooc.services.tenants import tenant_branding_css, tenant_label


# ---------------------------------------------------------------------------
# Catalog seed
# ---------------------------------------------------------------------------


def test_seed_creates_default_tenant_and_plans():
    from mooc.seed import run_seed

    run_seed()
    with session_scope() as db:
        plans = db.query(SubscriptionPlan).all()
        codes = {p.code for p in plans}
        assert codes == {
            SubscriptionPlanCode.FREE,
            SubscriptionPlanCode.STANDARD,
            SubscriptionPlanCode.PREMIUM,
        }
        default = db.query(Tenant).filter(Tenant.slug == "default").first()
        assert default is not None
        assert default.subscription is not None
        # Demo course tagged with default tenant
        from mooc.models import Course

        cs101 = db.query(Course).filter(Course.code == "CS101").first()
        if cs101:
            assert cs101.tenant_id == default.id


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def test_homepage_includes_default_tenant_branding(client):
    r = client.get("/")
    assert r.status_code == 200
    # Default seeded tenant uses Saudi green (#006c35) — appears as a
    # CSS variable injected by base.html.
    assert "--brand-primary" in r.text


def test_homepage_renders_tenant_name(client):
    r = client.get("/")
    assert r.status_code == 200
    # Default tenant name from seed
    assert "منصة المساقات المفتوحة" in r.text


def test_pricing_page_lists_all_plans(client):
    r = client.get("/pricing")
    assert r.status_code == 200
    for label in ("تجريبي", "قياسي", "متميّز"):
        assert label in r.text


def test_signup_creates_tenant_and_logs_admin_in(client):
    suffix = uuid.uuid4().hex[:6]
    slug = f"acme{suffix}"
    r = client.post(
        "/signup",
        data={
            "workspace_name": "أكاديمية أكمي",
            "workspace_slug": slug,
            "contact_email": f"info-{suffix}@acme.sa",
            "admin_full_name": "مدير أكمي",
            "admin_email": f"admin-{suffix}@acme.sa",
            "admin_password": "Strong1234",
            "plan": "standard",
            "period": "monthly",
            "consent": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "mooc_session" in r.cookies
    assert r.cookies.get("mooc_tenant") == slug

    with session_scope() as db:
        tenant = db.query(Tenant).filter(Tenant.slug == slug).first()
        assert tenant is not None
        assert tenant.subscription is not None
        assert tenant.subscription.status == SubscriptionStatus.TRIAL
        admin = db.query(User).filter(User.email == f"admin-{suffix}@acme.sa").first()
        assert admin and admin.tenant_id == tenant.id


def test_signup_rejects_reused_slug(client):
    r = client.post(
        "/signup",
        data={
            "workspace_name": "تجربة",
            "workspace_slug": "default",  # reserved by seed
            "contact_email": "x@x.sa",
            "admin_full_name": "م",
            "admin_email": f"x-{uuid.uuid4().hex[:6]}@x.sa",
            "admin_password": "Strong1234",
            "plan": "free",
            "period": "monthly",
            "consent": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_signup_rejects_invalid_slug(client):
    r = client.post(
        "/signup",
        data={
            "workspace_name": "ت",
            "workspace_slug": "BAD-SLUG!",
            "contact_email": "x@x.sa",
            "admin_full_name": "م",
            "admin_email": "y@x.sa",
            "admin_password": "Strong1234",
            "plan": "free",
            "period": "monthly",
            "consent": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_public_custom_page_renders(client):
    """The seed creates /p/about for the default tenant."""
    r = client.get("/p/about")
    assert r.status_code == 200
    assert "عن المنصة" in r.text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_tenant_branding_css_emits_variables():
    t = Tenant(
        slug="x",
        name_ar="x",
        primary_color="#123456",
        accent_color="#abcdef",
        background_color="#fafafa",
        text_color="#111111",
    )
    css = tenant_branding_css(t)
    assert "--brand-primary:#123456" in css
    assert "--brand-accent:#abcdef" in css


def test_tenant_label_returns_default_when_missing():
    t = Tenant(slug="x", name_ar="x", custom_labels={"course": "حقيبة"})
    assert tenant_label(t, "course", "مقرر") == "حقيبة"
    assert tenant_label(t, "lesson", "درس") == "درس"
