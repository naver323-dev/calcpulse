#!/usr/bin/env python3
"""CalcPulse daily guide pipeline: collect -> generate -> validate -> gate -> commit.

One run publishes at most one guide. The order is deliberate:

  1. scripts/collect_topic.py picks a topic from free public sources (Hacker News,
     GitHub, Google Trends) and drops anything CalcPulse has already published.
  2. A free LLM writes the guide as JSON: Gemini first, then Groq, then OpenRouter
     (scripts/llm_fallback.py). One tier running out of quota is no longer a lost day.
  3. The draft is validated against the editorial rules *and* the same forbidden-topic
     list the deployment guard uses (scripts/forbidden_terms.py), so a bad topic is
     refused before a file exists — and again by `npm test` before anything is pushed.
  4. The page is rendered into the real site structure: a guide entry in
     src/data/guides.ts plus src/pages/guides/<slug>.astro, which renders the
     calculator component for its topic. sitemap.xml, llms.txt and the guide index
     pick the new entry up at build time.
  5. `npm test` (build + arithmetic + DOM + guard) has to pass. If it does not, the
     generated files are reverted and nothing is committed.
  6. With --publish the page and the state file are committed and pushed to main.

Free-tier protection: a 429/quota answer is not a failure, it is "skip today" with exit 0.
The daily cap and the one-per-run limit live here, not in the workflow.

Usage
    python3 scripts/generate_guide.py                 # collect + generate, leave files (no commit)
    python3 scripts/generate_guide.py --publish       # ... and commit + push when the gate passes
    python3 scripts/generate_guide.py --dry-run       # fixture draft, full gate, then revert
    python3 scripts/generate_guide.py --self-test     # validator must accept the fixture, reject bad
    python3 scripts/generate_guide.py --collect-only  # just print today's topic

Environment
    GEMINI_API_KEY      free tier, first choice (unless --dry-run / --self-test / --collect-only)
    GEMINI_MODEL        optional, comma separated model list for that tier
    GROQ_API_KEY        free tier, second choice; skipped when unset
    GROQ_MODEL          optional, comma separated model list
    OPENROUTER_API_KEY  third choice, ":free" models (no card); skipped when unset
    OPENROUTER_MODEL    optional, comma separated model list

Any one of the three keys is enough to generate; the chain uses whatever is present.

Exit codes: 0 published / skipped today / nothing to do, 2 nothing to collect,
3 API or key problem, 4 validation or build gate failed, 5 git problem.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
GUIDES_TS = ROOT / "src" / "data" / "guides.ts"
GUIDES_DIR = ROOT / "src" / "pages" / "guides"
FIXTURE_DIR = SCRIPTS / "fixtures"
STATE_PATH = SCRIPTS / "pipeline_state.json"
QUEUE_DIR = ROOT / "content_queue"

sys.path.insert(0, str(SCRIPTS))
import content_queue  # noqa: E402  (queue-first publishing: content_queue/*.json)
from forbidden_terms import FORBIDDEN_TERMS  # noqa: E402  (same list the build guard uses)
import collect_topic  # noqa: E402
import llm_fallback  # noqa: E402  (Gemini -> Groq -> GitHub Models, all free tiers)

SITE_ORIGIN = "https://calcpulse.pages.dev"
STACKVERDICT_URL = "https://stackverdict-8jj.pages.dev"
KST = timezone(timedelta(hours=9))

API_BASE = llm_fallback.GEMINI_BASE
# Same free-tier pattern as the sister site: Flash drafts, Flash-Lite is the fallback with
# far more free headroom. No Search grounding — it has no free quota and burns retries.
DEFAULT_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
PROVIDER_ORDER = llm_fallback.DEFAULT_PROVIDERS
GENERATION_ATTEMPTS = 2
MAX_PER_RUN = 1

# topic family -> (component, calculator label for the registry, anchor guide for links)
FAMILY_CALCULATOR: dict[str, tuple[str, str, str]] = {
    "AI cost": ("LlmApiCostCalculator", "LLM API cost calculator", "ai-api-cost-calculator"),
    "SaaS & tooling": (
        "SaasRoiCalculator",
        "SaaS break-even and ROI calculator",
        "saas-break-even-calculator",
    ),
    "Small-business finance": (
        "PaymentFeeCalculator",
        "Payment fee calculator",
        "payment-fee-calculator",
    ),
}

EDITORIAL_BANS = (
    "putin",
    "invasion",
    "election",
    "president",
    "ceasefire",
    "war in",
    "genocide",
    "abortion",
    "vaccine",
    "cancer",
    "therapy",
    "depression",
)
# Not a topic filter: a reminder that guides are about budgets, not about people.
PERSONAL_NAME_BANS = ("김호빈", "kim hobeen", "hobin")
PLACEHOLDER_BANS = ("todo", "lorem", "placeholder text", "as an ai", "insert ", "xxx")

WORD_RANGE = (780, 1700)


class QuotaError(RuntimeError):
    """The free tier said no. Not a failure: nobody publishes today."""


class ApiError(RuntimeError):
    """The API answered with something we cannot use."""


class ValidationError(RuntimeError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


# --------------------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------------------
def read_state() -> dict:
    if not STATE_PATH.is_file():
        return {"published": [], "skips": [], "runs": []}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        state = {}
    for key in ("published", "skips", "runs"):
        state.setdefault(key, [])
    return state


def write_state(state: dict) -> None:
    state["runs"] = state["runs"][-60:]
    state["skips"] = state["skips"][-60:]
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def today_kst() -> str:
    return datetime.now(KST).date().isoformat()


def published_today(state: dict) -> bool:
    return any(item.get("date") == today_kst() for item in state.get("published", []))


# --------------------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the editor of CalcPulse, a small site of practical guides about what AI, software
and payment tooling actually cost. The reader is a founder, operator or developer paying from their own
budget; they want the arithmetic and the decision it supports, not encouragement.

Voice
- Plain English, concrete, unhedged. Short paragraphs, two to four sentences.
- Specific mechanisms ("the fixed fee is charged per charge, so a $10 sale loses 5.9%").
- No hype adjectives, no "in today's fast-paced world", no rhetorical questions as headings, no emojis,
  no listicle padding, no exclamation marks, no second-person cheerleading.
- British or American spelling, consistently; use typographic apostrophes is NOT required.

What you must not do
- Do not state current prices, vendor plans, market sizes, funding rounds or statistics about third
  parties as fact. Write about the reader's own inputs ("the rate you enter") and label any illustrative
  figure as a hypothetical example.
- Do not invent studies, surveys, quotes, people, companies, products or links.
- Do not include any URL, markdown, HTML, footnotes, citations or code fences. The site adds its own
  navigation and links.
- Never write about weapons, defence procurement, military service, gambling, adult content, illegal
  activity, evading a platform's fees or rules, tax evasion, politics, or personal medical, legal or
  investment advice. If the topic points that way, write about the boring budget question instead.
- No mention of any individual author's name. The byline is the brand.

Output: one JSON object, no surrounding text, exactly this shape
{
  "slug": "kebab-case, 3-6 words, no year",
  "title": "under 60 characters, no trailing period",
  "h1": "the page headline, sentence case",
  "description": "one sentence under 155 characters for the meta description",
  "summary": "one sentence, under 200 characters, reused by llms.txt",
  "keywords": ["3 to 4 short search phrases"],
  "lede": "one paragraph of 45-75 words that states the argument, not the topic",
  "sections": [
    {"heading": "short noun-phrase heading", "paragraphs": ["70-110 words", "70-110 words"]}
  ],
  "checklist": ["4 to 6 items, each one concrete action with a number or a threshold"],
  "faq": [{"q": "question a reader would ask", "a": "40-90 words, direct answer"}],
  "minutes": 6
}
Five sections. Total body 1000-1400 words. The FAQ has four entries."""


def build_user_prompt(topic: dict, existing: list[dict], date: str) -> str:
    already = "; ".join(
        f"{guide['slug']} ({guide['h1']})" for guide in existing if guide.get("slug")
    )
    return json.dumps(
        {
            "date": date,
            "topic_family": topic["family"],
            "prompting_story": {
                "headline": topic["source_title"],
                "source": topic["source"],
                "url": topic["source_url"],
                "note": "A story that suggests the reader is already thinking about this. Do not "
                "write about the story itself, do not name the company or product, and do not "
                "repeat its claims. Use it only as the reason this question is live this week.",
            },
            "already_published_slugs": already,
            "task": "Write one new guide for this topic family that the site does not already cover. "
            "Different angle, different arithmetic from the guides listed above.",
        },
        ensure_ascii=False,
        indent=2,
    )


def call_with_fallback(
    system: str,
    user: str,
    models: list[str],
    log=print,
    transport=None,
) -> tuple[dict, str]:
    """Gemini -> Groq -> GitHub Models, every tier free.

    A quota answer on one tier moves to the next instead of ending the day. Only when
    every reachable tier is out does this surface QuotaError (skip today, exit 0); a
    broken key or an unreachable service surfaces ApiError (exit 3) so it gets noticed.
    """
    env = dict(os.environ)
    if models:
        env["GEMINI_MODEL"] = ",".join(models)
    kwargs = {"log": log, "temperature": 0.7, "max_tokens": 8192, "providers": PROVIDER_ORDER, "env": env}
    if transport is not None:
        kwargs["transport"] = transport
        kwargs["sleep"] = lambda _seconds: None
    try:
        return llm_fallback.chat_json(system, user, **kwargs)
    except llm_fallback.QuotaExhausted as exc:
        raise QuotaError(str(exc)) from exc
    except llm_fallback.ChainFailed as exc:
        raise ApiError(str(exc)) from exc


# --------------------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------------------
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BANNED_CHARS = set("<>{}\\`[]*_#|")
URL_RE = re.compile(r"(https?://|www\.)", re.I)


def _strings(draft: dict) -> list[tuple[str, str]]:
    """Every user-visible string in the draft, with a label for the error message."""
    items: list[tuple[str, str]] = []

    def add(label: str, value) -> None:
        if isinstance(value, str):
            items.append((label, value))

    for key in ("title", "h1", "description", "summary", "lede"):
        add(key, draft.get(key))
    for index, section in enumerate(draft.get("sections") or []):
        add(f"sections[{index}].heading", section.get("heading"))
        for p_index, paragraph in enumerate(section.get("paragraphs") or []):
            add(f"sections[{index}].paragraphs[{p_index}]", paragraph)
    for index, item in enumerate(draft.get("checklist") or []):
        add(f"checklist[{index}]", item)
    for index, entry in enumerate(draft.get("faq") or []):
        add(f"faq[{index}].q", entry.get("q"))
        add(f"faq[{index}].a", entry.get("a"))
    for index, keyword in enumerate(draft.get("keywords") or []):
        add(f"keywords[{index}]", keyword)
    return items


def _words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9$%'’-]+", text))


def forbidden_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits = [term for term in FORBIDDEN_TERMS if term in lowered]
    hits += [term for term in EDITORIAL_BANS if term in lowered]
    hits += [term for term in PERSONAL_NAME_BANS if term in lowered]
    hits += [term for term in PLACEHOLDER_BANS if term in lowered]
    return sorted(set(hits))


def validate_draft(draft: dict, existing_slugs: set[str]) -> list[str]:
    """The editorial contract, checked without the model in the loop."""
    problems: list[str] = []
    if not isinstance(draft, dict):
        return ["draft is not a JSON object"]

    slug = str(draft.get("slug") or "").strip()
    if not SLUG_RE.match(slug) or not 8 <= len(slug) <= 60:
        problems.append(f"slug {slug!r} is not kebab-case between 8 and 60 characters")
    if slug in existing_slugs:
        problems.append(f"slug {slug!r} is already published")

    topic = draft.get("topic")
    if topic not in FAMILY_CALCULATOR:
        problems.append(f"topic {topic!r} is not one of {sorted(FAMILY_CALCULATOR)}")

    title = str(draft.get("title") or "")
    if not 20 <= len(title) <= 65:
        problems.append("title must be 20-65 characters")
    h1 = str(draft.get("h1") or "")
    if not 20 <= len(h1) <= 90:
        problems.append("h1 must be 20-90 characters")
    description = str(draft.get("description") or "")
    if not 60 <= len(description) <= 160:
        problems.append("description must be 60-160 characters")
    if description and not description.endswith((".", "?", "!")):
        problems.append("description must be one complete sentence")
    summary = str(draft.get("summary") or "")
    if not 60 <= len(summary) <= 220:
        problems.append("summary must be 60-220 characters")

    keywords = draft.get("keywords")
    if not isinstance(keywords, list) or not 3 <= len(keywords) <= 5:
        problems.append("keywords must be a list of 3-5 phrases")
    else:
        for keyword in keywords:
            if not isinstance(keyword, str) or not 3 <= len(keyword) <= 60:
                problems.append(f"keyword {keyword!r} is unusable")

    sections = draft.get("sections")
    if not isinstance(sections, list) or not 4 <= len(sections) <= 8:
        problems.append("sections must be a list of 4-8 entries")
        sections = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            problems.append(f"sections[{index}] is not an object")
            continue
        heading = str(section.get("heading") or "")
        if not 8 <= len(heading) <= 90:
            problems.append(f"sections[{index}].heading must be 8-90 characters")
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list) or not 1 <= len(paragraphs) <= 4:
            problems.append(f"sections[{index}].paragraphs must be 1-4 paragraphs")
            continue
        for p_index, paragraph in enumerate(paragraphs):
            words = _words(str(paragraph))
            if not 35 <= words <= 190:
                problems.append(
                    f"sections[{index}].paragraphs[{p_index}] is {words} words (35-190 allowed)"
                )

    body = " ".join(
        " ".join(str(p) for p in section.get("paragraphs") or [])
        for section in sections
        if isinstance(section, dict)
    )
    full_words = _words(str(draft.get("lede") or "")) + _words(body)
    if not WORD_RANGE[0] <= full_words <= WORD_RANGE[1]:
        problems.append(f"body is {full_words} words ({WORD_RANGE[0]}-{WORD_RANGE[1]} allowed)")

    minutes = draft.get("minutes")
    if not isinstance(minutes, int) or not 4 <= minutes <= 14:
        problems.append("minutes must be an integer between 4 and 14")
    else:
        expected = max(4, round(full_words / 210))
        if abs(minutes - expected) > 2:
            problems.append(f"minutes {minutes} does not match a {full_words}-word body")

    checklist = draft.get("checklist")
    if not isinstance(checklist, list) or not 3 <= len(checklist) <= 7:
        problems.append("checklist must be a list of 3-7 items")
    else:
        for index, item in enumerate(checklist):
            if not isinstance(item, str) or not 8 <= len(item) <= 220:
                problems.append(f"checklist[{index}] must be 8-220 characters")

    faq = draft.get("faq")
    if not isinstance(faq, list) or not 3 <= len(faq) <= 5:
        problems.append("faq must be a list of 3-5 entries")
    else:
        for index, entry in enumerate(faq):
            if not isinstance(entry, dict):
                problems.append(f"faq[{index}] is not an object")
                continue
            question = str(entry.get("q") or "")
            answer = str(entry.get("a") or "")
            if not 12 <= len(question) <= 130:
                problems.append(f"faq[{index}].q must be 12-130 characters")
            if not 40 <= _words(answer) <= 130:
                problems.append(f"faq[{index}].a must be 40-130 words")

    for label, text in _strings(draft):
        if not text.strip():
            problems.append(f"{label} is empty")
            continue
        hits = forbidden_hits(text)
        if hits:
            problems.append(f"{label} contains a banned term: {hits[0]!r}")
        if URL_RE.search(text):
            problems.append(f"{label} contains a link; the page adds its own")
        bad = sorted({char for char in text if char in BANNED_CHARS})
        if bad:
            problems.append(f"{label} contains characters Astro or the guard would misread: {bad}")
        if "  " in text:
            problems.append(f"{label} has a double space")
        if text.strip() != text:
            problems.append(f"{label} has leading or trailing whitespace")

    return problems


def normalize_draft(draft: dict, topic_family: str) -> dict:
    """Small, mechanical fixes before validation: whitespace, a trailing period, the topic."""
    if not isinstance(draft, dict):
        return draft

    def clean(value):
        if isinstance(value, str):
            value = re.sub(r"\s+", " ", value).strip()
            return value.replace("‘", "’").replace("“", "”")
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        return value

    draft = clean(draft)
    draft["topic"] = topic_family
    title = str(draft.get("title") or "")
    draft["title"] = title.rstrip(".")
    if isinstance(draft.get("keywords"), list):
        draft["keywords"] = [str(keyword).lower() for keyword in draft["keywords"]]
    if isinstance(draft.get("minutes"), float):
        draft["minutes"] = int(draft["minutes"])
    return draft


# --------------------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------------------
def esc(text: str) -> str:
    return html.escape(text, quote=False)


def render_sections(sections: list[dict]) -> str:
    blocks = []
    for section in sections:
        paragraphs = "\n".join(f"        <p>{esc(p)}</p>" for p in section["paragraphs"])
        blocks.append(
            f"        <h2>{esc(section['heading'])}</h2>\n{paragraphs}"
        )
    return "\n\n".join(blocks)


def render_page(draft: dict, topic: dict, date: str) -> str:
    family = draft["topic"]
    component, _, anchor_slug = FAMILY_CALCULATOR[family]
    sections = draft["sections"]
    split = 2 if len(sections) > 3 else 1
    before, after = sections[:split], sections[split:]

    faq_js = ",\n".join(
        "  {\n    q: " + json.dumps(entry["q"], ensure_ascii=False) +
        ",\n    a: " + json.dumps(entry["a"], ensure_ascii=False) + ",\n  }"
        for entry in draft["faq"]
    )
    checklist = "\n".join(f"          <li>{esc(item)}</li>" for item in draft["checklist"])
    others = [
        (label, slug, h1) for other_family, (_, label, slug) in FAMILY_CALCULATOR.items()
        if other_family != family
        for h1 in [guide_h1(slug)]
    ]
    other_links = "\n".join(
        f'        <li class="mt-2">\n'
        f'          <a href="/guides/{slug}/" class="font-medium text-ink-950 hover:text-pulse-700">{esc(label)}</a>'
        f'<span class="text-ink-600"> — {esc(h1)}</span>\n'
        f"        </li>"
        for label, slug, h1 in others
    )
    minutes = int(draft.get("minutes") or 6)

    return f"""---
import BaseLayout from '../../layouts/BaseLayout.astro';
import {{ guideBySlug }} from '../../data/guides';
import OfferSlot from '../../components/OfferSlot.astro';
import {component} from '../../components/{component}.astro';

const guide = guideBySlug('{draft['slug']}');

const faq = [
{faq_js},
];

const jsonLd = {{
  '@context': 'https://schema.org',
  '@graph': [
    {{
      '@type': 'Article',
      headline: guide.h1,
      description: guide.description,
      datePublished: '{date}',
      dateModified: guide.updated,
      inLanguage: 'en',
      author: {{ '@type': 'Organization', name: 'CalcPulse Editorial Team' }},
      publisher: {{ '@type': 'Organization', name: 'CalcPulse' }},
      mainEntityOfPage: `https://calcpulse.pages.dev/guides/${{guide.slug}}/`,
    }},
    {{
      '@type': 'FAQPage',
      mainEntity: faq.map((item) => ({{
        '@type': 'Question',
        name: item.q,
        acceptedAnswer: {{ '@type': 'Answer', text: item.a }},
      }})),
    }},
  ],
}};
---

<BaseLayout title={{guide.title}} description={{guide.description}} jsonLd={{jsonLd}} updated={{guide.updated}}>
  <div class="mx-auto max-w-5xl px-4 sm:px-6 py-12">
    <nav class="text-sm text-ink-400" aria-label="Breadcrumb">
      <a href="/" class="hover:text-ink-600">Home</a> <span aria-hidden="true">/</span>
      <a href="/guides/" class="hover:text-ink-600">Guides</a> <span aria-hidden="true">/</span>
      {esc(family)}
    </nav>

    <article class="mt-4">
      <header class="max-w-3xl">
        <p class="text-xs font-semibold uppercase tracking-[0.14em] text-pulse-600">{esc(family)}</p>
        <h1 class="mt-2 text-3xl sm:text-4xl font-semibold tracking-tight text-ink-950 leading-tight">
          {esc(draft['h1'])}
        </h1>
        <p class="mt-4 text-lg text-ink-600 leading-relaxed">
          {esc(draft['lede'])}
        </p>
        <p class="mt-4 text-sm text-ink-400">
          Reviewed {date} · {minutes} min read · by CalcPulse Editorial Team · calculator runs in your browser
        </p>
      </header>

      <div class="prose prose-ink mt-10 max-w-3xl">
{render_sections(before)}
      </div>

      <{component} />

      <div class="prose prose-ink mt-10 max-w-3xl">
{render_sections(after)}

        <h2>What to check this week</h2>
        <ul>
{checklist}
        </ul>
      </div>

      <section class="mt-12 max-w-3xl">
        <h2 class="text-xl font-semibold text-ink-950">Questions this guide gets</h2>
        <dl class="mt-4 divide-y divide-ink-200 border-y border-ink-200">
          {{
            faq.map((item) => (
              <div class="py-4">
                <dt class="font-medium text-ink-950">{{item.q}}</dt>
                <dd class="mt-1.5 text-sm leading-relaxed text-ink-600">{{item.a}}</dd>
              </div>
            ))
          }}
        </dl>
      </section>

      <aside class="mt-12 max-w-3xl rounded-xl border border-ink-200 bg-white p-5">
        <p class="text-xs font-semibold uppercase tracking-wider text-ink-400">Run the numbers</p>
        <p class="mt-1 font-semibold text-ink-950">The {esc(FAMILY_CALCULATOR[family][1])} is on this page</p>
        <p class="mt-1 text-sm text-ink-600">
          The same arithmetic drives the rest of the site. If this guide was the closest one to your
          question, one of these is usually the next:
        </p>
        <ul class="mt-3 text-sm">
{other_links}
        </ul>
      </aside>

      <aside class="mt-6 max-w-3xl rounded-xl border border-ink-200 bg-white p-5">
        <p class="text-xs font-semibold uppercase tracking-wider text-ink-400">Paid tools</p>
        <a href="{STACKVERDICT_URL}" rel="noopener" class="mt-1 block font-semibold text-ink-950 hover:text-pulse-700">
          StackVerdict reviews the tools you would be paying for →
        </a>
        <p class="mt-1 text-sm text-ink-600">
          The sibling site writes long, hands-on reviews of paid software. Read one before you put a
          subscription on the same spreadsheet as the numbers above.
        </p>
      </aside>

      <section class="mt-10 max-w-3xl text-sm text-ink-500">
        <h2 class="text-xs font-semibold uppercase tracking-wider text-ink-400">Prompted by</h2>
        <p class="mt-2">
          <a href="{topic['source_url'].replace('"', '%22')}" rel="noopener" class="underline decoration-ink-300 hover:text-ink-700">
            {esc(topic['source_title'])}
          </a>
          ({esc(topic['source'])}, {topic.get('points', 0)} points). The link is the discussion that
          prompted this guide, not a source for its figures: every number on the page is an input you
          set yourself.
        </p>
      </section>

      <OfferSlot class="mt-4 max-w-3xl" />
    </article>
  </div>
</BaseLayout>
"""


def guide_h1(slug: str) -> str:
    for guide in collect_topic.published_guides():
        if guide["slug"] == slug:
            return guide["h1"]
    return ""


# --------------------------------------------------------------------------------------
# registry + build gate + git
# --------------------------------------------------------------------------------------
def registry_entry(draft: dict, date: str) -> str:
    _, calculator, _ = FAMILY_CALCULATOR[draft["topic"]]
    keywords = ", ".join(json.dumps(keyword, ensure_ascii=False) for keyword in draft["keywords"])
    return (
        "  {\n"
        f"    slug: {json.dumps(draft['slug'])},\n"
        f"    title: {json.dumps(draft['title'], ensure_ascii=False)},\n"
        f"    h1: {json.dumps(draft['h1'], ensure_ascii=False)},\n"
        f"    description:\n      {json.dumps(draft['description'], ensure_ascii=False)},\n"
        f"    summary:\n      {json.dumps(draft['summary'], ensure_ascii=False)},\n"
        f"    calculator: {json.dumps(calculator)},\n"
        f"    updated: '{date}',\n"
        f"    minutes: {int(draft['minutes'])},\n"
        f"    keywords: [{keywords}],\n"
        f"    topic: {json.dumps(draft['topic'])},\n"
        "  },\n"
    )


def write_files(draft: dict, topic: dict, date: str) -> tuple[Path, str]:
    """Write the page and the registry entry; return (page path, original registry text)."""
    original = GUIDES_TS.read_text(encoding="utf-8")
    page_path = GUIDES_DIR / f"{draft['slug']}.astro"
    page_path.write_text(render_page(draft, topic, date), encoding="utf-8")

    anchor = original.rstrip().rfind("];")
    if anchor == -1:
        raise ValidationError(["src/data/guides.ts has no closing '];'"])
    updated = original[:anchor] + registry_entry(draft, date) + original[anchor:]
    GUIDES_TS.write_text(updated, encoding="utf-8")
    return page_path, original


def revert_files(page_path: Path, original_registry: str) -> None:
    if page_path.exists():
        page_path.unlink()
    GUIDES_TS.write_text(original_registry, encoding="utf-8")


def node_env() -> dict:
    env = dict(os.environ)
    local_bin = Path("/workspace/.local/node/bin")
    if local_bin.is_dir():
        env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    return env


def run_npm_test(log=print) -> tuple[bool, str]:
    log("  · running npm test (build + arithmetic + DOM + guard)")
    result = subprocess.run(
        ["npm", "test"],
        cwd=ROOT,
        env=node_env(),
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output


def git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=check
    )


def commit_and_push(draft: dict, page_path: Path, log=print, from_queue: str = "") -> None:
    relative = page_path.relative_to(ROOT)
    git(["config", "user.name", "calcpulse-pipeline"])
    git(["config", "user.email", "calcpulse-pipeline@users.noreply.github.com"])
    # content_queue is staged too: a guide published from the queue leaves the queue in this
    # same commit, and a rejected item moves to content_queue/rejected/.
    git(["add", "--", str(relative), "src/data/guides.ts", "scripts/pipeline_state.json", "content_queue"])
    origin = f"\n\nFrom content_queue item {from_queue}." if from_queue else ""
    message = f"content: {draft['title']}\n\nGenerated by scripts/generate_guide.py; passed npm test.{origin}"
    git(["commit", "-m", message])
    log(f"  · committed {relative}")

    for attempt in range(2):
        pushed = git(["push", "origin", "HEAD:main"], check=False)
        if pushed.returncode == 0:
            log("  · pushed to origin/main")
            return
        log(f"  ! push failed: {pushed.stderr.strip()[:300]}")
        if attempt == 0:
            rebase = git(["pull", "--rebase", "--autostash", "origin", "main"], check=False)
            if rebase.returncode != 0:
                git(["rebase", "--abort"], check=False)
                raise RuntimeError(f"could not rebase onto origin/main: {rebase.stderr[:300]}")
    raise RuntimeError("push failed twice")


# --------------------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------------------
def log(message: str) -> None:
    print(message, file=sys.stderr)


def generate_draft(
    topic: dict,
    existing: list[dict],
    models: list[str],
    transport=None,
) -> tuple[dict, str]:
    slugs = {guide["slug"] for guide in existing if guide.get("slug")}
    user = build_user_prompt(topic, existing, today_kst())
    draft, model = call_with_fallback(SYSTEM_PROMPT, user, models, log, transport=transport)
    draft = normalize_draft(draft, topic["family"])
    problems = validate_draft(draft, slugs)

    for _ in range(GENERATION_ATTEMPTS - 1):
        if not problems:
            break
        log(f"  ! draft failed {len(problems)} check(s); asking for one repair")
        for problem in problems[:12]:
            log(f"    - {problem}")
        repair = (
            f"{user}\n\nYour previous answer failed these checks:\n"
            + "\n".join(f"- {problem}" for problem in problems)
            + "\n\nReturn the complete corrected JSON object only, with the same shape."
        )
        draft, model = call_with_fallback(SYSTEM_PROMPT, repair, models, log, transport=transport)
        draft = normalize_draft(draft, topic["family"])
        problems = validate_draft(draft, slugs)

    if problems:
        raise ValidationError(problems)
    return draft, model


def self_test() -> int:
    fixture_path = FIXTURE_DIR / "guide_fixture.json"
    draft = json.loads(fixture_path.read_text(encoding="utf-8"))
    base = normalize_draft(json.loads(json.dumps(draft)), draft["topic"])
    existing = {"ai-api-cost-calculator", "saas-break-even-calculator", "payment-fee-calculator"}

    failures = 0
    problems = validate_draft(base, existing)
    if problems:
        failures += 1
        print("FAIL: the good fixture was rejected:")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("ok  good fixture accepted")

    def mutate(label: str, change, expect: str) -> None:
        nonlocal failures
        candidate = json.loads(json.dumps(base))
        change(candidate)
        found = validate_draft(candidate, existing)
        if not found:
            failures += 1
            print(f"FAIL: accepted: {label}")
        elif expect not in " ".join(found):
            failures += 1
            print(f"FAIL: rejected for the wrong reason: {label} -> {found[:2]}")
        else:
            print(f"ok  rejected: {label}")

    filler = (
        "This paragraph exists to keep the body long enough that the length rule cannot be the "
        "reason a candidate is refused, so each mutation below has to be caught by the rule it "
        "targets rather than by an accident of size in a list of paragraphs."
    )

    def add_paragraph(text: str):
        def change(candidate: dict) -> None:
            candidate["sections"][0]["paragraphs"].append(f"{filler} {text}")
        return change

    mutate("banned topic word", add_paragraph("It also covers casino loyalty schemes."), "banned term")
    mutate("defence term", add_paragraph("Ask the 국방 procurement office."), "banned term")
    mutate("an invented link", add_paragraph("See https://example.com/pricing."), "contains a link")
    mutate("Astro-breaking brace", add_paragraph("Enter {requests} per day."), "misread")
    mutate("markdown emphasis", add_paragraph("This is *important* to note."), "misread")
    mutate("a body far too short", lambda candidate: candidate.update(sections=candidate["sections"][:2]), "sections must be")
    mutate("a duplicate slug", lambda candidate: candidate.update(slug="saas-break-even-calculator"), "already published")
    mutate("a bad slug", lambda candidate: candidate.update(slug="Daily Guide 2026!"), "kebab-case")
    mutate("no FAQ", lambda candidate: candidate.update(faq=[]), "faq must be")
    mutate("the author's name", add_paragraph("A note from Kim Hobeen."), "banned term")
    mutate("a one-word title", lambda candidate: candidate.update(title="Cache"), "title must be")
    mutate("an unknown topic", lambda candidate: candidate.update(topic="Politics"), "not one of")

    print("self-test passed" if not failures else f"self-test FAILED with {failures} problem(s)")
    return 0 if not failures else 1


def pick_from_queue(day, log=log) -> tuple[dict, dict, content_queue.Item] | None:
    """First queued guide that is due today, already normalised and validated.

    The validator is the same one a generated draft goes through, so a queued guide cannot
    be held to a looser standard. A guide that fails it is rejected into
    content_queue/rejected/ with the reasons and the next item is tried in the same run.
    """
    existing = collect_topic.published_guides()
    slugs = {guide["slug"] for guide in existing if guide.get("slug")}
    while True:
        item = content_queue.take(QUEUE_DIR, day=day, is_published=lambda slug: slug in slugs, log=log)
        if item is None:
            return None
        draft = normalize_draft(item.draft, item.topic["family"])
        problems = validate_draft(draft, slugs)
        if problems:
            for problem in problems[:12]:
                log(f"  ! {problem}")
            content_queue.reject(QUEUE_DIR, item, problems, log=log)
            continue
        return draft, item.topic, item


def validate_queue(day, log=log) -> int:
    """Editorial + schema check for every queued guide, without writing or publishing."""
    items = content_queue.load(QUEUE_DIR, log=log)
    if not items:
        log(f"queue {QUEUE_DIR}: empty")
        return 0
    slugs = {guide["slug"] for guide in collect_topic.published_guides() if guide.get("slug")}
    failures = 0
    for item in items:
        problems = list(item.problems)
        if not problems and item.topic and item.draft:
            draft = normalize_draft(item.draft, item.topic["family"])
            problems.extend(validate_draft(draft, slugs))
        log(f"{'ok' if not problems else 'FAIL':4} {item.id:<31} {item.publish_after or '-':<12} {item.slug or '?'}")
        for problem in problems[:10]:
            log(f"      ! {problem}")
            failures += 1
    log("")
    log(f"{len(items)} item(s) checked, {failures} problem(s)")
    return 0 if failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate today's CalcPulse guide.")
    parser.add_argument("--publish", action="store_true", help="commit and push when the gate passes")
    parser.add_argument("--dry-run", action="store_true", help="fixture draft, full gate, then revert")
    parser.add_argument("--self-test", action="store_true", help="validator self-test, no API")
    parser.add_argument("--collect-only", action="store_true", help="print today's topic and stop")
    parser.add_argument("--force", action="store_true", help="ignore the one-guide-a-day cap")
    parser.add_argument("--date", help="YYYY-MM-DD override (defaults to today in KST)")
    parser.add_argument("--model", help="comma separated model list, overrides GEMINI_MODEL")
    parser.add_argument("--keep", action="store_true", help="with --dry-run, keep the generated files")
    parser.add_argument("--queue-dir", help="folder of approved guides (default content_queue/)")
    parser.add_argument("--no-queue", action="store_true", help="skip content_queue/ and run the live pipeline")
    parser.add_argument("--queue-list", action="store_true", help="show the queue and what is due today")
    parser.add_argument("--queue-validate", action="store_true", help="validate every queued item, publish nothing")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.dry_run and args.publish:
        print("--dry-run and --publish are mutually exclusive", file=sys.stderr)
        return 1

    date = args.date or today_kst()
    day = datetime.fromisoformat(date).date()
    state = read_state()
    global QUEUE_DIR
    if args.queue_dir:
        QUEUE_DIR = Path(args.queue_dir)
        if not QUEUE_DIR.is_absolute():
            QUEUE_DIR = ROOT / QUEUE_DIR

    if args.queue_list:
        print(content_queue.report(QUEUE_DIR, day=day))
        return 0
    if args.queue_validate:
        return validate_queue(day)

    if args.collect_only:
        topic = collect_topic.collect(day=datetime.fromisoformat(date).replace(tzinfo=timezone.utc))
        print(json.dumps(topic, ensure_ascii=False, indent=2) if topic else "no topic today")
        return 0 if topic else 2

    queued = None
    if not (args.dry_run or args.no_queue):
        queued = pick_from_queue(day)

    if published_today(state) and not args.force and not args.dry_run:
        log(f"skip today: a guide is already published for {today_kst()}")
        return 0

    existing = collect_topic.published_guides()
    model = ""
    queue_item = None
    if queued is not None:
        draft, topic, queue_item = queued
        model = f"queue:{queue_item.id}"
        log(f"  · content_queue: item {queue_item.id} ({topic.get('family')}) — no collect, no LLM call")
    elif args.dry_run:
        topic = collect_topic.collect(day=datetime.fromisoformat(date).replace(tzinfo=timezone.utc))
        draft = json.loads((FIXTURE_DIR / "guide_fixture.json").read_text(encoding="utf-8"))
        draft = normalize_draft(draft, topic["family"] if topic else draft.get("topic", "AI cost"))
        topic = topic or {
            "source": "Fixture",
            "source_title": "Fixture run: no live topic collected",
            "source_url": "https://news.ycombinator.com/",
            "points": 0,
            "family": draft["topic"],
        }
        if draft["topic"] != topic["family"]:
            draft["topic"] = topic["family"]
        model = "fixture"
    else:
        topic = collect_topic.collect(day=datetime.fromisoformat(date).replace(tzinfo=timezone.utc))
        if not topic:
            log("no topic today (sources returned nothing usable); nothing to publish")
            state["skips"].append({"date": date, "reason": "no topic"})
            write_state(state)
            return 0

        if not any(llm_fallback.provider_config(name) for name in PROVIDER_ORDER):
            print(
                "no LLM credential is set (GEMINI_API_KEY, GROQ_API_KEY or OPENROUTER_API_KEY); "
                "refusing to generate.",
                file=sys.stderr,
            )
            return 3
        models = [
            item.strip()
            for item in (args.model or os.environ.get("GEMINI_MODEL", "")).split(",")
            if item.strip()
        ] or DEFAULT_MODELS

        try:
            draft, model = generate_draft(topic, existing, models)
        except QuotaError as exc:
            log(f"skip today: free-tier quota ({exc})")
            state["skips"].append({"date": date, "reason": "quota", "detail": str(exc)[:200]})
            write_state(state)
            return 0
        except ValidationError as exc:
            log("skip today: the draft did not pass the editorial checks")
            for problem in exc.problems[:15]:
                log(f"  - {problem}")
            state["skips"].append({"date": date, "reason": "validation", "detail": exc.problems[:5]})
            write_state(state)
            return 0
        except ApiError as exc:
            print(f"generation failed: {exc}", file=sys.stderr)
            return 3

    page_path, original_registry = write_files(draft, topic, date)
    log(f"  · wrote {page_path.relative_to(ROOT)} and the registry entry")

    try:
        passed, output = run_npm_test(log)
    except FileNotFoundError as exc:
        revert_files(page_path, original_registry)
        print(f"npm is not available: {exc}", file=sys.stderr)
        return 4

    if not passed:
        revert_files(page_path, original_registry)
        print("FAIL: npm test did not pass; the generated page was reverted and nothing was committed")
        print("\n".join(output.strip().splitlines()[-40:]))
        return 4

    log("  · npm test passed (build, arithmetic, DOM, guard)")

    if args.dry_run:
        if args.keep:
            log("  · --keep: leaving the generated files in the working tree")
        else:
            revert_files(page_path, original_registry)
            log("  · reverted the dry-run files")
        state["runs"].append({"date": date, "mode": "dry-run", "slug": draft["slug"], "model": model})
        write_state(state)
        return 0

    if queue_item is not None:
        content_queue.retire(queue_item, log=log)

    state["runs"].append({"date": date, "mode": "generate", "slug": draft["slug"], "model": model})
    if args.publish:
        state["published"].append(
            {
                "date": date,
                "slug": draft["slug"],
                "title": draft["title"],
                "family": draft["topic"],
                "source": topic["source"],
                "source_url": topic["source_url"],
                "model": model,
                "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
    write_state(state)

    if args.publish:
        try:
            commit_and_push(
                draft,
                page_path,
                log,
                from_queue=f"{queue_item.id} ({queue_item.path.name})" if queue_item else "",
            )
        except (RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"git problem: {exc}", file=sys.stderr)
            return 5

    print(
        json.dumps(
            {
                "slug": draft["slug"],
                "title": draft["title"],
                "family": draft["topic"],
                "model": model,
                "published": bool(args.publish),
                "source": topic["source_url"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
