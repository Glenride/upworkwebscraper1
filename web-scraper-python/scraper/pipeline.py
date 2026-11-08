"""Core scraping pipeline orchestration for Cafe24 scraper MVP."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd

from .client import Cafe24Client, RequestConfig
from .ingest import InputLoader, ProductInput
from .models import RawProductData, ShopifyRecord
from .parser import Cafe24Parser
from .transform import raw_to_shopify


@dataclass
class PipelineSettings:
    input_path: Path
    output_dir: Path
    templates_dir: Path
    proxy_url: str | None = None
    captcha_key: str | None = None


@dataclass
class PipelineResult:
    records: List[ShopifyRecord]
    failures: List[Dict[str, str]]
    summary_path: Path
    csv_path: Path


def run_pipeline(settings: PipelineSettings) -> PipelineResult:
    loader = InputLoader(settings.input_path)
    inputs = loader.load()
    inputs = _dedupe_inputs(inputs)

    client = Cafe24Client(RequestConfig(proxy_url=settings.proxy_url))
    parser = Cafe24Parser()

    records: List[ShopifyRecord] = []
    failures: List[Dict[str, str]] = []

    logging.info("Processing %s product URLs", len(inputs))

    for product in inputs:
        try:
            record = _process_single(product, client, parser)
            records.append(record)
        except Exception as exc:  # pragma: no cover - will be covered in tests with specific exceptions
            logging.exception("Failed to process product", extra={"url": product.url})
            failures.append({"url": product.url, "error": str(exc)})

    csv_path = settings.output_dir / "shopify_import.csv"
    _export_csv(records, csv_path)

    summary_path = settings.output_dir / "run_summary.json"
    _write_summary(summary_path, records, failures)

    return PipelineResult(records=records, failures=failures, summary_path=summary_path, csv_path=csv_path)


def _dedupe_inputs(inputs: List[ProductInput]) -> List[ProductInput]:
    seen = set()
    deduped: List[ProductInput] = []
    for item in inputs:
        if item.url in seen:
            continue
        deduped.append(item)
        seen.add(item.url)
    return deduped


def _process_single(product: ProductInput, client: Cafe24Client, parser: Cafe24Parser) -> ShopifyRecord:
    response = client.fetch(product.url)
    raw: RawProductData = parser.parse(product.url, response.text)
    record = raw_to_shopify(raw)
    return record


def _export_csv(records: List[ShopifyRecord], destination: Path) -> None:
    rows: List[Dict[str, str]] = []
    for record in records:
        rows.extend(record.to_rows())

    if not rows:
        logging.warning("No records to export; writing empty CSV to %s", destination)
        pd.DataFrame(columns=["Handle", "Title"]).to_csv(destination, index=False)
        return

    df = pd.DataFrame(rows)
    df.to_csv(destination, index=False)
    logging.info("Wrote Shopify CSV with %s rows", len(df))


def _write_summary(path: Path, records: List[ShopifyRecord], failures: List[Dict[str, str]]) -> None:
    summary = {
        "success_count": len(records),
        "failure_count": len(failures),
        "failures": failures,
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logging.info("Run summary saved to %s", path)
