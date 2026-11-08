from scraper.parser import Cafe24Parser


def _load_fixture(name: str) -> str:
    from pathlib import Path

    fixture_path = Path(__file__).parent / "fixtures" / name
    return fixture_path.read_text(encoding="utf-8")


def test_parser_extracts_basic_fields():
    html = _load_fixture("product_basic.html")
    parser = Cafe24Parser()
    result = parser.parse("https://example.com/product", html)

    assert result.title == "Sample Product"
    assert result.price == 12000.0
    assert result.main_image == "https://cdn.example.com/main.jpg"


def test_parser_handles_missing_price_meta():
    html = _load_fixture("product_no_meta_price.html")
    parser = Cafe24Parser()
    result = parser.parse("https://example.com/product", html)

    assert result.price == 8990.0


def test_parser_extracts_jolse_fields():
    html = _load_fixture("jolse_product.html")
    parser = Cafe24Parser()
    url = "https://jolse.com/product/beauty-of-joseon-relief-sun-rice-probiotics-50ml/46958/"
    result = parser.parse(url, html)

    assert result.vendor == "Beauty of Joseon"
    assert result.price == 18.0
    assert result.sale_price == 9.0
    assert result.main_image and result.main_image.startswith("https://")
    assert result.detail_images
    assert all(img.startswith("http") for img in result.detail_images)
