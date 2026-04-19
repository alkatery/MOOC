"""Tests for password hashing and JWT."""

from __future__ import annotations

import time

from mooc.security import (
    create_access_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_hash_and_verify_password():
    h = hash_password("SuperSecure123")
    assert h != "SuperSecure123"
    assert verify_password("SuperSecure123", h) is True
    assert verify_password("wrong", h) is False


def test_password_strength_rules():
    assert validate_password_strength("short") is not None
    assert validate_password_strength("onlyletters") is not None
    assert validate_password_strength("12345678") is not None
    assert validate_password_strength("Good1234") is None


def test_jwt_roundtrip():
    token = create_access_token(subject="user-abc", role="student", extra={"uid": 42})
    payload = decode_token(token)
    assert payload["sub"] == "user-abc"
    assert payload["role"] == "student"
    assert payload["uid"] == 42
