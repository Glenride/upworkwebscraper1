"""Data models for Cafe24 scraping and Shopify export."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RawProductData:
    """Intermediate representation extracted from Cafe24 product pages."""

    source_url: str
    title: Optional[str] = None
    sku: Optional[str] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description_html: Optional[str] = None
    description_ko: Optional[str] = None
    description_en: Optional[str] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None
    currency: Optional[str] = None
    main_image: Optional[str] = None
    gallery_images: List[str] = field(default_factory=list)
    detail_images: List[str] = field(default_factory=list)


@dataclass
class ShopifyVariant:
    sku: str
    price: float
    compare_at_price: Optional[float]
    requires_shipping: bool = True
    grams: int = 0
    inventory_quantity: int = 0
    inventory_policy: str = "continue"
    fulfillment_service: str = "manual"
    option1_name: str = "Title"
    option1_value: str = "Default"


@dataclass
class ShopifyImage:
    src: str
    position: int
    alt_text: Optional[str] = None


@dataclass
class ShopifyRecord:
    handle: str
    title: str
    body_html: str
    vendor: str
    product_type: str
    tags: List[str]
    published: bool
    variants: List[ShopifyVariant]
    images: List[ShopifyImage]

    def to_rows(self) -> List[dict]:
        rows: List[dict] = []
        base_row = {
            "Handle": self.handle,
            "Title": self.title,
            "Body (HTML)": self.body_html,
            "Vendor": self.vendor,
            "Product Category": "",
            "Type": self.product_type,
            "Tags": ",".join(self.tags),
            "Published": "TRUE" if self.published else "FALSE",
        }

        if not self.variants:
            rows.append({**base_row, **_empty_variant_row(), **_empty_image_row()})
            return rows

        for idx, variant in enumerate(self.variants):
            variant_row = {
                "Option1 Name": variant.option1_name,
                "Option1 Value": variant.option1_value,
                "Variant SKU": variant.sku,
                "Variant Price": f"{variant.price:.2f}",
                "Variant Compare At Price": f"{variant.compare_at_price:.2f}" if variant.compare_at_price else "",
                "Variant Inventory Qty": variant.inventory_quantity,
                "Variant Inventory Policy": variant.inventory_policy,
                "Variant Fulfillment Service": variant.fulfillment_service,
                "Variant Requires Shipping": "TRUE" if variant.requires_shipping else "FALSE",
                "Variant Grams": variant.grams,
            }

            image_row = _image_row(self.images, idx)
            rows.append({**base_row, **variant_row, **image_row})

        return rows


def _image_row(images: List[ShopifyImage], variant_index: int) -> dict:
    if not images:
        return _empty_image_row()

    image = images[min(variant_index, len(images) - 1)]
    return {
        "Image Src": image.src,
        "Image Position": image.position,
        "Image Alt Text": image.alt_text or "",
    }


def _empty_variant_row() -> dict:
    return {
        "Option1 Name": "Title",
        "Option1 Value": "Default",
        "Variant SKU": "",
        "Variant Price": "",
        "Variant Compare At Price": "",
        "Variant Inventory Qty": 0,
        "Variant Inventory Policy": "continue",
        "Variant Fulfillment Service": "manual",
        "Variant Requires Shipping": "TRUE",
        "Variant Grams": 0,
    }


def _empty_image_row() -> dict:
    return {"Image Src": "", "Image Position": "", "Image Alt Text": ""}
