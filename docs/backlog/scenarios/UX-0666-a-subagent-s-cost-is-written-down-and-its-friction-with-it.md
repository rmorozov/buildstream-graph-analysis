# UX-666: a subagent's cost is written down, and its friction with it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-521 (the tokens-by-phase measurement), UX-508 (the process bands) | **Serves:** the round choosing a model and a shape for its next agent | **Topic:** docs

## Motivation

The Agent tool returns tokens, tool calls and wall clock for every
run, and until round 90 that figure survived only as a sentence in a
round document's Standing paragraph, when it survived at all:

```text
round 82   five researchers, ~665k tokens, two cut by the session limit and re-run — recorded nowhere but the round doc
round 77   three agents, ~610k; the control walk 336k                         — same
tools/dev_process_bands.py                                                     reads Outcomes; knows nothing about runs
tools/dev_track_cost.py                                                        reads the harness's own JSONL and prints; used once (round 80), persisted nowhere
```

Round 90 opened `docs/audits/agent-runs.md` with the twelve runs it
could reconstruct. What is missing is the *habit* and the *reader*:
nothing requires the row, and nothing reads the table.

## Required Fix

- Every agent body (`researcher`, `implementer`, `verifier`, and the
  ones the `walk`/`design-review` skills launch) ends its report with
  one **friction** line — what cost the most, what was missing, what
  went wrong — and the orchestrating session appends the row
  (tokens, tool calls, wall from the tool's own figures; the friction
  line verbatim).
- `dev_track_cost.py` writes the row (`--append docs/audits/agent-runs.md`) instead of only printing, and `dev_process_bands.py` gains a runs band: tokens per agent kind and
  model, cuts and re-runs, over the last N rows — reported, not
  verdicted, the tool's own rule.
- A guard: every round document from 90 on either carries a
  `## Agents` table or states "no agents launched"; the ledger's
  rows for that round match the table.

## Out of Scope

- Measuring the orchestrating session's own tokens — not returned by
  any tool; the round doc's Standing paragraph keeps the estimate.

## Acceptance Test

`dev_process_bands.py --runs 12` prints the twelve round-90 rows'
tokens by kind; mutation: drop a round-90 row — the round-doc guard
reds naming the round.
