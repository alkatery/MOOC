"""Passenger entry point for shared hosting (Hostinger / cPanel / Plesk).

Phusion Passenger speaks WSGI, but FastAPI is ASGI. We use ``a2wsgi``
to bridge the two. Install in your virtualenv with:

    pip install a2wsgi

This file is the single entry point that Hostinger's "Setup Python App"
invokes — set:

* Application root        : /home/u423175456/domains/alkathiri.net/public_html/larning
* Application URL         : larning.alkathiri.net
* Application startup file: passenger_wsgi.py
* Application entry point : application

It also makes sure the ``src/`` directory is on ``sys.path`` so the
``mooc`` package imports cleanly when the project is installed in
editable mode (``pip install -e .``) or simply checked out.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Load .env if python-dotenv is available (pip install python-dotenv).
try:
    from dotenv import load_dotenv

    load_dotenv(HERE / ".env")
except ImportError:
    pass

# Ensure schema exists on first request without needing a separate hook.
from mooc.database import init_db  # noqa: E402

init_db()

from mooc.main import app as _asgi_app  # noqa: E402

try:
    from a2wsgi import ASGIMiddleware
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: a2wsgi. Install with: "
        "pip install a2wsgi"
    ) from exc

# Passenger looks for the WSGI callable named ``application``.
application = ASGIMiddleware(_asgi_app)
