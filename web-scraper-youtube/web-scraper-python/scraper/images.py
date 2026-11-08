"""Image download and processing utilities for Cafe24 scraper MVP."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urlparse

import cv2
import requests
from PIL import Image


@dataclass
class ImageDownloadResult:
    path: Path
    source_url: str
    kind: str


class ImageManager:
    """Handles downloading images and applying template-based cropping."""

    def __init__(self, output_dir: Path, templates_dir: Path) -> None:
        self.output_dir = output_dir
        self.templates_dir = templates_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self.output_dir

    def download_images(self, urls: Iterable[str], prefix: str, kind: str) -> List[ImageDownloadResult]:
        results: List[ImageDownloadResult] = []
        for idx, url in enumerate(urls, start=1):
            try:
                path = self._download_single(url, prefix, kind, idx)
                if path:
                    results.append(ImageDownloadResult(path=path, source_url=url, kind=kind))
            except Exception as exc:
                logging.exception("Failed to download image", extra={"url": url, "kind": kind, "error": str(exc)})
        return results

    def _download_single(self, url: str, prefix: str, kind: str, index: int) -> Optional[Path]:
        if not url:
            return None
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        suffix = self._infer_extension(url) or ".jpg"
        filename = f"{prefix}_{kind}_{index}{suffix}"
        destination = self.output_dir / filename
        with destination.open("wb") as handle:
            handle.write(response.content)
        return destination

    def _infer_extension(self, url: str) -> Optional[str]:
        path = urlparse(url).path
        if "." in path:
            return path[path.rfind("."):]
        return None

    def crop_detail_image(self, image_path: Path, template_name: str, buffer_pixels: int = 10) -> Optional[Path]:
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            logging.warning("Template missing, skipping crop", extra={"template": template_name})
            return None

        target = cv2.imread(str(image_path))
        template = cv2.imread(str(template_path))
        if target is None or template is None:
            logging.warning("Failed to read image/template", extra={"image": str(image_path), "template": str(template_path)})
            return None

        result = cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < 0.8:
            logging.info("No confident match for template", extra={"image": str(image_path), "score": max_val})
            return None

        template_height = template.shape[0]
        crop_start = max_loc[1] + template_height + buffer_pixels
        cropped = target[crop_start:, :]
        if cropped.size == 0:
            logging.warning("Cropping resulted in empty image", extra={"image": str(image_path)})
            return None

        cropped_image = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
        cropped_path = image_path.with_name(image_path.stem + "_cropped" + image_path.suffix)
        cropped_image.save(cropped_path, quality=90)
        return cropped_path

    def optimize_image(self, image_path: Path, max_width: int = 1200) -> None:
        with Image.open(image_path) as img:
            if img.width <= max_width:
                return
            ratio = max_width / float(img.width)
            new_size = (max_width, int(img.height * ratio))
            resized = img.resize(new_size, Image.LANCZOS)
            resized.save(image_path, quality=90)
