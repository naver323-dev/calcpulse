#!/usr/bin/env python3
"""Deployment guard for CalcPulse.

Two jobs, both cheap and both run before a build is published:

1.  Forbidden-topic filter. The publishing pipeline generates pages from feeds and
    an LLM, so a single bad generation could ship a page about a topic this site
    must never touch (defence, procurement, weapon systems, or anything that reads
    as advice on evading a platform's rules). The list is fixed in code so the
    filter cannot drift with a prompt.

2.  Structural checks that catch a silent build failure: an empty page, a missing
    canonical, a missing sitemap entry, or a calculator that rendered without its
    result elements.

Usage:  python3 scripts/forbidden_terms.py dist
Exit code 0 = clean, 1 = at least one violation (build must not be published).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Lower-cased substrings. Matched against the visible text of every built page.
FORBIDDEN_TERMS: tuple[str, ...] = (
    "defen" + "se contract",
    "defen" + "se industry",
    "wea" + "pons system",
    "mili" + "tary procurement",
    "arms " + "deal",
    "국" + "방",
    "군" + "수",
    "방" + "산",
    "조" + "달청",
    "병" + "역",
    # Gambling, adult content and outright illegality: not the site's subject and not something
    # the daily generator may drift into when a source story is spicy.
    "도" + "박",
    "카" + "지노",
    "음" + "란",
    "성인" + " 콘텐츠",
    "포" + "르노",
    "불법" + " 도박",
    "자금" + "세탁",
    "gambling",
    "casino",
    "sports betting",
    "pornograph",
    "adult content",
    "money laundering",
)

# Pages that must exist after a build, with the marker text they must contain.
REQUIRED_PAGES: tuple[tuple[str, str], ...] = (
    ("index.html", "Decisions that hinge on a number"),
    ("guides/index.html", "Long-form workings"),
    ("guides/ai-api-cost-calculator/index.html", "LLM API cost calculator"),
    ("guides/saas-break-even-calculator/index.html", "SaaS break-even calculator"),
    ("guides/payment-fee-calculator/index.html", "Payment fee calculator"),
    ("vault/index.html", "Ten prompts that hold their shape"),
    ("datasets/index.html", "Open data, cleaned weekly"),
    ("about/index.html", "About CalcPulse"),
    ("privacy/index.html", "Calculator inputs"),
    ("affiliate-disclosure/index.html", "Affiliate disclosure"),
    ("llms.txt", "CalcPulse"),
    ("sitemap.xml", "/guides/ai-api-cost-calculator/"),
    ("robots.txt", "Sitemap:"),
)

# Strings that must never appear.
#   - ad network tags: the site's decision is zero-cost, affiliate and Gumroad only,
#     so an ad tag reaching production is a regression, not a feature;
#   - a checkout or password field on our own domain: payment stays on Gumroad;
#   - an unset placeholder that would ship as a dead link.
HARD_BANS: tuple[str, ...] = (
    "adsbygoogle",
    "pagead2.googlesyndication",
    "googlesyndication",
    "ca-pub-",
    "YOUR-DOMAIN",
    'href=""',
    'href="#"',
    "TODO(",
    "<input type=\"password\"",
    # The publisher's legal name is never published: the site, the products and
    # their metadata speak as CalcPulse / CalcPulse Editorial Team only.
    "김호빈",
    "hobeen",
)

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.S | re.I)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def visible_text(html: str) -> str:
    text = SCRIPT_RE.sub(" ", html)
    text = STYLE_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).lower()


def main() -> int:
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    if not dist.is_dir():
        print(f"FAIL: build output not found at {dist}")
        return 1

    problems: list[str] = []

    for relative, marker in REQUIRED_PAGES:
        path = dist / relative
        if not path.is_file():
            problems.append(f"missing page: {relative}")
            continue
        body = path.read_text(encoding="utf-8", errors="ignore")
        if marker.lower() not in body.lower():
            problems.append(f"{relative}: marker not found ({marker!r})")

    pages = sorted(dist.rglob("*.html"))
    if not pages:
        problems.append("no HTML pages were built")

    for page in pages:
        html = page.read_text(encoding="utf-8", errors="ignore")
        rel = page.relative_to(dist)

        if 'rel="canonical"' not in html:
            problems.append(f"{rel}: no canonical link")

        text = visible_text(html)
        for term in FORBIDDEN_TERMS:
            if term in text:
                problems.append(f"{rel}: forbidden topic term {term!r}")

        # Comments are stripped first: the template keeps an inert AdSense snippet for
        # the day the account is approved, and an inert placeholder must not fail a build.
        lowered = COMMENT_RE.sub(" ", html).lower()
        for banned in HARD_BANS:
            if banned.lower() in lowered:
                problems.append(f"{rel}: banned string {banned!r}")

        if 'id="api-cost-form"' in html:
            for element in ("out-total", "out-per-req"):
                if element not in html:
                    problems.append(f"{rel}: calculator result element {element!r} missing")
        if 'id="roi-form"' in html:
            for element in ("out-payback", "out-roi"):
                if element not in html:
                    problems.append(f"{rel}: calculator result element {element!r} missing")

    print(f"checked {len(pages)} pages in {dist}")
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("PASS: no forbidden topics, all required pages present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
