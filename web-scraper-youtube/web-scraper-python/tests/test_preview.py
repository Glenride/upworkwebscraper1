from __future__ import annotations

from importlib import import_module, reload
import os
from pathlib import Path
import sys


def _load_helper(tmp_path: Path):
    csv_stub = tmp_path / "stub.csv"
    csv_stub.write_text("store_name,url\n", encoding="utf-8")
    os.environ["SCRAPER_INPUT_URLS"] = str(csv_stub)
    os.environ["SCRAPER_UI_DB_PATH"] = str(tmp_path / "ui_runs.db")
    # ensure module reflects latest env
    module_name = "api.app"
    if module_name in sys.modules:
        module = reload(sys.modules[module_name])
    else:
        module = import_module(module_name)
    return module._load_preview_rows  # type: ignore[attr-defined]


def test_load_preview_rows_limits_and_deduplicates(tmp_path: Path) -> None:
    _load_preview_rows = _load_helper(tmp_path)

    csv_path = tmp_path / "shopify_import.csv"
    csv_path.write_text(
        """Handle,Title,Body (HTML)
handle-1,Product One,<p>HTML 1</p>
handle-1,Product One Alt,<p>HTML 1 alt</p>
handle-2,Product Two,<p>HTML 2</p>
handle-3,Product Three,<p>HTML 3</p>
""",
        encoding="utf-8",
    )

    previews = _load_preview_rows(csv_path, limit=2)

    assert len(previews) == 2
    assert previews[0]["handle"] == "handle-1"
    assert previews[0]["body_html"] == "<p>HTML 1</p>"
    assert previews[1]["handle"] == "handle-2"

def test_load_preview_rows_returns_all_if_under_limit(tmp_path: Path) -> None:
    _load_preview_rows = _load_helper(tmp_path)

    csv_path = tmp_path / "shopify_import.csv"
    csv_path.write_text(
        """Handle,Title,Body (HTML)
handle-1,Product One,<p>HTML 1</p>
""",
        encoding="utf-8",
    )

    previews = _load_preview_rows(csv_path, limit=5)

    assert len(previews) == 1
    assert previews[0]["title"] == "Product One"
    assert previews[0]["body_html"] == "<p>HTML 1</p>"
