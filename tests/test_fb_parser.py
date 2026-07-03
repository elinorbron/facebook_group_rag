from pathlib import Path

from src.fb_parser import load_posts, parse_html_file

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
SAMPLE_HTML = EXAMPLES_DIR / "group_posts_and_comments.html"


def test_parse_html_file_extracts_posts():
    posts = parse_html_file(SAMPLE_HTML)
    assert len(posts) == 2
    assert posts[0].group_name == "Coaching Circle"
    assert posts[0].post_date == "2025-09-02"
    assert posts[0].post_type == "celebration"
    assert "workbook" in posts[0].body.lower()


def test_load_posts_group_filter_matches_any():
    posts = load_posts(data_dir=EXAMPLES_DIR, group_filter="Coaching")
    assert len(posts) == 1
    assert posts[0].group_name == "Coaching Circle"


def test_load_posts_group_filter_multiple():
    posts = load_posts(data_dir=EXAMPLES_DIR, group_filter="Coaching,Other")
    assert len(posts) == 2


def test_load_posts_no_filter_returns_all():
    posts = load_posts(data_dir=EXAMPLES_DIR, group_filter="")
    assert len(posts) == 2
