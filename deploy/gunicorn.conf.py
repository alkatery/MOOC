"""Gunicorn configuration for the MOOC platform on larning.alkathiri.net.

Tuning notes:
* ``workers``       — start with (CPU cores * 2) + 1; the platform is
                      I/O-bound (DB + Ollama HTTP), so 4–8 is usually
                      plenty. Override with ``GUNICORN_WORKERS`` env var.
* ``worker_class``  — ``uvicorn.workers.UvicornWorker`` is what FastAPI
                      needs for ASGI semantics.
* ``bind``          — uses the socket-activated unix socket from
                      ``larning.socket``. Override with ``GUNICORN_BIND``
                      to test locally on a TCP port (e.g. ``0.0.0.0:8000``).
* ``timeout``       — long enough for SCORM uploads / Ollama replies.
"""

from __future__ import annotations

import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "unix:/run/larning.sock")
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Timeouts
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5

# Process management
max_requests = 1000          # restart worker after N requests (mitigates leaks)
max_requests_jitter = 50

# Logging — go to stdout/stderr so journalctl picks them up
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '%(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)ss'
)

# Forwarded headers (we sit behind nginx)
forwarded_allow_ips = "127.0.0.1"
proxy_allow_ips = "127.0.0.1"

# Preload the app so workers share parsed code (lower RAM)
preload_app = True

# Process name (shows up in `ps`/`htop`)
proc_name = "larning"
