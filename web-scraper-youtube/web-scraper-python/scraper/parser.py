"""Parsing routines extracting data from Cafe24 product pages."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import RawProductData
from .utils import split_tags


class Cafe24Parser:
    """Parse Cafe24 product HTML into RawProductData."""

    def parse(self, url: str, html: str) -> RawProductData:
        soup = BeautifulSoup(html, "html.parser")
        raw = RawProductData(source_url=url)

        raw.title = self._parse_title(soup)
        raw.sku = self._parse_sku(soup)
        raw.vendor = self._parse_vendor(soup)
        raw.product_type = self._parse_product_type(soup)
        raw.tags = self._parse_tags(soup)
        raw.description_html = self._parse_description(soup)
        raw.description_ko, raw.description_en = self._parse_multilingual_descriptions(soup)
        raw.price, raw.sale_price, raw.currency = self._parse_price(soup)
        raw.main_image, raw.gallery_images = self._parse_images(soup, url)
        raw.detail_images = self._parse_detail_images(soup, url)

        return raw

    def _parse_title(self, soup: BeautifulSoup) -> Optional[str]:
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            return meta_title["content"].strip()
        title_node = soup.select_one(".product_tit, #prdDetail h2, .infoArea h3")
        if title_node:
            return title_node.get_text(strip=True)
        return None

    def _parse_sku(self, soup: BeautifulSoup) -> Optional[str]:
        sku_node = soup.select_one(".product_sku, #product_detail_info [data-sku], .infoArea .info li span.sku")
        if sku_node:
            return sku_node.get_text(strip=True)
        meta_sku = soup.find("meta", property="product:retailer_item_id")
        if meta_sku and meta_sku.get("content"):
            return meta_sku["content"].strip()
        return None

    def _parse_vendor(self, soup: BeautifulSoup) -> Optional[str]:
        detail_table_rows = soup.select("table tr")
        for row in detail_table_rows:
            header = row.find("th")
            if not header:
                continue
            header_text = header.get_text(strip=True).lower()
            if "brand" in header_text:
                cell = row.find("td")
                if cell:
                    value = cell.get_text(strip=True)
                    if value:
                        return value

        vendor_meta = soup.find("meta", property="og:site_name")
        if vendor_meta and vendor_meta.get("content"):
            return vendor_meta["content"].strip()
        vendor_node = soup.select_one(".product_vendor, .infoArea .info li span.supplier")
        if vendor_node:
            return vendor_node.get_text(strip=True)
        return None

    def _parse_product_type(self, soup: BeautifulSoup) -> Optional[str]:
        meta_type = soup.find("meta", property="product:category")
        if meta_type and meta_type.get("content"):
            return meta_type["content"].strip()

        breadcrumb = soup.select(".path li a, .xans-product-menupackage a, nav.breadcrumb a")
        if breadcrumb:
            return breadcrumb[-1].get_text(strip=True)
        return None

    def _parse_tags(self, soup: BeautifulSoup) -> list[str]:
        tag_nodes = soup.select(".product_tags a")
        if tag_nodes:
            return [node.get_text(strip=True) for node in tag_nodes if node.get_text(strip=True)]
        tag_meta = soup.find("meta", attrs={"name": "keywords"})
        if tag_meta and tag_meta.get("content"):
            return split_tags(tag_meta["content"])
        return []

    def _parse_description(self, soup: BeautifulSoup) -> Optional[str]:
        detail_section = soup.select_one("#prdDetail, .cont_detail, .productDetail")
        if detail_section:
            return str(detail_section)
        return None

    def _parse_multilingual_descriptions(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        ko_node = soup.select_one(".product-detail-ko, [lang=ko]")
        en_node = soup.select_one(".product-detail-en, [lang=en]")
        ko_text = ko_node.get_text("\n", strip=True) if ko_node else None
        en_text = en_node.get_text("\n", strip=True) if en_node else None
        return ko_text, en_text

    def _parse_price(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[float], Optional[str]]:
        amount_meta = soup.find("meta", property="product:price:amount")
        currency_meta = soup.find("meta", property="product:price:currency")
        sale_meta = soup.find("meta", property="product:sale_price:amount")
        price = self._to_float(amount_meta.get("content") if amount_meta else None)
        sale_price = self._to_float(sale_meta.get("content") if sale_meta else None)
        currency = currency_meta.get("content") if currency_meta else None

        if price is not None:
            return price, sale_price, currency

        price_node = soup.select_one(".product_price, .price .sell")
        sale_node = soup.select_one(".price .strike")
        return (
            self._to_float(price_node.get_text(strip=True) if price_node else None),
            self._to_float(sale_node.get_text(strip=True) if sale_node else None),
            currency,
        )

    def _parse_images(self, soup: BeautifulSoup, base_url: str) -> tuple[Optional[str], list[str]]:
        main_meta = soup.find("meta", property="og:image")
        main = self._absolute(main_meta.get("content"), base_url) if main_meta and main_meta.get("content") else None
        gallery_nodes = soup.select(".product_thumbs img, .xans-product-addimage img")
        gallery = []
        for node in gallery_nodes:
            src = node.get("data-src") or node.get("src")
            if src:
                gallery.append(self._absolute(src, base_url))
        return main, gallery

    def _parse_detail_images(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        detail_section = soup.select_one("#prdDetail, .cont_detail, .productDetail")
        if not detail_section:
            return []
        images = []
        for node in detail_section.find_all("img"):
            src = node.get("data-src") or node.get("src")
            if src:
                images.append(self._absolute(src, base_url))
        return images

    def _to_float(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        cleaned = value.replace(",", "").replace("₩", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _absolute(self, src: str, base_url: str) -> str:
        if not src:
            return src
        src = src.strip()
        if src.startswith("http://") or src.startswith("https://"):
            return src
        return urljoin(base_url, src)
