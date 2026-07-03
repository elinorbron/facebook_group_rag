from langchain_core.documents import Document

from src.query_parsing import format_docs, is_summary_query, parse_month_year, parse_single_date


def test_is_summary_query():
    assert is_summary_query("Summarize my posts from April")
    assert not is_summary_query("What did I post yesterday?")


def test_parse_single_date():
    assert parse_single_date("What did I post on Sep 02, 2025?") == "2025-09-02"
    assert parse_single_date("Posts from 2025-09-04") == "2025-09-04"


def test_parse_month_year():
    assert parse_month_year("Summarize posts from April 2025") == ("2025-04-01", "2025-05-01")


def test_format_docs_includes_metadata():
    text = format_docs(
        [
            Document(
                page_content="Hello",
                metadata={"post_date": "2025-09-02", "group_name": "group1", "post_type": "post"},
            )
        ]
    )
    assert "2025-09-02" in text
    assert "group1" in text
