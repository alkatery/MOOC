"""Entry point for ``python -m mooc`` and the ``mooc-platform`` script."""

from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mooc-platform",
        description="تشغيل منصة المساقات المفتوحة المتوافقة مع NELC",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="تهيئة قاعدة البيانات ببيانات تجريبية قبل التشغيل",
    )
    args = parser.parse_args()

    from .database import init_db

    init_db()
    if args.seed:
        from .seed import run_seed

        run_seed()

    import uvicorn

    uvicorn.run(
        "mooc.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
