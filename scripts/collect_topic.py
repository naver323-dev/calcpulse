#!/usr/bin/env python3
"""Pick one topic for the daily guide, from free public sources.

One run = one topic. The sources are the free ones that need no key and no account:

  * Hacker News (Algolia search API)  — a story that people are already arguing about,
  * GitHub search (public API)        — a repository or tool that is visibly being adopted,
  * Google Trends daily RSS           — last resort, only when the first two return nothing.

The site has three topics (AI running cost, SaaS and tooling, small-business finance); the
day of the year picks which one today's guide belongs to, so the pipeline does not publish
five AI-cost guides in a row. A candidate is dropped when it repeats something CalcPulse has
already published: the same story URL, a near-identical title, or a keyword the existing
guides already own.

Usage
    python3 scripts/collect_topic.py                 # print the topic as JSON
    python3 scripts/collect_topic.py --family "AI cost"
    python3 scripts/collect_topic.py --explain       # human-readable reasoning on stderr

Exit codes: 0 topic printed, 2 nothing usable found today, 3 the sources could not be read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
GUIDES_TS = ROOT / "src" / "data" / "guides.ts"
STATE_PATH = ROOT / "scripts" / "pipeline_state.json"

USER_AGENT = "CalcPulse-pipeline/1.0 (+https://calcpulse.pages.dev)"

# Each query belongs to exactly one of the site's three topics, so the chosen family is a
# property of the query rather than something a model has to guess.
QUERIES: dict[str, tuple[str, ...]] = {
    "AI cost": (
        "LLM cost",
        "token pricing",
        "AI inference cost",
        "prompt caching",
        "AI API spend",
        "model routing",
        "AI agent cost",
    ),
    "SaaS & tooling": (
        "SaaS pricing",
        "usage-based pricing",
        "seat-based pricing",
        "developer tool ROI",
        "AI coding assistant",
        "build vs buy software",
        "software subscriptions",
        "tool sprawl",
        "self-hosted software",
        "vendor lock-in",
    ),
    "Small-business finance": (
        "payment processing fees",
        "Stripe fees",
        "invoicing",
        "freelance rates",
        "small business",
        "cash flow",
        "chargebacks",
        "creator payout",
        "subscription churn",
    ),
}

# How far back and how popular a story has to be, per topic. Finance stories are rarer on
# Hacker News, so they are searched further back at a lower bar rather than being dropped.
FAMILY_SETTINGS: dict[str, tuple[int, int]] = {
    "AI cost": (21, 40),
    "SaaS & tooling": (30, 30),
    "Small-business finance": (60, 15),
}

FAMILIES = tuple(QUERIES)

# A story only belongs to a topic if its title actually carries one of these words. The
# search API matches loosely ("model routing" returns a speech-recognition demo), so the
# filter is what keeps the guide on the site's subject.
ANCHORS: dict[str, frozenset[str]] = {
    "AI cost": frozenset(
        {
            "llm", "llms", "token", "tokens", "inference", "api", "cost", "costs", "spend",
            "bill", "billing", "pricing", "price", "prices", "budget", "cache", "caching",
            "gpu", "model", "models", "agent", "agents", "prompt", "quota", "rate", "limit",
        }
    ),
    "SaaS & tooling": frozenset(
        {
            "saas", "subscription", "subscriptions", "seat", "seats", "licence", "license",
            "software", "tool", "tools", "tooling", "vendor", "vendors", "developer",
            "devtools", "buy", "build", "pricing", "price", "plan", "plans", "billing",
        }
    ),
    "Small-business finance": frozenset(
        {
            "payment", "payments", "fee", "fees", "invoice", "invoices", "invoicing", "cash",
            "churn", "payout", "payouts", "stripe", "paypal", "bookkeeping", "tax", "taxes",
            "freelance", "freelancer", "small", "business", "revenue", "margin", "refund",
        }
    ),
}

# Words too common to prove anything about a topic.
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with", "your", "you",
    "how", "what", "why", "when", "is", "are", "it", "this", "that", "at", "by", "from",
    "new", "why", "we", "i", "my", "our", "its", "be", "do", "does", "can", "should",
    "vs", "versus", "guide", "calculator", "cost", "costs", "pricing", "price", "prices",
}

JACCARD_LIMIT = 0.45


# --------------------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------------------
def log(message: str) -> None:
    print(f"  · {message}", file=sys.stderr)


def fetch(url: str, timeout: int = 25) -> bytes | None:
    request = urlrequest.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    for attempt in range(2):
        try:
            with urlrequest.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urlerror.HTTPError, urlerror.URLError, TimeoutError, OSError) as exc:
            log(f"{url} failed ({exc}); attempt {attempt + 1}/2")
            if attempt == 0:
                time.sleep(2)
    return None


def fetch_json(url: str) -> dict | None:
    raw = fetch(url)
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        log(f"{url} did not return JSON")
        return None


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+|[\uac00-\ud7a3]+", (text or "").lower())
    return {word for word in words if word not in STOPWORDS and len(word) > 2}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def read_state() -> dict:
    if not STATE_PATH.is_file():
        return {"published": [], "skips": [], "runs": []}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"published": [], "skips": [], "runs": []}
    for key in ("published", "skips", "runs"):
        state.setdefault(key, [])
    return state


def published_guides() -> list[dict]:
    """The guides already on the site: slug, h1 and keywords, read from the registry."""
    if not GUIDES_TS.is_file():
        return []
    text = GUIDES_TS.read_text(encoding="utf-8")
    entries = []
    for block in re.split(r"\n  \{\n", text)[1:]:
        def field(name: str) -> str:
            match = re.search(rf"{name}:\s*\n?\s*['\"](.+?)['\"],\n", block, re.S)
            return match.group(1) if match else ""

        keywords = re.search(r"keywords:\s*\[(.+?)\]", block, re.S)
        entries.append(
            {
                "slug": field("slug"),
                "h1": field("h1"),
                "title": field("title"),
                "keywords": re.findall(r"['\"](.+?)['\"]", keywords.group(1)) if keywords else [],
            }
        )
    return [entry for entry in entries if entry["slug"]]


# --------------------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------------------
def hacker_news(query: str, days: int = 21, min_points: int = 40) -> list[dict]:
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    filters = urlparse.quote(f"points>{min_points},created_at_i>{since}")
    url = (
        "https://hn.algolia.com/api/v1/search"
        f"?query={urlparse.quote(query)}&tags=story&hitsPerPage=10&numericFilters={filters}"
    )
    data = fetch_json(url)
    if not data:
        return []
    stories = []
    for hit in data.get("hits") or []:
        title = (hit.get("title") or "").strip()
        if not title:
            continue
        stories.append(
            {
                "source": "Hacker News",
                "source_title": title,
                "source_url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                "discussion_url": f"https://news.ycombinator.com/item?id={hit['objectID']}",
                "points": int(hit.get("points") or 0),
                "comments": int(hit.get("num_comments") or 0),
                "published_at": hit.get("created_at") or "",
                "query": query,
            }
        )
    return stories


def github_repos(query: str, days: int = 45, min_stars: int = 40) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    url = (
        "https://api.github.com/search/repositories"
        f"?q={urlparse.quote(query)}+created%3A%3E{since}+stars%3A%3E%3D{min_stars}"
        "&sort=stars&order=desc&per_page=5"
    )
    data = fetch_json(url)
    if not data or "items" not in data:
        return []
    repos = []
    for item in data["items"][:5]:
        repos.append(
            {
                "source": "GitHub",
                "source_title": f"{item['full_name']}: {(item.get('description') or '').strip()}",
                "source_url": item["html_url"],
                "discussion_url": item["html_url"],
                "points": int(item.get("stargazers_count") or 0),
                "comments": int(item.get("open_issues_count") or 0),
                "published_at": item.get("created_at") or "",
                "query": query,
            }
        )
    return repos


def google_trends() -> list[dict]:
    raw = fetch("https://trends.google.com/trending/rss?geo=US")
    if not raw:
        return []
    text = raw.decode("utf-8", "replace")
    trends = []
    for title in re.findall(r"<item>.*?<title>(.*?)</title>", text, re.S)[:10]:
        trends.append(
            {
                "source": "Google Trends",
                "source_title": re.sub(r"<!\[CDATA\[|\]\]>", "", title).strip(),
                "source_url": "https://trends.google.com/trending?geo=US",
                "discussion_url": "https://trends.google.com/trending?geo=US",
                "points": 0,
                "comments": 0,
                "published_at": "",
                "query": "trending",
            }
        )
    return trends


# --------------------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------------------
def relevance(candidate: dict, family: str, query: str) -> int:
    """0 = off-topic, otherwise a bonus that lifts a query match over a loose one."""
    title = tokens(candidate.get("source_title", ""))
    query_hit = bool(title & (tokens(query) - {"ai"}))
    anchor_hit = bool(title & ANCHORS[family])
    if not (query_hit or anchor_hit):
        return 0
    return 80 * query_hit + 30 * anchor_hit


def family_for_today(day: datetime) -> str:
    return FAMILIES[day.timetuple().tm_yday % len(FAMILIES)]


def is_duplicate(candidate: dict, guides: list[dict], state: dict) -> tuple[bool, str]:
    url = (candidate.get("source_url") or "").rstrip("/")
    for published in state.get("published", []):
        if published.get("source_url", "").rstrip("/") == url:
            return True, "same source URL already used"
        if jaccard(tokens(published.get("title", "")), tokens(candidate["source_title"])) > 0.6:
            return True, f"near-duplicate of the published guide {published.get('slug')}"

    candidate_tokens = tokens(candidate["source_title"])
    for guide in guides:
        theirs = tokens(f"{guide['h1']} {' '.join(guide['keywords'])}")
        if jaccard(candidate_tokens, theirs) >= JACCARD_LIMIT:
            return True, f"too close to the existing guide {guide['slug']}"
        if (candidate.get("query") or "").lower() in [k.lower() for k in guide["keywords"]]:
            return True, f"keyword {candidate['query']!r} already used by {guide['slug']}"
    return False, ""


def collect(family: str | None = None, day: datetime | None = None) -> dict | None:
    day = day or datetime.now(timezone.utc)
    guides = published_guides()
    state = read_state()
    wanted = family or family_for_today(day)
    log(f"family for {day.date()} is {wanted!r} ({len(guides)} guides already published)")

    candidates: list[dict] = []
    days, min_points = FAMILY_SETTINGS[wanted]
    for query in QUERIES[wanted]:
        found = hacker_news(query, days=days, min_points=min_points)
        log(f"Hacker News {query!r}: {len(found)} stories")
        candidates.extend(found)

    if len(candidates) < 3:
        for query in QUERIES[wanted][:2]:
            found = github_repos(query)
            log(f"GitHub {query!r}: {len(found)} repositories")
            candidates.extend(found)

    if not candidates:
        log("no stories or repositories; falling back to Google Trends")
        candidates = google_trends()

    scored: list[dict] = []
    for candidate in candidates:
        bonus = relevance(candidate, wanted, candidate.get("query", ""))
        if not bonus:
            continue
        candidate["relevance"] = bonus
        scored.append(candidate)
    log(f"{len(scored)} of {len(candidates)} candidates are on-topic")

    seen: set[str] = set()
    ranked: list[dict] = []
    for candidate in sorted(
        scored,
        key=lambda item: item["points"] + item["comments"] * 0.5 + item["relevance"],
        reverse=True,
    ):
        key = candidate["source_url"].rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        duplicate, why = is_duplicate(candidate, guides, state)
        if duplicate:
            log(f"skip {candidate['source_title'][:60]!r}: {why}")
            continue
        candidate["family"] = wanted
        ranked.append(candidate)

    if not ranked:
        return None

    pick = ranked[0]
    pick["collected_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log(f"picked {pick['source']} {pick['source_title'][:70]!r} ({pick['points']} points)")
    return pick


def main() -> int:
    parser = argparse.ArgumentParser(description="Pick one topic for today's CalcPulse guide.")
    parser.add_argument("--family", choices=FAMILIES, help="force a topic instead of rotating")
    parser.add_argument("--date", help="YYYY-MM-DD, for a deterministic run")
    parser.add_argument("--out", help="write the topic JSON to this path as well")
    args = parser.parse_args()

    day = datetime.now(timezone.utc)
    if args.date:
        day = datetime.fromisoformat(args.date).replace(tzinfo=timezone.utc)

    topic = collect(args.family, day)
    if not topic:
        print("no usable topic today", file=sys.stderr)
        return 2

    payload = json.dumps(topic, ensure_ascii=False, indent=2)
    print(payload)
    if args.out:
        __import__("pathlib").Path(args.out).write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
