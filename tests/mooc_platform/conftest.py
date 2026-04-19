"""Shared pytest fixtures for the MOOC platform tests."""

from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def isolated_env():
    """Run tests against an ephemeral SQLite database + data dir."""
    tmpdir = tempfile.mkdtemp(prefix="mooc-test-")
    os.environ["MOOC_DATA_DIR"] = tmpdir
    os.environ["MOOC_DATABASE_URL"] = f"sqlite:///{tmpdir}/mooc-test.db"
    os.environ["MOOC_SECRET_KEY"] = "test-secret-key-for-tests-only"
    # Force the settings singleton to reload
    from mooc import config as c

    c._settings = None

    from mooc.database import init_db

    init_db()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from mooc.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
