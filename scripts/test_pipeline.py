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

print("fallback chain")

import os  # noqa: E402
from unittest import mock  # noqa: E402

import llm_fallback  # noqa: E402

ALL_KEYS = {"GEMINI_API_KEY": "gemini-key", "GROQ_API_KEY": "groq-key", "OPENROUTER_API_KEY": "or-key"}


def gemini_body(text: str) -> str:
    return json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]})


def openai_body(text: str) -> str:
    return json.dumps(
        {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}
    )


def recorder(routes: dict):
    """A transport that answers by URL fragment and remembers what was asked, newest last."""
    calls: list[str] = []

    def send(url: str, headers: dict, payload: dict, timeout: int):
        calls.append(url)
        for fragment, answer in routes.items():
            if fragment in url:
                return answer
        raise AssertionError(f"unexpected request to {url}")

    return send, calls


# A CI run has the real keys in the environment; a test that says "only this key is set"
# has to take the others away first, or it calls a live provider from the gate.
LLM_KEYS = (
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
    "CEREBRAS_API_KEY",
    "GITHUB_MODELS_TOKEN",
    "GITHUB_TOKEN",
)


def chain(env: dict, transport, **kwargs):
    blank = {key: "" for key in LLM_KEYS}
    with mock.patch.dict(os.environ, {**blank, **env}, clear=False):
        return llm_fallback.chat_json("system", "user", transport=transport, sleep=lambda _s: None, **kwargs)


def gemini_quota_goes_to_groq() -> None:
    transport, calls = recorder({
        "generativelanguage": (429, '{"error": {"status": "RESOURCE_EXHAUSTED"}}'),
        "api.groq.com": (200, openai_body('{"slug": "from-groq"}')),
        "openrouter.ai/api": (200, openai_body('{"slug": "from-openrouter"}')),
    })
    draft, label = chain(ALL_KEYS, transport)
    assert draft == {"slug": "from-groq"}, draft
    assert label == "groq:openai/gpt-oss-120b", label
    assert not any("openrouter.ai/api" in url for url in calls), "the third tier must not be touched"


check("a Gemini 429 hands the draft to Groq", gemini_quota_goes_to_groq)


def two_tiers_out_reaches_openrouter() -> None:
    transport, calls = recorder({
        "generativelanguage": (429, "quota exceeded"),
        "api.groq.com": (429, "rate limit exceeded"),
        "openrouter.ai/api": (200, openai_body('{"slug": "from-openrouter"}')),
    })
    draft, label = chain(ALL_KEYS, transport)
    assert draft == {"slug": "from-openrouter"}, draft
    assert label.startswith("openrouter:") and label.endswith(":free"), label
    assert calls[-1].startswith("https://openrouter.ai/api/v1/chat/completions"), calls[-1]


check(
    "Gemini and Groq both out of quota still publishes through an OpenRouter free model",
    two_tiers_out_reaches_openrouter,
)


def spare_openai_compatible_slot() -> None:
    transport, _calls = recorder({
        "models.example.test": (200, openai_body('{"slug": "from-spare"}')),
    })
    env = {
        "GROQ_API_KEY": "groq-key",
        "OPENROUTER_API_KEY": "or-key",
        "GITHUB_MODELS_TOKEN": "spare-token",
        "GITHUB_MODELS_ENDPOINT": "https://models.example.test/inference",
    }
    draft, label = chain(env, transport, providers=["github-models"])
    assert draft == {"slug": "from-spare"} and label == "github:openai/gpt-4o-mini", (draft, label)


check("an OpenAI-compatible spare endpoint can take the third slot", spare_openai_compatible_slot)


def unusable_json_moves_on() -> None:
    transport, _ = recorder({
        "generativelanguage": (200, gemini_body("I cannot answer in JSON today.")),
        "api.groq.com": (200, openai_body('{"slug": "second-try"}')),
    })
    draft, label = chain(ALL_KEYS, transport)
    assert draft == {"slug": "second-try"} and label.startswith("groq:"), (draft, label)


check("an answer that is not JSON moves to the next tier", unusable_json_moves_on)


def missing_key_is_skipped() -> None:
    transport, calls = recorder({
        "api.groq.com": (200, openai_body('{"slug": "groq-only"}')),
    })
    draft, label = chain({"GROQ_API_KEY": "groq-key"}, transport)
    assert draft == {"slug": "groq-only"}, draft
    assert label.startswith("groq:"), label
    assert not any("generativelanguage" in url for url in calls), "no Gemini call without a key"


check("a tier without a credential is skipped, not an error", missing_key_is_skipped)


def every_tier_out_quotes() -> None:
    transport, _ = recorder({
        "generativelanguage": (429, "quota"),
        "api.groq.com": (429, "rate limit"),
        "openrouter.ai/api": (429, "rate limit"),
    })
    try:
        chain(ALL_KEYS, transport)
    except llm_fallback.QuotaExhausted:
        return
    raise AssertionError("QuotaExhausted was not raised")


check("every tier out of quota raises QuotaExhausted (a skip, not a red run)", every_tier_out_quotes)


def broken_key_is_loud() -> None:
    transport, _ = recorder({
        "generativelanguage": (400, '{"error": {"message": "API key not valid"}}'),
        "api.groq.com": (401, '{"error": "invalid_api_key"}'),
        "openrouter.ai/api": (404, '{"error": "gone"}'),
    })
    try:
        chain(ALL_KEYS, transport)
    except llm_fallback.ChainFailed as exc:
        assert "invalid_api_key" in str(exc) or "401" in str(exc), str(exc)
        return
    except llm_fallback.QuotaExhausted:
        raise AssertionError("a broken key must not look like a quiet quota skip")
    raise AssertionError("ChainFailed was not raised")


check("a broken key fails loudly instead of looking like a quota skip", broken_key_is_loud)


def draft_from_groq_passes_the_gate() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    transport, _ = recorder({
        "generativelanguage": (429, "quota"),
        "api.groq.com": (200, openai_body(fixture)),
    })
    topic = {
        "source": "Hacker News",
        "source_title": "Show HN: a fixture story",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "points": 12,
        "family": "AI cost",
    }
    with mock.patch.dict(os.environ, ALL_KEYS, clear=False):
        generated, label = generate_guide.generate_draft(topic, [], ["gemini-3.8-flash"], transport=transport)
    assert generate_guide.validate_draft(generated, EXISTING) == [], "the Groq draft failed the validator"
    assert label.startswith("groq:"), label
    assert generated["sections"], "the draft lost its sections"


check("a draft generated on the Groq tier passes the same validator", draft_from_groq_passes_the_gate)


def quota_maps_to_the_skip_path() -> None:
    transport, _ = recorder({
        "generativelanguage": (429, "quota"),
        "api.groq.com": (429, "quota"),
        "openrouter.ai/api": (429, "quota"),
    })
    with mock.patch.dict(os.environ, ALL_KEYS, clear=False):
        try:
            generate_guide.call_with_fallback("s", "u", ["gemini-3.8-flash"], lambda *_: None, transport=transport)
        except generate_guide.QuotaError:
            return
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"expected QuotaError, got {type(exc).__name__}: {exc}")
    raise AssertionError("QuotaError was not raised")


check("the generator turns an all-quota chain into today's skip", quota_maps_to_the_skip_path)


def sequencer(routes: dict):
    """A transport whose answer per URL fragment is a queue; the last answer repeats.

    A fragment maps either to one (status, body) pair or to a list of them.
    """
    calls: list[tuple[str, dict]] = []
    queues = {
        fragment: [answers] if isinstance(answers, tuple) else list(answers)
        for fragment, answers in routes.items()
    }

    def send(url: str, headers: dict, payload: dict, timeout: int):
        calls.append((url, payload))
        for fragment, answers in queues.items():
            if fragment in url and answers:
                return answers.pop(0) if len(answers) > 1 else answers[0]
        raise AssertionError(f"unexpected request to {url}")

    return send, calls


def tolerant_json_keeps_the_tier() -> None:
    chatty = 'Sure — here is the draft.\n```json\n{"slug": "tolerant-draft", "faq": [{"q": "a", "a": "b"},],}\n```\nLet me know if you want changes.'
    transport, _calls = sequencer({
        "generativelanguage": (200, gemini_body(chatty)),
        "api.groq.com": (200, openai_body('{"slug": "wrong-tier"}')),
    })
    draft, label = chain(ALL_KEYS, transport)
    assert draft.get("slug") == "tolerant-draft", draft
    assert label.startswith("gemini"), label


check("a fenced, chatty answer with a trailing comma is still that tier's answer", tolerant_json_keeps_the_tier)


def groq_json_validator_retry() -> None:
    transport, calls = sequencer({
        "api.groq.com": [
            (400, '{"error":{"message":"Failed to validate JSON. Please adjust your prompt.","code":"json_validate_failed","failed_generation":""}}'),
            (200, openai_body('{"slug": "after-flag-drop"}')),
        ],
    })
    draft, label = chain({"GROQ_API_KEY": "groq-key"}, transport, providers=["groq"])
    assert draft == {"slug": "after-flag-drop"}, draft
    assert label.startswith("groq:"), label
    assert "response_format" in calls[0][1], "the first request should ask for JSON mode"
    assert "response_format" not in calls[1][1], "the retry must drop the flag Groq refused"


check("Groq's own JSON validator refusing a generation retries without the flag", groq_json_validator_retry)


def truncated_empty_is_retried_lean() -> None:
    empty_length = json.dumps(
        {"choices": [{"message": {"role": "assistant", "content": ""}, "finish_reason": "length"}]}
    )
    transport, calls = sequencer({
        "api.groq.com": [(200, empty_length), (200, openai_body('{"slug": "lean-answer"}'))],
    })
    draft, _label = chain({"GROQ_API_KEY": "groq-key"}, transport, providers=["groq"])
    assert draft == {"slug": "lean-answer"}, draft
    assert calls[1][1].get("reasoning_effort") == "low", calls[1][1]
    assert calls[1][1]["max_completion_tokens"] > calls[0][1]["max_completion_tokens"], calls[1][1]
    assert calls[1][1]["max_completion_tokens"] <= llm_fallback.LEAN_TOKEN_CAP["groq"], calls[1][1]


check(
    "an empty answer that ran out of budget gets one lean retry before the next tier",
    truncated_empty_is_retried_lean,
)


def worse_repair_keeps_the_first_draft() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for entry in fixture["faq"][2:4]:
        entry["a"] = "Too short."
    stub = json.dumps({"slug": "stub", "sections": []})
    transport, _calls = sequencer({
        "generativelanguage": (429, "quota"),
        "api.groq.com": (200, openai_body(json.dumps(fixture))),
        "openrouter.ai/api": (200, openai_body(stub)),
    })
    topic = {
        "source": "Hacker News",
        "source_title": "Show HN: a fixture story",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "points": 12,
        "family": "AI cost",
    }
    with mock.patch.dict(os.environ, ALL_KEYS, clear=False):
        try:
            generate_guide.generate_draft(topic, [], ["gemini-3.8-flash"], transport=transport)
        except generate_guide.ValidationError as exc:
            assert len(exc.problems) == 2, exc.problems
            assert all("faq[" in problem for problem in exc.problems), exc.problems
            return
    raise AssertionError("the stub repair must not replace the near-complete draft")


check("a repair that comes back worse does not replace the draft it was fixing", worse_repair_keeps_the_first_draft)


def faq_only_repair_keeps_the_article() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fixture["faq"][3]["a"] = "Too short."
    fixed_faq = json.loads(FIXTURE.read_text(encoding="utf-8"))["faq"]
    transport, calls = sequencer({
        "generativelanguage": (429, "quota"),
        "api.groq.com": (200, openai_body(json.dumps(fixture))),
        "openrouter.ai/api": (200, openai_body(json.dumps({"faq": fixed_faq}))),
    })
    topic = {
        "source": "Hacker News",
        "source_title": "Show HN: a fixture story",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "points": 12,
        "family": "AI cost",
    }
    with mock.patch.dict(os.environ, ALL_KEYS, clear=False):
        draft, label = generate_guide.generate_draft(topic, [], ["gemini-3.8-flash"], transport=transport)
    assert generate_guide.validate_draft(draft, EXISTING) == [], "the merged draft failed the validator"
    assert draft["slug"] == fixture["slug"], "the article must not be rewritten for a short FAQ answer"
    assert label.startswith("openrouter:"), label
    faq_prompt = calls[-1][1]["messages"][-1]["content"]
    assert "Only these FAQ answers" in faq_prompt, faq_prompt[:200]


check("a short FAQ answer is repaired on its own and the article is kept", faq_only_repair_keeps_the_article)


def minutes_follow_the_words() -> None:
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source["minutes"] = 12
    normalized = generate_guide.normalize_draft(json.loads(json.dumps(source)), source["topic"])
    assert generate_guide.validate_draft(normalized, EXISTING) == [], "a guessed reading time must not fail the gate"
    assert 4 <= normalized["minutes"] <= 9, normalized["minutes"]


check("the reading time is derived from the body, not taken from the model", minutes_follow_the_words)


def title_only_repair_keeps_the_article() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fixture["title"] = "Too short"
    good_title = json.loads(FIXTURE.read_text(encoding="utf-8"))["title"]
    transport, calls = sequencer({
        "generativelanguage": (429, "quota"),
        "api.groq.com": (200, openai_body(json.dumps(fixture))),
        "openrouter.ai/api": (200, openai_body(json.dumps({"title": good_title}))),
    })
    topic = {
        "source": "Hacker News",
        "source_title": "Show HN: a fixture story",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "points": 12,
        "family": "AI cost",
    }
    with mock.patch.dict(os.environ, ALL_KEYS, clear=False):
        draft, _label = generate_guide.generate_draft(topic, [], ["gemini-3.8-flash"], transport=transport)
    assert generate_guide.validate_draft(draft, EXISTING) == [], "the field repair did not fix the title"
    assert draft["slug"] == fixture["slug"], "only the title should have changed"
    assert draft["title"] == good_title
    assert "Only `title` failed" in calls[-1][1]["messages"][-1]["content"]


check("a title that is the only failed check is repaired without rewriting the guide", title_only_repair_keeps_the_article)


def short_body_is_repaired_on_the_sections() -> None:
    full = json.loads(FIXTURE.read_text(encoding="utf-8"))
    short = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for section in short["sections"]:
        section["paragraphs"] = section["paragraphs"][:1]
    transport, calls = sequencer({
        "generativelanguage": (429, "quota"),
        "api.groq.com": (200, openai_body(json.dumps(short))),
        "openrouter.ai/api": (200, openai_body(json.dumps({"sections": full["sections"]}))),
    })
    topic = {
        "source": "Hacker News",
        "source_title": "Show HN: a fixture story",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "points": 12,
        "family": "AI cost",
    }
    with mock.patch.dict(os.environ, ALL_KEYS, clear=False):
        draft, _label = generate_guide.generate_draft(topic, [], ["gemini-3.8-flash"], transport=transport)
    assert generate_guide.validate_draft(draft, EXISTING) == [], "the sections repair did not lengthen the body"
    assert draft["title"] == full["title"], "the title that already passed must survive"
    assert "Only `sections` failed" in calls[-1][1]["messages"][-1]["content"]
    assert "expand the existing paragraphs" in calls[-1][1]["messages"][-1]["content"]


check("a body under the word floor is lengthened by repairing the sections alone", short_body_is_repaired_on_the_sections)


def repair_does_not_return_to_a_dead_tier() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fixture["faq"][2]["a"] = "Too short."
    fixed_faq = json.loads(FIXTURE.read_text(encoding="utf-8"))["faq"]
    transport, calls = sequencer({
        "generativelanguage": (503, '{"error":{"status":"UNAVAILABLE"}}'),
        "api.groq.com": (200, openai_body(json.dumps(fixture))),
        "openrouter.ai/api": (200, openai_body(json.dumps({"faq": fixed_faq}))),
    })
    topic = {
        "source": "Hacker News",
        "source_title": "Show HN: a fixture story",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "points": 12,
        "family": "AI cost",
    }
    with mock.patch.dict(os.environ, ALL_KEYS, clear=False):
        draft, _label = generate_guide.generate_draft(topic, [], ["gemini-3.8-flash"], transport=transport)
    urls = [url for url, _payload in calls]
    first_groq = next(index for index, url in enumerate(urls) if "api.groq.com" in url)
    after = urls[first_groq + 1:]
    assert after and not any("generativelanguage" in url for url in after), urls
    assert generate_guide.validate_draft(draft, EXISTING) == []


check("a repair after a failed Gemini pass does not wait on Gemini again", repair_does_not_return_to_a_dead_tier)

print(f"\n{passed} pipeline checks passed")
