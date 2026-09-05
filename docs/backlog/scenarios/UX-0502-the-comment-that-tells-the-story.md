# UX-502: the comment that tells the story

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-497 (the budget these are over) | **Serves:** every session that opens a dev tool to use it, not to relive it | **Topic:** docs | **Area:** tools

## Motivation

The dev tools carry their own history in-line. Measured in round 74:

```text
tools/dev_tier_drift.py       206 comment lines / 46 code lines   (448 %)
tools/dev_trace_coverage.py   module docstring 85 lines
tools/dev_plane_capability.py module docstring 55 lines
grandfathered over the 25-line cap (UX-497)   8 of 11 files
```

`dev_tier_drift.py`'s docstring walks through three rejected CI
designs with their measured factors. That record is valuable and it
already exists — in `UX-418`'s and `UX-420`'s Outcome sections, which
is where the guide (§3.6) says superseded explanations live. In the
tool, every session that runs `--against` pays for the narrative first.

## Required Fix

For each grandfathered file: a docstring of what it does, how it is
invoked, and one sentence per non-obvious decision *with the task id
that holds the argument* — under 25 lines — and the in-body comment
blocks reduced the same way. Nothing is lost: each deleted paragraph
is checked to exist in the named task file, and where it does not, it
is appended there first (§3.6, the annotation rule).

Before/after per file, pasted: docstring lines, comment lines, code
lines. The `UX-497` grandfather table shrinks to empty in the same
commit, one entry per file brought under the cap.

## Out of Scope

- Any behaviour change in the tools — a refactor-stream item: the
  measurement moves, nothing else does.
- The test files' docstrings — many are long for the same reason;
  measure them first and file separately if they are the same shape.

## Acceptance Test

`tests/unit/test_the_register_is_terse.py` green with an empty
`GRANDFATHERED`; the tools' own guards green; per-file before/after
lines pasted.

## Outcome (round 75, 2026-09-01) — 🟢 Done

### The gap, measured

Eight of eleven budgeted files over `UX-497`'s 25-line cap. Each
docstring walks its rejected designs with their measured factors — a
record that is valuable and that already exists, in the Outcome
sections §3.6 says superseded explanations live in. In the tool, every
session that runs `--against` pays for the narrative first.

### After

```text
docstring lines, before -> after         comment lines, dev_tier_drift
  dev_perfetto_queries    29 -> 16         314 -> 197
  dev_process_bands       29 -> 17
  no_bulk_add             33 -> 17       GRANDFATHERED = {}
  dev_refresh_analysis    35 -> 22
  dev_js_deps             38 -> 25
  dev_plane_capability    55 -> 24
  dev_tier_drift          77 -> 24
  dev_trace_coverage      85 -> 25
```

Each is now what the tool does, how it is invoked, and one sentence per
non-obvious decision **with the task id that holds the argument**.
`dev_tier_drift.py`'s six longest in-body `#:` blocks went the same
way; the constants still say why they are what they are, in a sentence
each with the run that sized them.

**Nothing was lost, and that was checked before a line was cut.** Every
distinctive figure in all eight docstrings — ratios, byte counts, file
counts, seconds — was matched against the backlog and the audits:

```text
docstrings audited                                8
distinctive figures in them                      33
absent from docs/backlog/scenarios + docs/audits  0
```

So no §3.6 append was needed. Had one been, it would have gone into the
named task file first.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| S1 | twelve lines added to a docstring | `..._budgeted_docstring_fits[dev_tier_drift]` |
| S2 | an entry put back for a file that now fits | `..._grandfathered_docstring_only_shrinks` |
| S3 | an entry naming a file that does not exist | 2 clauses |

### Two guards that caught the cut, both correctly

`test_the_graph_is_derived_not_guessed.py::test_it_says_what_it_reads`
holds the literal sentence "not a JavaScript parser" in
`dev_js_deps.py` — `UX-340`'s Out of Scope, where the reader is rather
than only in the task file. My rewrite capitalised it away, and the
guard reddened. Restored verbatim.

`UX-449`'s skip census went red on `got empty parameter set for (rel,
recorded)`: emptying `GRANDFATHERED` left a parametrized clause with
nothing to parametrise, and pytest skips it with a reason the census
has never seen. Declaring that reason known would be a fudge over a
guard with nothing left to guard, so the clause loops instead — S2 and
S3 prove it still discriminates.

### Deviation from the Required Fix

`dev_tier_drift.py`'s in-body comments are reduced, not brought to any
stated ratio: the filing's `206 / 46` was measured over a narrower span
than this file's whole body, and there is no cap on comment lines to
size against. The docstring cap is the one this item was asked to meet,
and it is met for all eight. Test-file docstrings stay out of scope.

```text
make test  5766 passed, 27 skipped in 336.17s;  make lint clean
```
