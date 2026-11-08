"""URL intake and discovery utilities for Cafe24 scraper MVP."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class ProductInput:
    """Represents a single product URL entry."""

    url: str


class InputLoader:
    """Loads client-supplied product URLs from CSV or JSON."""

    SUPPORTED_EXTENSIONS = {".csv", ".json"}

    def __init__(self, path: Path) -> None:
        self.path = path
        self._validate_extension()

    def load(self) -> List[ProductInput]:
        if self.path.suffix.lower() == ".csv":
            return list(self._load_csv())
        return list(self._load_json())

    def _load_csv(self) -> Iterable[ProductInput]:
        with self.path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if "url" not in reader.fieldnames:
                raise ValueError("CSV must contain a 'url' column")
            for row in reader:
                url = (row.get("url") or "").strip()
                if not url:
                    continue
                yield ProductInput(url=url)

    def _load_json(self) -> Iterable[ProductInput]:
        with self.path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("JSON input must be a list of objects with 'url'")
        for entry in data:
            url = ""
            if isinstance(entry, str):
                url = entry
            elif isinstance(entry, dict):
                url = entry.get("url", "")
            if url:
                yield ProductInput(url=url.strip())

    def _validate_extension(self) -> None:
        if self.path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported input format: {self.path.suffix}")
