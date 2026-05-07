"""SaaS / multi-tenant routes: pricing, signup, tenant settings.

A new tenant signs up at ``/signup``, which creates a Tenant + admin
User + a 14-day trial Subscription on the chosen plan. After signup the
admin can manage their workspace at ``/tenant/...``:

* ``/tenant/settings``   — name, about, contact, theme colors, logo URL
* ``/tenant/social``     — social-media links
* ``/tenant/policies``   — privacy, terms, refund policies
* ``/tenant/labels``     — rename UI strings (e.g. "Course" → "حقيبة")
* ``/tenant/pages``      — CRUD custom CMS pages (FAQ, About, …)
* ``/tenant/billing``    — change plan / billing period
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import (
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
from ..security import (
    get_current_user_optional,
    hash_password,
    issue_session_cookie,
    require_admin,
)
from ..services.audit import log as audit_log
from ..services.tenants import resolve_tenant, tenant_by_slug

router = APIRouter(tags=["saas"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{2,30}$")


def _ctx(request, user=None, tenant=None, **kwargs):
    return {
        "request": request,
        "user": user,
        "tenant": tenant,
        "settings": get_settings(),
        **kwargs,
    }


# ---------------------------------------------------------------------------
# Pricing + signup
# ---------------------------------------------------------------------------


@router.get("/pricing", response_class=HTMLResponse)
def pricing(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
    tenant: Optional[Tenant] = Depends(resolve_tenant),
):
    plans = (
        db.query(SubscriptionPlan)
        .order_by(SubscriptionPlan.price_monthly_sar)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "saas/pricing.html",
        _ctx(request, user, tenant, plans=plans),
    )


@router.get("/signup", response_class=HTMLResponse)
def signup_form(
    request: Request,
    plan: str = "standard",
    period: str = "monthly",
    db: Session = Depends(get_db),
    tenant: Optional[Tenant] = Depends(resolve_tenant),
):
    selected_plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.code == SubscriptionPlanCode(plan))
        .first()
        if plan in {p.value for p in SubscriptionPlanCode}
        else None
    )
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.price_monthly_sar).all()
    return templates.TemplateResponse(
        request,
        "saas/signup.html",
        _ctx(
            request,
            tenant=tenant,
            selected_plan=selected_plan,
            plans=plans,
            chosen_period=period if period in {"monthly", "yearly"} else "monthly",
        ),
    )


@router.post("/signup")
def signup_submit(
    request: Request,
    workspace_name: str = Form(...),
    workspace_slug: str = Form(...),
    contact_email: str = Form(...),
    admin_full_name: str = Form(...),
    admin_email: str = Form(...),
    admin_password: str = Form(...),
    plan: str = Form("standard"),
    period: str = Form("monthly"),
    consent: str = Form("off"),
    db: Session = Depends(get_db),
):
    if consent != "on":
        raise HTTPException(
            status_code=400,
            detail="يجب الموافقة على شروط الخدمة وسياسة الخصوصية قبل المتابعة.",
        )
    slug = workspace_slug.strip().lower()
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail="رمز المنصة يجب أن يبدأ بحرف ويحتوي 3-31 خانة (حروف لاتينية صغيرة وأرقام و'-').",
        )
    if tenant_by_slug(db, slug):
        raise HTTPException(status_code=400, detail="هذا الرمز محجوز، اختر رمزاً آخر.")
    if db.query(User).filter(User.email == admin_email).first():
        raise HTTPException(status_code=400, detail="البريد الإلكتروني للمدير مستخدم.")
    if len(admin_password) < 8:
        raise HTTPException(status_code=400, detail="كلمة المرور قصيرة جداً (٨ خانات على الأقل).")
    if plan not in {p.value for p in SubscriptionPlanCode}:
        plan = SubscriptionPlanCode.STANDARD.value
    if period not in {p.value for p in BillingPeriod}:
        period = BillingPeriod.MONTHLY.value

    plan_row = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.code == SubscriptionPlanCode(plan))
        .first()
    )
    if not plan_row:
        raise HTTPException(status_code=400, detail="الخطة المطلوبة غير متاحة.")

    tenant = Tenant(
        slug=slug,
        name_ar=workspace_name.strip(),
        contact_email=contact_email.strip(),
        primary_color="#0a7d3a",
        accent_color="#1f5fbf",
        background_color="#ffffff",
        text_color="#1a1a1a",
        social_links={},
        policies={},
        custom_labels={},
    )
    db.add(tenant)
    db.flush()

    admin = User(
        email=admin_email.strip().lower(),
        full_name_ar=admin_full_name.strip(),
        password_hash=hash_password(admin_password),
        role=UserRole.ADMIN,
        tenant_id=tenant.id,
        is_active=True,
        is_verified=True,
        consent_privacy=True,
        consent_timestamp=datetime.utcnow(),
    )
    db.add(admin)
    db.flush()

    now = datetime.utcnow()
    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=plan_row.id,
        period=BillingPeriod(period),
        status=SubscriptionStatus.TRIAL,
        starts_at=now,
        trial_ends_at=now + timedelta(days=14),
        current_period_end=now + timedelta(days=14),
    )
    db.add(sub)
    audit_log(db, admin, "tenant.signup", "tenant", tenant.public_id, {"plan": plan, "period": period})
    db.commit()

    token = issue_session_cookie(admin)
    response = RedirectResponse("/tenant/settings", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("mooc_session", token, httponly=True, samesite="lax")
    response.set_cookie("mooc_tenant", tenant.slug, samesite="lax")
    return response


# ---------------------------------------------------------------------------
# Tenant admin settings
# ---------------------------------------------------------------------------


def _require_tenant_admin(
    user: User = Depends(require_admin),
    tenant: Optional[Tenant] = Depends(resolve_tenant),
) -> tuple[User, Tenant]:
    if not tenant:
        raise HTTPException(status_code=404, detail="لا توجد منصة محددة.")
    if user.tenant_id and user.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="لست مدير هذه المنصة.")
    return user, tenant


@router.get("/tenant/settings", response_class=HTMLResponse)
def tenant_settings(
    request: Request,
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    return templates.TemplateResponse(
        request,
        "saas/tenant_settings.html",
        _ctx(request, user, tenant),
    )


@router.post("/tenant/settings/branding")
def tenant_save_branding(
    name_ar: str = Form(...),
    name_en: str = Form(""),
    tagline_ar: str = Form(""),
    about_ar: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    logo_url: str = Form(""),
    favicon_url: str = Form(""),
    primary_color: str = Form("#0a7d3a"),
    accent_color: str = Form("#1f5fbf"),
    background_color: str = Form("#ffffff"),
    text_color: str = Form("#1a1a1a"),
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    tenant.name_ar = name_ar.strip()
    tenant.name_en = name_en.strip() or None
    tenant.tagline_ar = tagline_ar.strip() or None
    tenant.about_ar = about_ar.strip() or None
    tenant.contact_email = contact_email.strip() or None
    tenant.contact_phone = contact_phone.strip() or None
    tenant.logo_url = logo_url.strip() or None
    tenant.favicon_url = favicon_url.strip() or None
    tenant.primary_color = primary_color
    tenant.accent_color = accent_color
    tenant.background_color = background_color
    tenant.text_color = text_color
    audit_log(db, user, "tenant.update_branding", "tenant", tenant.public_id)
    db.commit()
    return RedirectResponse("/tenant/settings", status_code=303)


@router.post("/tenant/settings/social")
async def tenant_save_social(
    request: Request,
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    form = await request.form()
    social = {
        key: (value or "").strip()
        for key in ("twitter", "linkedin", "instagram", "youtube", "facebook", "tiktok", "snapchat", "website")
        if (value := form.get(key))
    }
    tenant.social_links = social
    audit_log(db, user, "tenant.update_social", "tenant", tenant.public_id)
    db.commit()
    return RedirectResponse("/tenant/settings", status_code=303)


@router.post("/tenant/settings/policies")
async def tenant_save_policies(
    request: Request,
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    form = await request.form()
    tenant.policies = {
        "privacy": (form.get("privacy") or "").strip(),
        "terms": (form.get("terms") or "").strip(),
        "refund": (form.get("refund") or "").strip(),
        "code_of_conduct": (form.get("code_of_conduct") or "").strip(),
    }
    audit_log(db, user, "tenant.update_policies", "tenant", tenant.public_id)
    db.commit()
    return RedirectResponse("/tenant/settings", status_code=303)


@router.post("/tenant/settings/labels")
async def tenant_save_labels(
    request: Request,
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    form = await request.form()
    keys = ("course", "courses", "lesson", "instructor", "student", "enroll", "catalog")
    labels = {}
    for k in keys:
        v = (form.get(f"label_{k}") or "").strip()
        if v:
            labels[k] = v
    tenant.custom_labels = labels
    audit_log(db, user, "tenant.update_labels", "tenant", tenant.public_id)
    db.commit()
    return RedirectResponse("/tenant/settings", status_code=303)


# ---------------------------------------------------------------------------
# Tenant pages (CMS)
# ---------------------------------------------------------------------------


@router.get("/tenant/pages", response_class=HTMLResponse)
def tenant_pages_list(
    request: Request,
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    pages = (
        db.query(TenantPage)
        .filter(TenantPage.tenant_id == tenant.id)
        .order_by(TenantPage.order_index, TenantPage.created_at)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "saas/tenant_pages.html",
        _ctx(request, user, tenant, pages=pages),
    )


@router.get("/tenant/pages/new", response_class=HTMLResponse)
@router.get("/tenant/pages/{page_id}/edit", response_class=HTMLResponse)
def tenant_page_form(
    request: Request,
    page_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    page = None
    if page_id:
        page = (
            db.query(TenantPage)
            .filter(TenantPage.id == page_id, TenantPage.tenant_id == tenant.id)
            .first()
        )
        if not page:
            raise HTTPException(status_code=404, detail="الصفحة غير موجودة.")
    return templates.TemplateResponse(
        request,
        "saas/tenant_page_form.html",
        _ctx(request, user, tenant, page=page),
    )


@router.post("/tenant/pages/new")
@router.post("/tenant/pages/{page_id}/edit")
def tenant_page_save(
    page_id: Optional[int] = None,
    slug: str = Form(...),
    title_ar: str = Form(...),
    body_html: str = Form(...),
    show_in_nav: str = Form("off"),
    is_published: str = Form("off"),
    order_index: int = Form(0),
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    slug_clean = re.sub(r"[^a-z0-9-]+", "-", slug.strip().lower()).strip("-")
    if not slug_clean:
        raise HTTPException(status_code=400, detail="رمز الصفحة غير صالح.")
    if page_id:
        page = (
            db.query(TenantPage)
            .filter(TenantPage.id == page_id, TenantPage.tenant_id == tenant.id)
            .first()
        )
        if not page:
            raise HTTPException(status_code=404, detail="الصفحة غير موجودة.")
    else:
        existing = (
            db.query(TenantPage)
            .filter(TenantPage.tenant_id == tenant.id, TenantPage.slug == slug_clean)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="رمز الصفحة مستخدم.")
        page = TenantPage(tenant_id=tenant.id, slug=slug_clean)
        db.add(page)
    page.slug = slug_clean
    page.title_ar = title_ar.strip()
    page.body_html = body_html
    page.show_in_nav = show_in_nav == "on"
    page.is_published = is_published == "on"
    page.order_index = order_index
    audit_log(db, user, "tenant.page_save", "tenant_page", page.id, {"slug": slug_clean})
    db.commit()
    return RedirectResponse("/tenant/pages", status_code=303)


@router.post("/tenant/pages/{page_id}/delete")
def tenant_page_delete(
    page_id: int,
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    page = (
        db.query(TenantPage)
        .filter(TenantPage.id == page_id, TenantPage.tenant_id == tenant.id)
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="الصفحة غير موجودة.")
    db.delete(page)
    audit_log(db, user, "tenant.page_delete", "tenant_page", page_id)
    db.commit()
    return RedirectResponse("/tenant/pages", status_code=303)


# ---------------------------------------------------------------------------
# Public custom-page renderer
# ---------------------------------------------------------------------------


@router.get("/p/{slug}", response_class=HTMLResponse)
def public_tenant_page(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
    tenant: Optional[Tenant] = Depends(resolve_tenant),
):
    if not tenant:
        raise HTTPException(status_code=404, detail="منصة غير موجودة.")
    page = (
        db.query(TenantPage)
        .filter(
            TenantPage.tenant_id == tenant.id,
            TenantPage.slug == slug,
            TenantPage.is_published.is_(True),
        )
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="الصفحة غير موجودة.")
    return templates.TemplateResponse(
        request,
        "saas/public_page.html",
        _ctx(request, user, tenant, page=page),
    )


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


@router.get("/tenant/billing", response_class=HTMLResponse)
def billing_view(
    request: Request,
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.price_monthly_sar).all()
    return templates.TemplateResponse(
        request,
        "saas/billing.html",
        _ctx(request, user, tenant, subscription=tenant.subscription, plans=plans),
    )


@router.post("/tenant/billing/change")
def billing_change(
    plan: str = Form(...),
    period: str = Form("monthly"),
    db: Session = Depends(get_db),
    auth: tuple = Depends(_require_tenant_admin),
):
    user, tenant = auth
    if plan not in {p.value for p in SubscriptionPlanCode}:
        raise HTTPException(status_code=400, detail="خطة غير معروفة.")
    if period not in {p.value for p in BillingPeriod}:
        period = BillingPeriod.MONTHLY.value
    plan_row = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.code == SubscriptionPlanCode(plan))
        .first()
    )
    if not plan_row:
        raise HTTPException(status_code=400, detail="خطة غير متاحة.")

    sub = tenant.subscription
    if not sub:
        sub = Subscription(tenant_id=tenant.id, plan_id=plan_row.id)
        db.add(sub)
    sub.plan_id = plan_row.id
    sub.period = BillingPeriod(period)
    sub.status = SubscriptionStatus.ACTIVE
    days = 30 if period == BillingPeriod.MONTHLY.value else 365
    sub.current_period_end = datetime.utcnow() + timedelta(days=days)
    sub.last_payment_at = datetime.utcnow()
    sub.last_payment_amount = (
        plan_row.price_monthly_sar if period == BillingPeriod.MONTHLY.value
        else plan_row.price_yearly_sar
    )
    audit_log(db, user, "tenant.billing_change", "subscription", sub.id, {"plan": plan, "period": period})
    db.commit()
    return RedirectResponse("/tenant/billing", status_code=303)
