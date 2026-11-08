"""Tests for pipeline CSV export behavior."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from scraper.pipeline import PipelineResult, _export_csv, _zip_directory


def test_export_csv_writes_rows(tmp_path: Path):
    class DummyRecord:
        def to_rows(self):
            return [
                {"Handle": "sample", "Title": "Sample", "Variant SKU": "SKU1", "Image Src": "img1.jpg"},
                {"Handle": "sample", "Title": "Sample", "Variant SKU": "SKU2", "Image Src": "img2.jpg"},
            ]

    records = [DummyRecord()]
    destination = tmp_path / "shopify.csv"
    _export_csv(records, destination)
    df = pd.read_csv(destination)
    assert len(df) == 2


def test_export_csv_empty(tmp_path: Path):
    destination = tmp_path / "shopify.csv"
    with patch("pandas.DataFrame.to_csv") as mock_to_csv:
        _export_csv([], destination)
        assert mock_to_csv.called


def test_zip_directory_creates_archive(tmp_path: Path):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "file1.txt").write_text("hello", encoding="utf-8")

    archive_path = _zip_directory(assets_dir, tmp_path / "archive.zip")

    assert archive_path and archive_path.exists()


def test_zip_directory_skips_empty(tmp_path: Path, caplog):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with caplog.at_level(logging.INFO):
        archive_path = _zip_directory(empty_dir, tmp_path / "archive.zip")

    assert archive_path is None
    assert "Zip skipped" in caplog.text
