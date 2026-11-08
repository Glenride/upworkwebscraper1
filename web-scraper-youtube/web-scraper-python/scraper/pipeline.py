"""Core scraping pipeline orchestration for Cafe24 scraper MVP."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .client import Cafe24Client, RequestConfig
from .images import ImageManager
from .ingest import InputLoader, ProductInput
from .models import RawProductData, ShopifyRecord
from .parser import Cafe24Parser
from .transform import raw_to_shopify
from .utils import slugify


@dataclass
class PipelineSettings:
    input_path: Path
    output_dir: Path
    templates_dir: Path
    proxy_url: str | None = None
    captcha_key: str | None = None
    detail_template_name: str = "detail_header.png"
    zip_outputs: bool = True
    zip_images_name: str = "images.zip"
    zip_screenshots_name: str = "screenshots.zip"


@dataclass
class PipelineResult:
    records: List[ShopifyRecord]
    failures: List[Dict[str, str]]
    summary_path: Path
    csv_path: Path
    images_dir: Path
    images_zip: Optional[Path]
    screenshots_zip: Optional[Path]


def run_pipeline(settings: PipelineSettings) -> PipelineResult:
    loader = InputLoader(settings.input_path)
    inputs = _dedupe_inputs(loader.load())

    client = Cafe24Client(RequestConfig(proxy_url=settings.proxy_url))
    parser = Cafe24Parser()
    image_manager = ImageManager(settings.output_dir / "images", settings.templates_dir)

    records: List[ShopifyRecord] = []
    failures: List[Dict[str, str]] = []

    logging.info("Processing %s product URLs", len(inputs))

    for product in inputs:
        try:
            record = _process_single(
                product,
                client,
                parser,
                image_manager,
                settings.output_dir,
                settings.detail_template_name,
            )
            records.append(record)
        except Exception as exc:  # pragma: no cover - to be caught in integration tests
            logging.exception("Failed to process product", extra={"url": product.url})
            failures.append({"url": product.url, "error": str(exc)})

    csv_path = settings.output_dir / "shopify_import.csv"
    _export_csv(records, csv_path)

    images_zip: Optional[Path] = None
    screenshots_zip: Optional[Path] = None

    if settings.zip_outputs:
        images_zip = _zip_directory(image_manager.base_dir, settings.output_dir / settings.zip_images_name)
        screenshots_dir = settings.output_dir / "screenshots"
        if screenshots_dir.exists():
            screenshots_zip = _zip_directory(
                screenshots_dir,
                settings.output_dir / settings.zip_screenshots_name,
            )

    summary_path = settings.output_dir / "run_summary.json"
    _write_summary(
        summary_path,
        records,
        failures,
        images_zip=images_zip,
        screenshots_zip=screenshots_zip,
    )

    return PipelineResult(
        records=records,
        failures=failures,
        summary_path=summary_path,
        csv_path=csv_path,
        images_dir=image_manager.base_dir,
        images_zip=images_zip,
        screenshots_zip=screenshots_zip,
    )


def _dedupe_inputs(inputs: List[ProductInput]) -> List[ProductInput]:
    seen = set()
    deduped: List[ProductInput] = []
    for item in inputs:
        if item.url in seen:
            continue
        deduped.append(item)
        seen.add(item.url)
    return deduped


def _process_single(
    product: ProductInput,
    client: Cafe24Client,
    parser: Cafe24Parser,
    image_manager: ImageManager,
    output_root: Path,
    detail_template_name: str,
) -> ShopifyRecord:
    response = client.fetch(product.url)
    raw: RawProductData = parser.parse(product.url, response.text)

    prefix = slugify(raw.title or raw.sku or raw.source_url)

    if raw.main_image:
        main_paths = _download_and_prepare(
            image_manager,
            [raw.main_image],
            prefix,
            "main",
            output_root,
            detail_template_name,
        )
        if main_paths:
            raw.main_image = main_paths[0]

    if raw.gallery_images:
        raw.gallery_images = _download_and_prepare(
            image_manager,
            raw.gallery_images,
            prefix,
            "gallery",
            output_root,
            detail_template_name,
        )

    if raw.detail_images:
        raw.detail_images = _download_and_prepare(
            image_manager,
            raw.detail_images,
            prefix,
            "detail",
            output_root,
            detail_template_name,
        )

    record = raw_to_shopify(raw)
    return record


def _download_and_prepare(
    image_manager: ImageManager,
    urls: List[str],
    prefix: str,
    kind: str,
    output_root: Path,
    detail_template_name: str,
) -> List[str]:
    downloads = image_manager.download_images(urls, prefix, kind)
    prepared_paths: List[str] = []

    for download in downloads:
        target_path = download.path
        if kind == "detail" and detail_template_name:
            cropped = image_manager.crop_detail_image(download.path, detail_template_name)
            if cropped:
                target_path = cropped
        image_manager.optimize_image(target_path)
        prepared_paths.append(_relative(target_path, output_root))

    return prepared_paths


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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


def _write_summary(
    path: Path,
    records: List[ShopifyRecord],
    failures: List[Dict[str, str]],
    *,
    images_zip: Optional[Path] = None,
    screenshots_zip: Optional[Path] = None,
) -> None:
    summary = {
        "success_count": len(records),
        "failure_count": len(failures),
        "failures": failures,
    }
    if images_zip:
        summary["images_archive"] = str(images_zip)
    if screenshots_zip:
        summary["screenshots_archive"] = str(screenshots_zip)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logging.info("Run summary saved to %s", path)


def _zip_directory(source_dir: Path, destination: Path) -> Optional[Path]:
    if not source_dir.exists() or not any(source_dir.iterdir()):
        logging.info("Zip skipped; directory empty", extra={"directory": str(source_dir)})
        return None

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.make_archive(str(destination.with_suffix("")), "zip", root_dir=source_dir)
    archive_path = destination if destination.suffix == ".zip" else destination.with_suffix(".zip")
    logging.info("Created archive %s", archive_path)
    return archive_path
