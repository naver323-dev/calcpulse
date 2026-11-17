#!/usr/bin/env python3
"""Offline tests for the daily pipeline (scripts/collect_topic.py, scripts/generate_guide.py).

No network and no API key: the fixtures stand in for what the model returns, so this runs in
`npm test` and in CI on every push. What it proves is the part that must never regress — a bad
draft cannot become a page, a duplicate cannot be published, and the rendered page carries the
calculator, the sibling-site link and the internal links the site depends on.

    python3 scripts/test_pipeline.py
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import collect_topic  # noqa: E402
import generate_guide  # noqa: E402

FIXTURE = SCRIPTS / "fixtures" / "guide_fixture.json"
EXISTING = {"ai-api-cost-calculator", "saas-break-even-calculator", "payment-fee-calculator"}

passed = 0


def check(name: str, fn) -> None:
    global passed
    try:
        fn()
    except AssertionError as exc:
        print(f"  FAIL  {name}: {exc}")
        raise SystemExit(1)
    except Exception:  # noqa: BLE001 - a crash in a test is a failure with a trace
        print(f"  ERROR {name}")
        traceback.print_exc()
        raise SystemExit(1)
    passed += 1
    print(f"  ok  {name}")


def draft() -> dict:
    return generate_guide.normalize_draft(json.loads(FIXTURE.read_text(encoding="utf-8")), "AI cost")


def mutated(change) -> list[str]:
    candidate = json.loads(FIXTURE.read_text(encoding="utf-8"))
    change(candidate)
    return generate_guide.validate_draft(
        generate_guide.normalize_draft(candidate, candidate.get("topic", "AI cost")), EXISTING
    )


print("validator")

check("the fixture draft passes every rule", lambda: (
    (lambda problems: (_ for _ in ()).throw(AssertionError(problems)) if problems else None)(
        generate_guide.validate_draft(draft(), EXISTING)
    )
))


def rejects(label: str, change, expect: str) -> None:
    problems = mutated(change)
    assert problems, f"{label} was accepted"
    joined = " ".join(problems)
    assert expect in joined, f"{label} was rejected for the wrong reason: {problems[:2]}"


check("a forbidden topic word is refused", lambda: rejects(
    "gambling", lambda d: d["sections"][0]["paragraphs"].append("Also casino loyalty."), "banned term"
))
check("a defence topic word is refused", lambda: rejects(
    "defence", lambda d: d["sections"][0]["paragraphs"].append("Ask 국방."), "banned term"
))
check("a link in the draft is refused", lambda: rejects(
    "link", lambda d: d["sections"][0]["paragraphs"].append("See https://example.com."), "contains a link"
))
check("braces that would break Astro are refused", lambda: rejects(
    "brace", lambda d: d["sections"][0]["paragraphs"].append("Enter {n} requests."), "misread"
))
check("a published slug is refused", lambda: rejects(
    "slug", lambda d: d.update(slug="saas-break-even-calculator"), "already published"
))
check("an unknown topic is refused", lambda: rejects(
    "topic", lambda d: d.update(topic="Politics"), "not one of"
))
check("a short body is refused", lambda: rejects(
    "short", lambda d: d.update(sections=d["sections"][:1]), "sections must be"
))

print("rendering")

page = generate_guide.render_page(draft(), {
    "source": "Hacker News",
    "source_title": "Show HN: a fixture story",
    "source_url": "https://news.ycombinator.com/item?id=1",
    "points": 12,
    "family": "AI cost",
}, "2026-11-17")


def render_contains() -> None:
    assert "guideBySlug('prompt-cache-hit-rate-value')" in page, "page must read its registry entry"
    assert "<LlmApiCostCalculator />" in page, "the AI-cost family must render its calculator"
    assert "https://stackverdict-8jj.pages.dev" in page, "the sibling-site link is missing"
    assert "/guides/saas-break-even-calculator/" in page and "/guides/payment-fee-calculator/" in page, (
        "internal links to the other calculators are missing"
    )
    assert "CalcPulse Editorial Team" in page, "byline must be the brand, never a person"
    assert "Kim" not in page and "김호빈" not in page, "a person's name leaked into the page"
    assert page.count("<h2") >= 5, "the rendered page lost its sections"


check("the page carries the calculator, both internal links and the sibling site", render_contains)
check("the page has no unescaped braces outside the template", lambda: (
    # Every brace in the rendered page belongs to the template's own expressions.
    (lambda braces: None if braces else (_ for _ in ()).throw(AssertionError("no template braces found")))(
        [line for line in page.splitlines() if "{" in line]
    )
))

print("collection")

check("a finance story does not pass as an AI-cost candidate", lambda: (
    (lambda bonus: None if bonus == 0 else (_ for _ in ()).throw(AssertionError(f"bonus {bonus}")))(
        collect_topic.relevance({"source_title": "Stripe closed our account"}, "AI cost", "LLM cost")
    )
))
check("an on-topic story passes", lambda: (
    (lambda bonus: None if bonus > 0 else (_ for _ in ()).throw(AssertionError("no bonus")))(
        collect_topic.relevance({"source_title": "LLM inference cost at scale"}, "AI cost", "LLM cost")
    )
))
check("a published title is treated as a duplicate", lambda: (
    (lambda duplicate: None if duplicate[0] else (_ for _ in ()).throw(AssertionError("not flagged")))(
        collect_topic.is_duplicate(
            {"source_url": "https://example.test/x", "source_title": "What a prompt cache hit is actually worth"},
            [],
            {"published": [{"date": "2026-11-16", "slug": "prompt-cache-hit-rate-value",
                            "title": "What a prompt cache hit is actually worth",
                            "source_url": "https://example.test/y"}]},
        )
    )
))
check("a title close to an existing guide is refused", lambda: (
    (lambda duplicate: None if duplicate[0] else (_ for _ in ()).throw(AssertionError("not flagged")))(
        collect_topic.is_duplicate(
            {"source_url": "https://example.test/x", "source_title": "Prompt caching hit rate value"},
            [{"slug": "prompt-cache-hit-rate-value", "h1": "A prompt cache hit is worth a discount",
              "keywords": ["prompt caching cost", "cache hit rate"]}],
            {"published": []},
        )
    )
))
check("the same source URL is never used twice", lambda: (
    (lambda duplicate: None if duplicate[0] else (_ for _ in ()).throw(AssertionError("not flagged")))(
        collect_topic.is_duplicate(
            {"source_url": "https://example.test/x", "source_title": "Something else entirely"},
            [],
            {"published": [{"source_url": "https://example.test/x", "title": "Old", "slug": "old"}]},
        )
    )
))
check("the family rotates across the three topics", lambda: (
    None
    if {collect_topic.family_for_today(datetime(2026, 11, day, tzinfo=timezone.utc)) for day in (17, 18, 19)}
    == set(generate_guide.FAMILY_CALCULATOR)
    else (_ for _ in ()).throw(AssertionError("rotation does not cover every family"))
))

print("registry")

check("the registry parses the published guides", lambda: (
    None
    if {"payment-fee-calculator"} <= {guide["slug"] for guide in collect_topic.published_guides()}
    else (_ for _ in ()).throw(AssertionError("payment-fee-calculator missing from guides.ts"))
))
check("a registry entry is TypeScript with the calculator label", lambda: (
    None
    if 'calculator: "LLM API cost calculator"' in generate_guide.registry_entry(draft(), "2026-11-17")
    else (_ for _ in ()).throw(AssertionError("calculator label missing"))
))

print(f"\n{passed} pipeline checks passed")
