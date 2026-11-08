"""Helper utilities for Cafe24 scraper."""

from __future__ import annotations

import re
from typing import Iterable, List


_SLUGIFY_PATTERN = re.compile(r"[^a-z0-9-]+")


def slugify(value: str) -> str:
    value = (value or "").lower()
    value = value.strip().replace(" ", "-")
    value = _SLUGIFY_PATTERN.sub("-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "product"


def split_tags(raw: str | Iterable[str] | None) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [part.strip() for part in raw.split(",")]
    else:
        parts = [str(part).strip() for part in raw]
    return [part for part in parts if part]
