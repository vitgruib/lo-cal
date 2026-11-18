"""Upcoming events as plain text for AI assistants: everything in llms-full.txt, and small slices\n(today, tomorrow, the weekend, each day, each topic) under data/llms/."""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .enrich import TOPICS
from .models import Event
from .reports import describe

PACIFIC = ZoneInfo("America/Los_Angeles")


def slug(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")


def time_range(e: Event) -> str:
    if e.all_day:
        return "All day"
    start = e.start.astimezone(PACIFIC)
    out = f"{start:%-I:%M %p}".replace(":00", "")
    if e.end:
        out += f"–{e.end.astimezone(PACIFIC):%-I:%M %p}".replace(":00", "")
    return out


def _line(e: Event) -> str:
    facts = [time_range(e), e.title, e.venue or e.address or ("Online" if e.online else ""), e.host or "",
             e.region or "", ", ".join(e.tags), "Free" if e.free else "",
             f"Getting in: {'; '.join(e.access)}" if e.access else "",
             *(f"Reported by a visitor (unverified): {describe(r)}" for r in e.reports),
             e.url, f"id:{e.id}"]
    # A " | " inside a title would read as a field break.
    return "- " + " | ".join(f.replace("|", "/") for f in facts if f)


def _render(title: str, events: list[Event], site_url: str, now: datetime) -> str:
    lines = [
        f"# Lo-Cal: {title}",
        "",
        f"Generated {now.astimezone(PACIFIC):%Y-%m-%d %H:%M} Pacific. {len(events)} events, sorted by start.",
        (f"Times are Pacific. Other days and topics: {site_url}data/llms/index.txt. "
         f"About the fields and rules: {site_url}llms.txt"),
        ("Each line: time | title | place | host | area | tags | Free | Getting in | reports | event link | "
         f"id; empty fields are left out. Lo-Cal's page for an event: {site_url}e/<id>.html"),
        "Tags, area, free and getting-in come from keyword rules, not people: check the event link.",
    ]
    day = None
    for e in events:
        d = e.start.astimezone(PACIFIC).date()
        if d != day:
            day = d
            lines += ["", f"## {d:%A %B %-d, %Y}", ""]
        lines.append(_line(e))
    if not events:
        lines += ["", "No events listed."]
    return "\n".join(lines) + "\n"


def write_llms_full(events: list[Event], site_url: str, path: Path, now: datetime) -> None:
    path.write_text(_render("upcoming Berkeley events", events, site_url, now))


def slices(events: list[Event], now: datetime) -> dict[str, tuple[str, list[Event]]]:
    """Slice name (no extension) -> (title, events); shared by the text and JSON slices."""
    def day(e: Event) -> date:
        return e.start.astimezone(PACIFIC).date()

    today = now.astimezone(PACIFIC).date()
    saturday = today + timedelta(days=5 - today.weekday())  # on a Sunday, that's yesterday
    weekend = {saturday, saturday + timedelta(days=1)}
    week = today + timedelta(days=7)
    files = {
        "today": (f"today, {today:%A %B %-d}", [e for e in events if day(e) == today]),
        "tomorrow": ("tomorrow", [e for e in events if day(e) == today + timedelta(days=1)]),
        "weekend": ("this weekend", [e for e in events if day(e) in weekend]),
    }
    for t in TOPICS:
        files[f"topics/{slug(t)}"] = (f"{t}, next 7 days", [e for e in events if t in e.tags and day(e) < week])
    for d in sorted({day(e) for e in events}):
        files[f"days/{d}"] = (f"{d:%A %B %-d, %Y}", [e for e in events if day(e) == d])
    return files


def write_llms_slices(events: list[Event], site_url: str, out: Path, now: datetime) -> None:
    """Small files an assistant can read whole in one fetch, at addresses that never change:
    llms-full.txt is too long for most assistants' web tools, which cut a page off part way."""
    files = {f"{name}.txt": v for name, v in slices(events, now).items()}
    for sub in ("days", "topics"):
        for old in (out / sub).glob("*.txt"):
            if f"{sub}/{old.name}" not in files:
                old.unlink()
    index = ["# Lo-Cal for AI assistants", "",
             "Each file below is one slice of upcoming Berkeley events, small enough to read in one fetch.",
             (f"Generated {now.astimezone(PACIFIC):%Y-%m-%d %H:%M} Pacific. Every event at once: "
             f"{site_url}data/llms-full.txt"), ""]
    for name, (title, chosen) in files.items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(_render(title, chosen, site_url, now))
        index.append(f"- {site_url}data/llms/{name}: {title} ({len(chosen)} events)")
    (out / "index.txt").write_text("\n".join(index) + "\n")


def _slim(e: Event) -> dict:
    return {k: v for k, v in e.to_json().items() if k not in ("image", "source_tags", "source_access")}


def write_json_slices(events: list[Event], out: Path, now: datetime) -> None:
    """The same slices as events.json-style JSON, for agents that parse rather than read:
    events.json itself is too big for most assistants' fetch tools. Image and the source's raw
    tags and access are left out (events.json has them): they cost a sixth of the size and tell an
    assistant nothing the rest of the record doesn't."""
    files = {f"{name}.json": v for name, v in slices(events, now).items()}
    for sub in ("days", "topics"):
        for old in (out / sub).glob("*.json"):
            if f"{sub}/{old.name}" not in files:
                old.unlink()
    for name, (title, chosen) in files.items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(json.dumps({"generated_at": now.isoformat(), "title": title,
                                            "events": [_slim(e) for e in chosen]},
                                           ensure_ascii=False, separators=(",", ":")))
