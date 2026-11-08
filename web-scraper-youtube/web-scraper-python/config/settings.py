"""Application settings loading for Cafe24 scraper MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Settings:
    """Runtime configuration values."""

    input_urls_path: Path
    output_root: Path = Path("output")
    logs_root: Path = Path("logs")
    templates_root: Path = Path("templates")
    detail_template_name: str = "detail_header.png"
    puppeteer_enabled: bool = False
    puppeteer_bin: Optional[Path] = None
    puppeteer_output_dir: Optional[Path] = None
    puppeteer_script: Optional[Path] = None
    zip_outputs: bool = True
    zip_images_name: str = "images.zip"
    zip_screenshots_name: str = "screenshots.zip"
    schedule_enabled: bool = False
    schedule_cron: str = "0 2 * * *"  # default 2 AM daily
    proxy_url: Optional[str] = None
    captcha_api_key: Optional[str] = None
    ui_database_path: Path = Path("ui_runs.db")
    ui_basic_auth_username: Optional[str] = None
    ui_basic_auth_password: Optional[str] = None
    visual_output_root: Path = Path("visual_output")
    visual_default_max_urls: int = 50
    visual_max_images: Optional[int] = None
    session_secret: Optional[str] = None


def load_settings(env_file: str | Path = ".env") -> Settings:
    """Load settings from environment variables with optional .env file."""

    load_dotenv(env_file)

    input_urls = Path(_require_env("SCRAPER_INPUT_URLS"))
    visual_max_images_env = _get_env("SCRAPER_VISUAL_MAX_IMAGES")
    session_secret = _get_env("SCRAPER_SESSION_SECRET") or _get_env("SCRAPER_UI_PASSWORD") or "scraper-session-secret"

    return Settings(
        input_urls_path=input_urls,
        output_root=Path(_get_env("SCRAPER_OUTPUT_ROOT", "output")),
        logs_root=Path(_get_env("SCRAPER_LOGS_ROOT", "logs")),
        templates_root=Path(_get_env("SCRAPER_TEMPLATES_ROOT", "templates")),
        detail_template_name=_get_env("SCRAPER_DETAIL_TEMPLATE", "detail_header.png"),
        puppeteer_enabled=_get_env("PUPPETEER_ENABLED", "false").lower() == "true",
        puppeteer_bin=Path(_get_env("PUPPETEER_BIN", "node")),
        puppeteer_output_dir=_optional_path(_get_env("PUPPETEER_OUTPUT_DIR")),
        puppeteer_script=_optional_path(_get_env("PUPPETEER_SCRIPT")),
        zip_outputs=_get_env("SCRAPER_ZIP_OUTPUTS", "true").lower() == "true",
        zip_images_name=_get_env("SCRAPER_ZIP_IMAGES_NAME", "images.zip"),
        zip_screenshots_name=_get_env("SCRAPER_ZIP_SCREENSHOTS_NAME", "screenshots.zip"),
        schedule_enabled=_get_env("SCRAPER_SCHEDULE_ENABLED", "false").lower() == "true",
        schedule_cron=_get_env("SCRAPER_SCHEDULE_CRON", "0 2 * * *"),
        proxy_url=_get_env("SCRAPER_PROXY_URL"),
        captcha_api_key=_get_env("SCRAPER_CAPTCHA_API_KEY"),
        ui_database_path=Path(_get_env("SCRAPER_UI_DB_PATH", "ui_runs.db")),
        ui_basic_auth_username=_get_env("SCRAPER_UI_USERNAME"),
        ui_basic_auth_password=_get_env("SCRAPER_UI_PASSWORD"),
        visual_output_root=Path(_get_env("SCRAPER_VISUAL_OUTPUT_ROOT", "visual_output")),
        visual_default_max_urls=int(_get_env("SCRAPER_VISUAL_MAX_URLS", "50")),
        visual_max_images=int(visual_max_images_env) if visual_max_images_env else None,
        session_secret=session_secret,
    )


def _require_env(key: str) -> str:
    value = _get_env(key)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def _optional_path(value: Optional[str]) -> Optional[Path]:
    if value and value.strip():
        return Path(value)
    return None


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    from os import getenv

    value = getenv(key)
    if value is None:
        return default
    return value
