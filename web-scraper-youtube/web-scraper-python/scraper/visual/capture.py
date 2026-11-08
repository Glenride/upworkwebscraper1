"""Utilities for capturing screenshots and extracting text from arbitrary URLs."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from scraper.utils import slugify


@dataclass
class CaptureResult:
    url: str
    screenshot_path: Optional[Path]
    text_path: Optional[Path]
    text_excerpt: Optional[str]
    status: str
    error: Optional[str] = None


def capture_pages(
    urls: Iterable[str],
    output_dir: Path,
    *,
    timeout_ms: int = 30000,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    proxy_url: str | None = None,
) -> List[CaptureResult]:
    """Capture full-page screenshots and extract body text for each URL.

    Returns a list of CaptureResult entries describing success/failure per URL.
    """

    screenshots_dir = output_dir / "screenshots"
    text_dir = output_dir / "text"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    results: List[CaptureResult] = []

    with sync_playwright() as playwright:
        launch_kwargs = {"headless": True}
        if proxy_url:
            launch_kwargs["proxy"] = {"server": proxy_url}

        browser = playwright.chromium.launch(**launch_kwargs)
        viewport = {
            "width": int(random.gauss(viewport_width, 40)),
            "height": int(random.gauss(viewport_height, 40)),
        }
        context = browser.new_context(
            viewport=viewport,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        _apply_stealth(context)
        page = context.new_page()
        page.set_default_navigation_timeout(timeout_ms)
        page.set_default_timeout(timeout_ms)

        for index, url in enumerate(urls, start=1):
            slug = _slug_for_url(url, index)
            screenshot_path: Optional[Path] = None
            text_path: Optional[Path] = None
            text_excerpt: Optional[str] = None
            error: Optional[str] = None
            status = "succeeded"

            try:
                page.route("**/*", _apply_request_headers)
                page.goto(url, wait_until="domcontentloaded")
                # Attempt to wait for a meaningful element; fallback to body
                try:
                    page.wait_for_selector("body", timeout=5000)
                except PlaywrightTimeoutError:
                    page.wait_for_timeout(1000)
                else:
                    page.wait_for_timeout(500)
                # allow additional network activity to quiet down
                page.wait_for_timeout(random.randint(750, 1500))

                screenshot_path = screenshots_dir / f"{slug}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)

                text_content = page.inner_text("body")
                text_path = text_dir / f"{slug}.txt"
                text_path.write_text(text_content, encoding="utf-8")
                text_excerpt = _excerpt(text_content)
            except PlaywrightTimeoutError:
                status = "failed"
                error = "Timed out loading page"
            except Exception as exc:  # pragma: no cover - defensive
                status = "failed"
                error = str(exc)
            finally:
                results.append(
                    CaptureResult(
                        url=url,
                        screenshot_path=screenshot_path if screenshot_path and screenshot_path.exists() else None,
                        text_path=text_path if text_path and text_path.exists() else None,
                        text_excerpt=text_excerpt,
                        status=status,
                        error=error,
                    )
                )

        context.close()
        browser.close()

    return results


def _apply_request_headers(route, request):
    headers = request.headers.copy()
    headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8")
    headers.setdefault("Accept-Encoding", "gzip, deflate, br")
    route.continue_(headers=headers)


def _apply_stealth(context) -> None:
    script = """
    // Navigator.webdriver block
    Object.defineProperty(navigator, 'webdriver', {
      get: () => undefined,
    });

    // Plugins spoofing
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3],
    });

    // Languages spoofing
    Object.defineProperty(navigator, 'languages', {
      get: () => ['en-US', 'en'],
    });

    // Hardware concurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {
      get: () => 8,
    });

    // Vendor
    Object.defineProperty(navigator, 'vendor', {
      get: () => 'Google Inc.',
    });

    // Chrome runtime
    window.chrome = {
      runtime: {},
    };
    """
    context.add_init_script(script)

def write_summary(output_dir: Path, results: List[CaptureResult]) -> Path:
    def _relative(path: Optional[Path]) -> Optional[str]:
        if not path:
            return None
        try:
            return str(path.relative_to(output_dir))
        except ValueError:
            return str(path)

    summary = {
        "success_count": sum(1 for item in results if item.status == "succeeded"),
        "failure_count": sum(1 for item in results if item.status != "succeeded"),
        "items": [
            {
                "url": item.url,
                "status": item.status,
                "screenshot_path": _relative(item.screenshot_path),
                "text_path": _relative(item.text_path),
                "text_excerpt": item.text_excerpt,
                "error": item.error,
            }
            for item in results
        ],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def _slug_for_url(url: str, index: int) -> str:
    parsed = urlparse(url)
    base = parsed.netloc or parsed.path or f"url-{index}"
    slug = slugify(base)
    if not slug:
        slug = f"url-{index}"
    return f"{slug}-{index}"


def _excerpt(text: str, limit: int = 320) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "…"
