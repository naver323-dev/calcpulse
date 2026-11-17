#!/usr/bin/env python3
"""Queue-first publishing for CalcPulse.

The daily run has two sources for a guide, in this order:

  1. ``content_queue/<id>.json`` — a guide written ahead of time by the Pickle + Gemini +
     Grok batch (see ``content_queue/README.md``). It is used when its ``publish_after``
     window is open, and the file leaves the queue in the same commit.
  2. the live pipeline in ``scripts/generate_guide.py`` — collect a topic from free public
     sources, then ask the free LLM tiers. Used only when the queue has nothing due, so the
     Gemini/Groq quota goes into the next batch instead of every day.

The editorial gate is not duplicated here: a queued guide is normalised and validated by the
same functions the generated draft goes through, and it still has to pass ``npm test``. This
module owns the queue file format and the bookkeeping only.

A guide that cannot be published is moved to ``content_queue/rejected/`` with the reasons
attached, so a broken item never blocks the ones behind it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

SCHEMA = "content-queue/1"
DEFAULT_DIR = Path(__file__).resolve().parents[1] / "content_queue"
REJECTED_DIRNAME = "rejected"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,80}$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# The topic is the provenance the page cites (source name, headline, URL) and the family the
# calculator is chosen from, so it must travel with the item instead of being collected later.
REQUIRED_TOPIC_FIELDS = ("family", "source", "source_title", "source_url")
REQUIRED_DRAFT_FIELDS = ("slug", "title", "h1", "description", "sections", "faq")


def _quiet(*_args, **_kwargs) -> None:
    """Swallow progress output (tests, --quiet)."""


@dataclass
class Item:
    """One queue file: where it is, what it says, and when it may run."""

    path: Path
    data: dict
    problems: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.data.get("id") or self.path.stem)

    @property
    def publish_after(self) -> str:
        return str(self.data.get("publish_after") or "")

    @property
    def expires_at(self) -> str:
        return str(self.data.get("expires_at") or "")

    @property
    def payload(self) -> dict:
        payload = self.data.get("payload")
        return payload if isinstance(payload, dict) else {}

    @property
    def topic(self) -> dict | None:
        topic = self.payload.get("topic")
        return topic if isinstance(topic, dict) else None

    @property
    def draft(self) -> dict | None:
        draft = self.payload.get("draft")
        return draft if isinstance(draft, dict) else None

    @property
    def slug(self) -> str:
        draft = self.draft or {}
        return str(draft.get("slug") or "")


def parse_day(value: str) -> date | None:
    if not value or not DAY_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _payload_problems(item: Item) -> list[str]:
    problems: list[str] = []
    if item.data.get("schema") not in (None, SCHEMA):
        problems.append(f"schema {item.data.get('schema')!r} is not {SCHEMA}")

    if not item.publish_after:
        problems.append("publish_after is missing (YYYY-MM-DD)")
    elif parse_day(item.publish_after) is None:
        problems.append(f"publish_after {item.publish_after!r} is not a YYYY-MM-DD date")
    if item.expires_at and parse_day(item.expires_at) is None:
        problems.append(f"expires_at {item.expires_at!r} is not a YYYY-MM-DD date")

    topic = item.topic
    if topic is None:
        problems.append("payload.topic is missing")
    else:
        for name in REQUIRED_TOPIC_FIELDS:
            if not topic.get(name):
                problems.append(f"payload.topic.{name} is missing")
        if topic.get("source_url") and not str(topic["source_url"]).startswith("https://"):
            problems.append("payload.topic.source_url must be https")

    draft = item.draft
    if draft is None:
        problems.append("payload.draft is missing")
    else:
        for name in REQUIRED_DRAFT_FIELDS:
            if not draft.get(name):
                problems.append(f"payload.draft.{name} is missing")
        if not isinstance(draft.get("sections"), list) or not draft.get("sections"):
            problems.append("payload.draft.sections must be a non-empty list")
        if not isinstance(draft.get("faq"), list) or not draft.get("faq"):
            problems.append("payload.draft.faq must be a non-empty list")
        if topic is not None and draft.get("topic") and draft["topic"] != topic.get("family"):
            problems.append(
                f"payload.draft.topic {draft['topic']!r} does not match payload.topic.family {topic.get('family')!r}"
            )
    return problems


def load(queue_dir: Path = DEFAULT_DIR, *, log=_quiet) -> list[Item]:
    """Every readable item in the queue, oldest scheduled first."""
    queue_dir = Path(queue_dir)
    if not queue_dir.is_dir():
        return []
    items: list[Item] = []
    for path in sorted(queue_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log(f"  ! queue {path.name}: unreadable ({exc})")
            items.append(Item(path=path, data={"id": path.stem, "unreadable": str(exc)}))
            continue
        if not isinstance(data, dict):
            items.append(Item(path=path, data={"id": path.stem, "unreadable": "not a JSON object"}))
            continue
        item = Item(path=path, data=data)
        item.problems = _payload_problems(item)
        if not ID_RE.match(item.id):
            item.problems.append(f"id {item.id!r} must be 3-80 characters of [A-Za-z0-9._-]")
        items.append(item)
    items.sort(key=lambda it: (it.publish_after or "9999-99-99", it.id))
    return items


def window_state(item: Item, day: date) -> str | None:
    """None when the item may run today, otherwise the reason it may not."""
    if "unreadable" in item.data:
        return f"unreadable: {item.data['unreadable']}"
    if item.problems:
        return "invalid: " + "; ".join(item.problems[:3])
    start = parse_day(item.publish_after)
    if start is None:
        return "invalid publish_after"
    if day < start:
        return f"waiting for {item.publish_after}"
    end = parse_day(item.expires_at) if item.expires_at else None
    if end is not None and day > end:
        return f"expired on {item.expires_at}"
    return None


def take(queue_dir: Path = DEFAULT_DIR, *, day: date, is_published=None, log=_quiet) -> Item | None:
    """First item that may be published today; hopeless items are rejected on the way."""
    is_published = is_published or (lambda _slug: False)
    for item in load(queue_dir, log=log):
        reason = window_state(item, day)
        if reason:
            if reason.startswith("waiting"):
                continue
            _reject(queue_dir, item, [reason], log=log)
            continue
        if item.slug and is_published(item.slug):
            _reject(queue_dir, item, [f"slug {item.slug} is already published"], log=log)
            continue
        return item
    return None


def reject(queue_dir: Path, item: Item, reasons: list[str], *, log=_quiet) -> None:
    """Reject for a project-level reason (the validator said no)."""
    _reject(queue_dir, item, reasons, log=log)


def _reject(queue_dir: Path, item: Item, reasons: list[str], *, log=_quiet) -> None:
    queue_dir = Path(queue_dir)
    rejected_dir = queue_dir / REJECTED_DIRNAME
    rejected_dir.mkdir(parents=True, exist_ok=True)
    data = dict(item.data)
    data["rejected"] = {"on": date.today().isoformat(), "reasons": [str(r)[:400] for r in reasons]}
    (rejected_dir / item.path.name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        item.path.unlink()
    except OSError:
        pass
    log(f"  ! rejected {item.id}: {reasons[0] if reasons else 'no reason given'}")


def retire(item: Item, *, log=_quiet) -> None:
    """Remove a published item from the queue (git history keeps the record)."""
    try:
        item.path.unlink()
    except OSError as exc:
        log(f"  ! could not remove {item.path.name}: {exc}")
        return
    log(f"  · queue item {item.id} published and removed")


def report(queue_dir: Path = DEFAULT_DIR, *, day: date) -> str:
    items = load(queue_dir)
    if not items:
        return f"queue {queue_dir}: empty — the live pipeline is the only source today"
    lines = [f"queue {queue_dir} ({day.isoformat()})", "", "STATE    PUBLISH_AFTER  ID                              SLUG"]
    for item in items:
        reason = window_state(item, day)
        state = "READY" if reason is None else ("WAIT" if reason.startswith("waiting") else "BAD")
        lines.append(
            f"{state:<8} {item.publish_after or '-':<14} {item.id:<31} {item.slug or '?'}"
            + (f"  ({reason})" if reason and not reason.startswith("waiting") else "")
        )
    ready = sum(1 for item in items if window_state(item, day) is None)
    lines.append("")
    lines.append(f"{ready} of {len(items)} item(s) publishable today")
    return "\n".join(lines)
