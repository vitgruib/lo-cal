from datetime import date

from lo_cal_mcp.server import search

TODAY = date(2026, 11, 5)
DATA = {"events": [
    {"id": "a", "title": "Pizza social", "start": "2026-11-05T18:00:00-08:00", "tags": ["Free food"],
     "free": True, "region": "Campus", "url": "https://luma.com/a"},
    {"id": "b", "title": "Rust talk", "start": "2026-11-06T12:00:00-08:00", "tags": ["Talks"],
     "region": "Berkeley", "url": "https://luma.com/b", "description": "Ownership and borrowing"},
    {"id": "c", "title": "Hackathon", "start": "2026-11-17T10:00:00-08:00", "tags": ["Hackathons"],
     "url": "https://luma.com/c"},
]}


def titles(result):
    return [e["title"] for e in result["events"]]


def test_defaults_to_the_coming_week():
    result = search(DATA, "", None, None, [], [], False, 30, TODAY)

    assert titles(result) == ["Pizza social", "Rust talk"]
    assert (result["from"], result["to"]) == ("2026-11-05", "2026-11-11")


def test_filters_combine():
    assert titles(search(DATA, "", None, None, ["Free food"], ["Campus"], True, 30, TODAY)) == ["Pizza social"]
    assert titles(search(DATA, "", None, None, [], ["Campus"], False, 30, TODAY)) == ["Pizza social"]


def test_query_words_all_match_including_description():
    assert titles(search(DATA, "rust borrowing", None, None, [], [], False, 30, TODAY)) == ["Rust talk"]
    assert titles(search(DATA, "rust pizza", None, None, [], [], False, 30, TODAY)) == []


def test_explicit_dates_and_limit_report_the_full_total():
    result = search(DATA, "", "2026-11-01", "2026-11-30", [], [], False, 1, TODAY)

    assert titles(result) == ["Pizza social"] and result["total"] == 3
