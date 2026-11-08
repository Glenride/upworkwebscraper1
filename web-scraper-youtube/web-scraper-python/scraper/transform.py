"""Transformation utilities converting raw Cafe24 data to Shopify records."""

from __future__ import annotations

from typing import List

from .models import RawProductData, ShopifyImage, ShopifyRecord, ShopifyVariant
from .utils import slugify


def raw_to_shopify(raw: RawProductData) -> ShopifyRecord:
    handle = slugify(raw.title or raw.sku or raw.source_url)
    effective_price = raw.sale_price if raw.sale_price else raw.price or 0.0
    compare_at = raw.price if raw.sale_price else raw.sale_price

    variant = ShopifyVariant(
        sku=raw.sku or handle,
        price=effective_price,
        compare_at_price=compare_at,
    )

    images: List[ShopifyImage] = []
    if raw.main_image:
        images.append(ShopifyImage(src=raw.main_image, position=1, alt_text=raw.title))
    for idx, img in enumerate(raw.gallery_images, start=2):
        images.append(ShopifyImage(src=img, position=idx, alt_text=raw.title))

    body_html = raw.description_html or ""
    if raw.detail_images:
        body_html += "".join(
            f'<p><img src="{src}" alt="{raw.title or handle}" /></p>' for src in raw.detail_images
        )

    return ShopifyRecord(
        handle=handle,
        title=raw.title or "Untitled Product",
        body_html=body_html,
        vendor=raw.vendor or "Unknown",
        product_type=raw.product_type or "General",
        tags=raw.tags,
        published=True,
        variants=[variant],
        images=images,
    )
