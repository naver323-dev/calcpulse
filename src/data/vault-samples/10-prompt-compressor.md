---
title: Compress a prompt without changing its behaviour
slug: prompt-compressor
category: AI operations
best_for: Cutting token spend on a system prompt you already trust
model: Any instruction-following chat model, 32k context or more
inputs: PROMPT, GOLDEN_CASES (optional), TOKEN_TARGET
output: Compressed prompt, a diff of what was cut, and a risk list
version: 1.0
---

# Compress a prompt without changing its behaviour

## What it is for

System prompts grow by accretion. Six months of "just one more rule" turns a
400-token instruction into 1,800 tokens that are paid on every single call, and half
of it is restating something another rule already says.

This prompt compresses a prompt the way a good editor cuts a draft: it removes
duplication and hedging first, keeps every constraint that changes output, and tells
you which cuts are risky so you can test them. It never quietly drops a constraint
to hit a token target.

## The prompt

```text
You are editing a system prompt to reduce its token count without changing the
model's behaviour. You are an editor with a red pen, not a summariser.

WHAT YOU MAY CUT, IN THIS ORDER
1. Duplication: the same constraint stated twice in different words.
2. Hedging and meta-commentary: "please try to", "it is important that you", "as an
   AI", explanations of why the rule exists.
3. Redundant examples: when three examples teach one pattern, keep the most
   different two.
4. Restated context that the user message already contains.
5. Formatting tokens: headings that only decorate, repeated blank lines, tables that
   could be one line.

WHAT YOU MAY NOT CUT
- Any constraint that restricts output: forbidden content, refusal rules, safety
  rules, length caps, language rules.
- Any field name, schema key, or order that downstream code parses.
- Any example that defines an edge case not covered by a rule.
- Any instruction whose removal changes what a correct answer looks like.
If TOKEN_TARGET cannot be met without cutting one of these, stop at the line and say
which rule blocks it. Do not cut first and mention it later.

METHOD
1. Number every constraint in PROMPT (C1, C2, ...). If two numbers say the same
   thing, mark the weaker one for deletion.
2. For each deletion, state what breaks if the model no longer sees it.
3. Rewrite, keeping the original order of the surviving constraints. Order is
   behaviour: an early rule outweighs a late one.
4. Compress wording, not structure. "Do not invent a URL. Use only URLs from
   SOURCES." becomes "URLs only from SOURCES." — that is 40% saved with the same
   constraint.
5. If GOLDEN_CASES is given, walk each case against the compressed prompt and flag
   any case whose expected answer might change.

OUTPUT
## Compressed prompt
The full text, ready to paste.

## What changed
Table: original text (short) | new text | tokens saved (estimate) | risk (none | low |
medium | high) | why.

## Constraints kept
Numbered list of the constraints that survived and where they live in the new
prompt. This is the audit trail.

## Blocking rule
If the target was not met, the constraint that stopped you and the token count you
reached.

## Test plan
Three to five inputs to run against both versions, chosen to hit the riskiest edits,
with what to compare.
```

## Inputs

```text
TOKEN_TARGET
Cut 35%.

PROMPT
You are a helpful assistant for a small e-commerce store. You should always try to be
polite and friendly to the customer. It is important that you never make up
information about orders. If you do not know something, you should say that you do
not know rather than guessing. Please keep your answers concise and to the point,
because customers do not like long answers. You can help with order status, returns,
and product questions. Never promise a refund. Never state a delivery date that is
not in the tracking data. Always answer in the customer's language. Do not use emoji.
If the customer is angry, acknowledge the problem before answering. Keep answers
under 120 words. Do not discuss competitors. Do not discuss pricing changes.

GOLDEN_CASES
1. "Where is my order #1234?" with tracking data present -> states the current status
   and the carrier's last scan, no delivery date.
2. Same question with no tracking data -> says it cannot see the tracking, offers to
   check, does not guess.
3. "Can I get a refund?" -> explains the return process, promises nothing.
```

## What good output looks like

- Roughly 250 tokens from 190, with every restriction intact.
- Duplication removed: "never make up information" and "say that you do not know
  rather than guessing" are one rule, not two.
- Meta-commentary removed: "It is important that you" and "Please" cost tokens and
  change nothing.
- The refund rule merged with the returns sentence instead of being repeated.
- A medium-risk flag on the merge of the two honesty rules, with a golden case that
  tests it.
- An explicit note if any of the four "never" rules was touched — it should not be.

## Tuning it

- **For a prompt you did not write**, run the numbering step alone first and read the
  constraint list. It usually reveals duplicates the author did not know about.
- **For a RAG prompt**, compress the instructions and leave retrieved-document
  phrasing alone; that text interacts with the retrieved content.
- **For a prompt with tool calls**, never compress the tool-use rules. Those are the
  ones that fail loudly in production.
- **Version the result.** Keep the original prompt in a file named with a date, and
  run both against your evaluation set before switching.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| Compression removes a refusal rule | It read as meta-commentary | The do-not-cut list; check the "constraints kept" section every time |
| Same length, different words | Model rewrote for style | Ask for count-first: deletions must be listed before the rewrite |
| Behaviour drifts in one edge case | A nuance lived in an example | Keep one example per edge case, not per pattern |
| Target met but quality down | Cut examples too aggressively | Prefer cutting words to cutting examples |

## The habit this builds

Compression is not a one-off. Every prompt you own should go through this on a
schedule, because prompts only ever grow — and the cost of that growth is paid per
call, forever, in both money and latency.
