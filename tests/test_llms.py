import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from scraper.llms import write_json_slices, write_llms_slices
from scraper.models import Event

PT = ZoneInfo("America/Los_Angeles")
NOW = datetime(2026, 11, 5, 9, tzinfo=PT)  # a Thursday
SITE = "https://example.github.io/lo-cal/"


def ev(title, start, tags=()):
    return Event(title=title, start=start, url=f"https://luma.com/{title.split()[0].lower()}", source="luma",
                 tags=list(tags))


EVENTS = [
    ev("Pizza social", NOW.replace(hour=18), ["Free food", "Social"]),
    ev("Rust talk", NOW.replace(hour=12) + timedelta(days=1), ["Talks"]),
    ev("Boba night", NOW.replace(hour=20) + timedelta(days=2), ["Free food"]),
    ev("Hackathon kickoff", NOW.replace(hour=10) + timedelta(days=12), ["Hackathons"]),
]


def test_today_and_tomorrow_hold_only_their_own_day(tmp_path):
    write_llms_slices(EVENTS, SITE, tmp_path, NOW)

    today = (tmp_path / "today.txt").read_text()
    tomorrow = (tmp_path / "tomorrow.txt").read_text()

    assert "Pizza social" in today and "Rust talk" not in today
    assert "Rust talk" in tomorrow and "Pizza social" not in tomorrow
    assert "Thursday November 5, 2026" in today
    assert f"id:{EVENTS[0].id}" in today
    assert f"{SITE}e/<id>.html" in today


def test_a_pipe_in_a_title_does_not_split_the_line(tmp_path):
    write_llms_slices([ev("Demo day | Spring", NOW.replace(hour=15))], SITE, tmp_path, NOW)

    assert "Demo day / Spring" in (tmp_path / "today.txt").read_text()


def test_json_slices_match_the_text_slices(tmp_path):
    write_json_slices(EVENTS, tmp_path, NOW)

    food = json.loads((tmp_path / "topics" / "free-food.json").read_text())
    day = json.loads((tmp_path / "days" / "2026-11-17.json").read_text())

    assert [e["title"] for e in food["events"]] == ["Pizza social", "Boba night"]
    assert [e["title"] for e in day["events"]] == ["Hackathon kickoff"]


def test_weekend_and_topic_files_cover_the_coming_days(tmp_path):
    write_llms_slices(EVENTS, SITE, tmp_path, NOW)

    weekend = (tmp_path / "weekend.txt").read_text()
    food = (tmp_path / "topics" / "free-food.txt").read_text()

    assert "Boba night" in weekend and "Rust talk" not in weekend  # Saturday, not Friday
    assert "Pizza social" in food and "Boba night" in food and "Rust talk" not in food
    # Topic files stop a week out, so the hackathon twelve days away is only in its day file.
    assert "Hackathon kickoff" not in (tmp_path / "topics" / "hackathons.txt").read_text()
    assert "Hackathon kickoff" in (tmp_path / "days" / "2026-11-17.txt").read_text()


def test_index_lists_every_file_and_stale_days_are_removed(tmp_path):
    (tmp_path / "days").mkdir()
    (tmp_path / "days" / "2026-11-01.txt").write_text("old")

    write_llms_slices(EVENTS, SITE, tmp_path, NOW)
    index = (tmp_path / "index.txt").read_text()

    assert not (tmp_path / "days" / "2026-11-01.txt").exists()
    assert f"{SITE}data/llms/days/2026-11-17.txt" in index
    assert f"{SITE}data/llms/topics/free-food.txt" in index
    assert f"{SITE}data/llms/today.txt" in index
