"""End-to-end HTTP tests (public pages + auth)."""

from __future__ import annotations


def test_home_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "منصة" in r.text
    assert "NELC" in r.text or "nelc" in r.text.lower()


def test_nelc_page_lists_domains(client):
    r = client.get("/nelc-standards")
    assert r.status_code == 200
    for code in ["K.1", "K.2", "K.3", "K.4", "K.5", "K.6", "K.7", "K.8"]:
        assert code in r.text


def test_register_and_login_flow(client):
    import uuid

    email = f"test-{uuid.uuid4().hex[:8]}@mooc.sa"

    r = client.post(
        "/register",
        data={
            "email": email,
            "full_name_ar": "طالب اختبار",
            "password": "Test1234",
            "password_confirm": "Test1234",
            "role": "student",
            "consent": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "mooc_session" in r.cookies

    r2 = client.post(
        "/login",
        data={"email": email, "password": "Test1234"},
        follow_redirects=False,
    )
    assert r2.status_code == 303


def test_admin_requires_auth(client):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code in (401, 303, 302)


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["nelc_domains"] == 8
    assert data["nelc_criteria"] > 0
