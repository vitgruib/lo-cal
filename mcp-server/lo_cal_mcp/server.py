"""MCP server over Lo-Cal's public events.json: lets any MCP client (Claude Desktop, Cursor, a local
model's chat app) search Berkeley events with filters instead of reading text slices."""

import os
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from mcp.server.mcpserver import MCPServer

SITE = os.environ.get("LOCAL_SITE_URL", "https://vitgruib.github.io/lo-cal/")
PACIFIC = ZoneInfo("America/Los_Angeles")
CACHE_SECONDS = 600  # the site rebuilds every 3 hours

_cache: tuple[float, dict] | None = None


def fetch() -> dict:
    global _cache
    if _cache is None or time.monotonic() - _cache[0] > CACHE_SECONDS:
        r = httpx.get(f"{SITE}data/events.json", timeout=30, follow_redirects=True)
        r.raise_for_status()
        _cache = (time.monotonic(), r.json())
    return _cache[1]


def _day(e: dict) -> date:
    return datetime.fromisoformat(e["start"]).astimezone(PACIFIC).date()


def _brief(e: dict) -> dict:
    keep = ("id", "title", "start", "end", "all_day", "host", "venue", "address", "region", "online",
            "tags", "free", "access", "transit", "url")
    return {k: e[k] for k in keep if k in e} | {"lo_cal_page": f"{SITE}e/{e['id']}.html"}


def search(data: dict, query: str, start_date: str | None, end_date: str | None, topics: list[str],
           regions: list[str], free_only: bool, limit: int, today: date) -> dict:
    first = date.fromisoformat(start_date) if start_date else today
    last = date.fromisoformat(end_date) if end_date else first + timedelta(days=6)
    words = query.lower().split()
    hits = []
    for e in data["events"]:
        if not first <= _day(e) <= last:
            continue
        if topics and not set(topics) & set(e.get("tags", [])):
            continue
        if regions and e.get("region") not in regions:
            continue
        if free_only and e.get("free") is not True:
            continue
        text = " ".join([e["title"], e.get("host", ""), e.get("venue", ""), e.get("description", ""),
                         *e.get("tags", [])]).lower()
        if all(w in text for w in words):
            hits.append(e)
    hits.sort(key=lambda e: e["start"])
    return {"from": str(first), "to": str(last), "total": len(hits), "events": [_brief(e) for e in hits[:limit]],
            "note": "Tags, region, free and access come from keyword rules: check the event's url."}


server = MCPServer(
    "lo-cal",
    instructions=("Upcoming events around UC Berkeley and the Bay Area: talks, hackathons, parties, club "
                  "meetings, free food. Times are Pacific. Link people to each event's url."),
    website_url=SITE,
)


@server.tool()
def search_events(query: str = "", start_date: str | None = None, end_date: str | None = None,
                  topics: list[str] | None = None, regions: list[str] | None = None,
                  free_only: bool = False, limit: int = 30) -> dict:
    """Find upcoming events, sorted by start time.

    query: words that must all appear in the title, host, venue, description or tags (blank = any).
    start_date, end_date: YYYY-MM-DD, Pacific. Default: today through 6 days later.
    topics: any of AI & Tech, Startups, Hackathons, Career, Talks, Social, Arts & Music,
      Sports & Wellness, Community, Free food.
    regions: any of Campus, Berkeley, East Bay, San Francisco, Peninsula & South Bay, North Bay,
      Sacramento, Los Angeles, San Diego, Online.
    free_only: only events known to be free.
    """
    return search(fetch(), query, start_date, end_date, topics or [], regions or [], free_only, limit,
                  datetime.now(PACIFIC).date())


@server.tool()
def get_event(event_id: str) -> dict:
    """Everything Lo-Cal knows about one event (by the id search_events returned), including its
    description and every place it is listed."""
    for e in fetch()["events"]:
        if e["id"] == event_id:
            return e | {"lo_cal_page": f"{SITE}e/{e['id']}.html"}
    raise ValueError(f"No upcoming event with id {event_id}")


def main() -> None:
    server.run()
