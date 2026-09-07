# UX-666: a subagent's cost is written down, and its friction with it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-521 (the tokens-by-phase measurement), UX-508 (the process bands) | **Serves:** the round choosing a model and a shape for its next agent | **Topic:** docs | **Shape:** judgement

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

## Outcome (round 103, 2026-09-07) — 🟢 Done

**Premise:** held — "nothing requires the row, and nothing reads the
table" was true of both halves; the friction line, which the row also
asks for, had already landed in all three agent bodies and both skills.

### The gap, measured

```text
$ python3 tools/dev_process_bands.py --runs 12
error: unrecognized arguments: --runs 12
$ python3 tools/dev_track_cost.py --ledger <t> --round 103 ... --append
error: unrecognized arguments: --append
$ git grep -l agent-runs HEAD -- tests/ tools/
tests/unit/test_a_counted_figure_is_derived.py
tests/unit/test_the_ledger_row_is_the_transcript_s.py
tools/dev_track_cost.py
```

Three readers, none of which reads a *run*: two check the ledger's own
count sentence and one formats a row to stdout. The row reached the
file by hand, and the count sentence with it.

### After

```text
$ python3 tools/dev_process_bands.py --runs 12
37 run(s) in the ledger; the last 12 by kind and model.
implementer   sonnet        11           190k       35.1 m
verifier      sonnet         1            64k        8.4 m
cut or re-run: 2 of 37 (round 82, round 82)
$ python3 tools/dev_track_cost.py --ledger <t> ... --append
appended to docs/audits/agent-runs.md; the summary now says thirty-eight
```

`--append` writes the row and re-derives the count sentence, so the
figure under the table is never typed. `--runs` prices the last N runs
by agent kind and model — the column `CLAUDE.md`'s advisory is
measured against — and draws no band, for the reason the other bands
do not.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | `## Agents` dropped from `round-91.md` | the round-document clause, 1 |
| A2 | the run filter loosened to `cells[0] == "round"` | 3, incl. the real ledger's row count |
| A3 | `append_row` inserts at the table's top | the row-order clause, 1 |
| A4 | `append_row` leaves the count sentence alone | the re-derivation clause, 1 |
| A5 | an unfilled token cell reads as `0.0` | the unknown-is-not-zero clause, 1 |
| A6 | `round-93`'s ledger rows deleted | the ledger-prices-it clause, 1 |

`round-95.md` reddened A1's clause on the first clean run: it priced
its eight runs under `## The tracks, priced`, a heading nothing could
find. Renamed, columns kept — its `shape` column is what `UX-708` wants.

### Deviation from the Required Fix

The third bullet's guard is written over **the round documents that
exist**, not over the rounds that happened, because no record says
which rounds happened: `docs/audits/round-*.md` stops at 95, README's
newest heading is the 94th, the ledger prices 100/102/103, and nine
commits name rounds 90..102. Rounds 96–98 never existed; 99–102 are
real and undocumented. A guard over a glob cannot see a round that
skipped its document, so the register is filed as `UX-744` and this
guard reads the glob until it exists. `--runs N` is a window over the
most recent N rows, not "the twelve round-90 rows" the Acceptance Test
names — the ledger held twelve when that was written and holds 37 now.

```text
$ make test
7620 passed, 82 skipped, 1 warning in 673.54s (0:11:13)
$ make lint
All checks passed!
clean: 300 finding(s) match .../tests/quality_baseline.json
```
