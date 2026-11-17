---
title: Meeting notes to decisions, owners and dates
slug: meeting-notes-to-actions
category: Operations
best_for: Turning a 900-word transcript into four lines people act on
model: Any instruction-following chat model, 8k context or more
inputs: NOTES, TODAY, ATTENDEES (optional)
output: One JSON object, then a short follow-up email
version: 1.0
---

# Meeting notes to decisions, owners and dates

## What it is for

Most meeting notes fail in the same three ways: nobody knows what was decided,
actions have no owner, and dates are implied rather than written. This prompt
extracts exactly those three things and refuses to invent the rest. Anything the
notes do not settle is returned as an open question rather than a decision, which
is the difference between notes people trust and notes people re-litigate.

## The prompt

```text
You turn raw meeting notes into a record a team can act on. You are strict about
the difference between what was said, what was decided, and what someone suggested.

INPUTS: NOTES (raw notes or transcript), TODAY (ISO date of the meeting),
ATTENDEES (optional list of names and roles).

EXTRACTION RULES
1. A decision is a statement the group settled. A suggestion, a preference or an
   idea is not a decision. If NOTES do not make clear that the group agreed, put it
   in open_questions, not decisions.
2. Every action needs an owner. If NOTES name a role but not a person, use the role
   and set owner_confirmed to false. If no owner appears, do not guess — put the
   action in open_questions under "unowned".
3. Every date must be either an ISO date resolved from TODAY ("Thursday" becomes
   the coming Thursday's date) or the literal word "unspecified". Never invent a
   deadline to make a row look complete.
4. Quote at most 15 words of the notes as evidence for each decision and action.
   The quote must appear verbatim in NOTES.
5. Do not summarise the conversation. Nobody needs a shorter version of a meeting.
6. If NOTES contain two statements that contradict each other, record both in
   conflicts with the quotes, and do not pick a winner.
7. Names: use the spelling in ATTENDEES if there is one; otherwise the spelling in
   NOTES. Never merge two similar names.

ORDERING
- decisions in the order they were made
- actions by due date, unspecified last
- open_questions by how soon they block someone

Return one JSON object and nothing else:
{
  "meeting": {"title": "", "date": "", "attendees": []},
  "decisions": [
    {"decision": "", "evidence": "", "reversible": true, "decided_by": ""}
  ],
  "actions": [
    {"action": "", "owner": "", "owner_confirmed": true, "due": "",
     "blocked_by": "", "evidence": ""}
  ],
  "open_questions": [
    {"question": "", "asked_by": "", "blocks": ""}
  ],
  "conflicts": [
    {"statement_a": "", "statement_b": ""}
  ],
  "follow_up_email": {
    "subject": "",
    "body": ""
  }
}

FOLLOW-UP EMAIL
- 120 words maximum, plain text.
- First line: what was decided, in one sentence.
- Then the actions, one per line, "owner — action — due".
- Then the open questions that need an answer before the next meeting.
- No greetings beyond "Hi all," and no closing paragraph about alignment or
  momentum. Sign with the sender name in SENDER if given, otherwise no signature.
- If there are no decisions, say so in the first line rather than padding.
```

## Inputs

```text
NOTES
Weekly product sync, 17 Nov. Present: Jae (PM), Soo (eng), Marcus (support),
Priya (design, dialled in late).
- Jae opened with the churn number, 3.1% in October, mostly self-serve.
- Soo said the export rewrite is two weeks of work if we skip the CSV streaming.
- We agreed to ship the export rewrite without streaming and revisit in January.
  Marcus flagged that support gets three tickets a week about >5k row exports.
- Priya suggested moving the onboarding checklist above the fold. No one objected,
  but Jae said design should own it.
- Discussion of pricing: Jae wants to test $19, Soo thinks it breaks the annual
  cohort. Nothing resolved. Priya to bring a pricing page mockup.
- Marcus will write the changelog for the 5k cap by Wednesday.
- Action from last week (Soo: load test on the report endpoint) still open, no date.
- Next sync 24 Nov.

TODAY
2026-11-17

ATTENDEES
Jae — product manager
Soo — backend engineer
Marcus — support lead
Priya — product designer
```

Expected shape of a good answer:

- One decision: the export rewrite ships without streaming, revisit January.
- The onboarding checklist idea goes to actions or open questions, not decisions —
  nobody agreed, one person moved it to design.
- Pricing appears in `conflicts` or `open_questions`, not as a decision.
- Marcus's changelog gets `2026-11-19` (the coming Wednesday).
- Soo's load test appears as an action with `due: "unspecified"` and
  `owner_confirmed: true`.

## Tuning it

- **Add a `risks` array** if your team tracks them; leave it out otherwise.
- **Change "reversible"** to your own decision tag (`type_1` / `type_2`) if you use
  Bezos framing. It is there because a reversible decision should not get the same
  meeting time as an irreversible one.
- **Feed it transcripts, not summaries.** ASR transcripts with speaker labels work
  better than a human summary, because the evidence quotes survive.
- **Chunk long meetings.** Above roughly 6,000 words, split by agenda item and run
  each chunk, then merge. A single pass over a two-hour transcript starts dropping
  actions at the edges.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Polite suggestions become decisions | Notes use "we should" and "let's" | Add to rules: "we should" is never a decision unless followed by explicit agreement |
| Everyone owes something | Model assigns the most-mentioned name | Keep the owner_confirmed field and ignore unconfirmed rows |
| Dates drift a week | TODAY missing or ambiguous | Always pass TODAY as ISO; check the weekday yourself |
| Actions duplicated | Two chunks overlapped | De-duplicate on action text after merging |

## Why this one survives contact with a real team

The follow-up email is written to be forwarded, not admired. It has no paragraph
about alignment, because the reader wants to know what changed and what they owe.
That single choice is what gets these notes read past line three.
