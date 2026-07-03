from src.config import parse_group_filters


def test_parse_group_filters_empty():
    assert parse_group_filters("") == []
    assert parse_group_filters("   ") == []


def test_parse_group_filters_single():
    assert parse_group_filters("group1") == ["group1"]


def test_parse_group_filters_multiple():
    assert parse_group_filters("group1, group2") == ["group1", "group2"]
    assert parse_group_filters("group1,group2, group3") == ["group1", "group2", "group3"]
