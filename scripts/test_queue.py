#!/usr/bin/env python3
"""Offline tests for queue-first publishing (scripts/content_queue.py, scripts/generate_guide.py).

No network, no API key, no build: what is pinned here is the part that must never regress —
a queued guide may only be published when its window is open, it is held to the same
validator as a generated draft, a guide that fails is rejected with its reasons instead of
blocking the item behind it, and an empty queue leaves the live pipeline untouched.

    python3 scripts/test_queue.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from datetime import date, timedelta
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import content_queue  # noqa: E402
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


def fixture_draft() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def fixture_topic() -> dict:
    return {
        "family": "AI cost",
        "source": "Hacker News",
        "source_title": "Show HN: a fixture story about API bills",
        "source_url": "https://news.ycombinator.com/item?id=1",
        "points": 12,
    }


def item(item_id: str, *, publish_after: str, slug: str, draft: dict | None = None,
         expires_at: str | None = None, topic_patch: dict | None = None) -> dict:
    draft = json.loads(json.dumps(draft if draft is not None else fixture_draft()))
    draft["slug"] = slug
    topic = fixture_topic()
    if topic_patch:
        topic.update(topic_patch)
    out = {
        "schema": "content-queue/1",
        "id": item_id,
        "publish_after": publish_after,
        "payload": {"topic": topic, "draft": draft},
    }
    if expires_at:
        out["expires_at"] = expires_at
    return out


class Workspace:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.queue = Path(self._tmp.name) / "content_queue"
        self.queue.mkdir(parents=True)

    def write(self, name: str, data: dict) -> Path:
        path = self.queue / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def files(self) -> list[Path]:
        return sorted(self.queue.glob("*.json"))

    def rejected(self) -> list[Path]:
        folder = self.queue / "rejected"
        return sorted(folder.glob("*.json")) if folder.is_dir() else []

    def close(self) -> None:
        self._tmp.cleanup()


def quiet(*_args, **_kwargs) -> None:
    """Swallow the module's log lines inside tests."""


print("queue window")


def a_ready_item_is_taken() -> None:
    ws = Workspace()
    try:
        today = date.today()
        ws.write("a", item("cp-ready-01", publish_after=today.isoformat(), slug="llm-cost-2027"))
        taken = content_queue.take(ws.queue, day=today, log=quiet)
        assert taken is not None, "a due item must be taken"
        assert taken.id == "cp-ready-01", taken.id
        assert taken.slug == "llm-cost-2027", taken.slug
    finally:
        ws.close()


check("a due item is taken", a_ready_item_is_taken)


def a_future_item_waits_instead_of_blocking() -> None:
    ws = Workspace()
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        ws.write("b", item("cp-wait-01", publish_after=tomorrow.isoformat(), slug="later-guide"))
        ws.write("c", item("cp-ready-02", publish_after=today.isoformat(), slug="due-guide"))
        taken = content_queue.take(ws.queue, day=today, log=quiet)
        assert taken is not None and taken.id == "cp-ready-02", "the due item is behind a waiting one"
        assert len(ws.files()) == 2, "taking does not remove anything"
        assert ws.rejected() == [], "a waiting item is not rejected"
    finally:
        ws.close()


check("a future item waits and does not block a due one", a_future_item_waits_instead_of_blocking)


def an_expired_item_is_rejected() -> None:
    ws = Workspace()
    try:
        today = date.today()
        yesterday = today - timedelta(days=1)
        ws.write("d", item("cp-stale-01", publish_after=yesterday.isoformat(), slug="stale-guide",
                           expires_at=yesterday.isoformat()))
        taken = content_queue.take(ws.queue, day=today, log=quiet)
        assert taken is None, "an expired item is not publishable"
        assert ws.files() == [], "it leaves the queue"
        reasons = json.loads(ws.rejected()[0].read_text(encoding="utf-8"))["rejected"]["reasons"]
        assert "expired" in " ".join(reasons), reasons
    finally:
        ws.close()


check("an expired item is rejected with its reason", an_expired_item_is_rejected)


def a_malformed_item_is_rejected() -> None:
    ws = Workspace()
    try:
        today = date.today()
        data = item("cp-broken-01", publish_after=today.isoformat(), slug="broken-guide")
        del data["payload"]["topic"]["source_url"]
        ws.write("e", data)
        taken = content_queue.take(ws.queue, day=today, log=quiet)
        assert taken is None, "an item without provenance cannot publish"
        reasons = json.loads(ws.rejected()[0].read_text(encoding="utf-8"))["rejected"]["reasons"]
        assert "source_url" in " ".join(reasons), reasons
    finally:
        ws.close()


check("a malformed item is rejected with the missing field", a_malformed_item_is_rejected)


def a_family_mismatch_is_rejected() -> None:
    ws = Workspace()
    try:
        today = date.today()
        draft = fixture_draft()
        draft["topic"] = "SaaS & tooling"
        ws.write("f", item("cp-family-01", publish_after=today.isoformat(), slug="family-guide", draft=draft))
        taken = content_queue.take(ws.queue, day=today, log=quiet)
        assert taken is None, "a guide whose family disagrees with its topic cannot publish"
        reasons = json.loads(ws.rejected()[0].read_text(encoding="utf-8"))["rejected"]["reasons"]
        assert "does not match" in " ".join(reasons), reasons
    finally:
        ws.close()


check("a draft/topic family mismatch is rejected", a_family_mismatch_is_rejected)


print("editorial gate")


def a_queued_guide_passes_the_same_validator() -> None:
    draft = generate_guide.normalize_draft(fixture_draft(), "AI cost")
    problems = generate_guide.validate_draft(draft, EXISTING)
    assert problems == [], f"the fixture must pass the validator it will meet in the queue: {problems[:3]}"


check("a queued guide is validated by the same rules as a generated one", a_queued_guide_passes_the_same_validator)


def a_duplicate_slug_is_not_taken() -> None:
    ws = Workspace()
    try:
        today = date.today()
        ws.write("g", item("cp-dup-01", publish_after=today.isoformat(), slug="ai-api-cost-calculator"))
        taken = content_queue.take(
            ws.queue, day=today, is_published=lambda slug: slug in EXISTING, log=quiet
        )
        assert taken is None, "an already published slug is not publishable again"
        reasons = json.loads(ws.rejected()[0].read_text(encoding="utf-8"))["rejected"]["reasons"]
        assert "already published" in " ".join(reasons), reasons
    finally:
        ws.close()


check("a duplicate slug is rejected, not republished", a_duplicate_slug_is_not_taken)


def a_bad_queued_draft_does_not_stop_the_next() -> None:
    ws = Workspace()
    try:
        today = date.today()
        bad = fixture_draft()
        bad["title"] = "short"
        bad["slug"] = "bad-titled-guide"
        ws.write("h1", item("cp-bad-01", publish_after=today.isoformat(), slug="bad-titled-guide", draft=bad))
        ws.write("h2", item("cp-good-02", publish_after=today.isoformat(), slug="good-guide-2027"))
        # Mirror pick_from_queue: take, validate, reject, take again.
        slugs = set(EXISTING)
        picked = None
        while True:
            taken = content_queue.take(ws.queue, day=today, is_published=lambda s: s in slugs, log=quiet)
            if taken is None:
                break
            draft = generate_guide.normalize_draft(taken.draft, taken.topic["family"])
            problems = generate_guide.validate_draft(draft, slugs)
            if problems:
                content_queue.reject(ws.queue, taken, problems, log=quiet)
                continue
            picked = taken
            break
        assert picked is not None and picked.id == "cp-good-02", "the guide behind a bad one must still be taken"
        assert ws.rejected()[0].name == "h1.json", [p.name for p in ws.rejected()]
    finally:
        ws.close()


check("a draft that fails the validator is rejected and the next item is taken",
      a_bad_queued_draft_does_not_stop_the_next)

print("queue surface")


def the_report_marks_ready_and_waiting() -> None:
    ws = Workspace()
    try:
        today = date.today()
        ws.write("i1", item("cp-ready-03", publish_after=today.isoformat(), slug="ready-guide"))
        ws.write("i2", item("cp-wait-02", publish_after=(today + timedelta(days=1)).isoformat(), slug="wait-guide"))
        text = content_queue.report(ws.queue, day=today)
        assert "cp-ready-03" in text and "cp-wait-02" in text, text
        assert "1 of 2 item(s) publishable today" in text, text
    finally:
        ws.close()


check("the queue report separates ready from waiting", the_report_marks_ready_and_waiting)


def an_empty_queue_is_not_an_error() -> None:
    ws = Workspace()
    try:
        assert content_queue.take(ws.queue, day=date.today(), log=quiet) is None
        assert content_queue.load(ws.queue, log=quiet) == []
        assert "empty" in content_queue.report(ws.queue, day=date.today())
    finally:
        ws.close()


check("an empty queue means 'fall back to the live pipeline'", an_empty_queue_is_not_an_error)


def the_schema_is_documented() -> None:
    assert content_queue.SCHEMA == "content-queue/1"
    readme = (Path(__file__).resolve().parents[1] / "content_queue" / "README.md").read_text(encoding="utf-8")
    assert content_queue.SCHEMA in readme, "the README documents the schema this code writes"


check("the queue schema is documented where the batch reads it", the_schema_is_documented)

print(f"\n{passed} queue checks passed")
