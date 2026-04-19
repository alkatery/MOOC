"""Runtime configuration for the MOOC platform.

Settings are read from environment variables (optionally via a .env file)
so the same codebase can be deployed in dev, staging, and production
without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_list(name: str, default: List[str]) -> List[str]:
    raw = os.environ.get(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    """Top-level runtime configuration."""

    # Identity / branding
    platform_name_ar: str = "منصة المساقات المفتوحة"
    platform_name_en: str = "Open MOOC Platform"
    organization_name_ar: str = "المركز الوطني للتعليم الإلكتروني"
    organization_name_en: str = "National eLearning Center"
    default_locale: str = "ar"
    supported_locales: List[str] = field(default_factory=lambda: ["ar", "en"])

    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("MOOC_DATA_DIR", "./var/mooc")).resolve()
    )

    # Database
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "MOOC_DATABASE_URL",
            f"sqlite:///{Path(os.environ.get('MOOC_DATA_DIR', './var/mooc')).resolve()}/mooc.db",
        )
    )

    # Security
    secret_key: str = field(
        default_factory=lambda: os.environ.get(
            "MOOC_SECRET_KEY",
            "change-me-in-production-this-is-for-local-development-only",
        )
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = int(os.environ.get("MOOC_TOKEN_TTL_MIN", "120"))
    password_min_length: int = 8
    password_require_complexity: bool = True

    # Course / catalog
    max_upload_size_mb: int = int(os.environ.get("MOOC_MAX_UPLOAD_MB", "100"))
    certificate_valid_years: int = 5
    default_passing_grade: int = 60

    # NELC compliance toggles
    nelc_compliance_mode: bool = _env_bool("MOOC_NELC_MODE", True)
    enforce_quality_review: bool = True
    enforce_accessibility_check: bool = True
    retain_audit_log_days: int = 365 * 2
    data_residency_region: str = "sa-central-1"

    # CORS / hosts
    cors_origins: List[str] = field(
        default_factory=lambda: _env_list("MOOC_CORS_ORIGINS", ["*"])
    )
    trusted_hosts: List[str] = field(
        default_factory=lambda: _env_list("MOOC_TRUSTED_HOSTS", ["*"])
    )

    # Runtime
    debug: bool = field(default_factory=lambda: _env_bool("MOOC_DEBUG", False))

    def ensure_directories(self) -> None:
        """Create on-disk directories the platform expects."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "uploads").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "scorm").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "xapi").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "certificates").mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings
