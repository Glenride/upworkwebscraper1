from scraper.utils import slugify, split_tags


def test_slugify_basic():
    assert slugify("Cafe24 Product") == "cafe24-product"


def test_slugify_handles_empty():
    assert slugify("") == "product"


def test_split_tags_from_string():
    assert split_tags("Tag1, Tag2 , ,Tag3") == ["Tag1", "Tag2", "Tag3"]


def test_split_tags_from_iterable():
    assert split_tags([" Tag1", "Tag2 "]) == ["Tag1", "Tag2"]


def test_split_tags_none_returns_empty():
    assert split_tags(None) == []
