# UX-583: the round history is typed, and three rounds are missing from it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the reader tracing a decision to the round that made it | **Topic:** docs

## Motivation

```text
docs/audits/round-81.md exists          directions.md: 0 mentions
rows 25 and 26                          link to round-24.md; no round-25/26 files exist
planted-defect-walk-round-72.md, guard-census-round-64.md   no row
Verification Log (directions.md:1444)   link text "optimization-walkthrough-06.md" for case-study-06-macro-micro.md
docs/README.md audits list              maintained by hand, same omissions (rounds 75-79 added by round 79 in passing)
```

Corrected in place on the base of round 83 (`8481f99`, 2026-09-03).
Row 1 is falsified: round 82 typed its own row **and** round 81's, so
`directions.md` mentions both. The count still reads three, with a
different membership — `round-83.md` (written this round),
`guard-census-round-64.md`, `planted-defect-walk-round-72.md` — and
the walkthrough-06 link text is at `:5` as well as `:1446`. Rows 3, 4
and 5 hold.

The table is the one place the arguments and the rounds meet, and it
is hand-typed by whichever session remembers.

## Required Fix

A guard that holds the round-history table and the `docs/README.md`
audits list to `docs/audits/`: every `round-*.md` and named walk has
a row that links to it, every row links to a file that exists, and
link text matches the file; the missing rows written (the sibling's
rounds are summarised from their own first paragraphs).

## Out of Scope

- Rewriting existing rows — they are the record of what each round claimed; only missing rows and broken links change.

## Acceptance Test

Mutation: add `round-99.md` — red; point a row at a missing file —
red.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** falsified — three is still the count, but not the filed
three. Rounds 81 and 82 both have rows already (round 82 typed them);
the three with none are `round-83.md`, `guard-census-round-64.md`,
`planted-defect-walk-round-72.md`. Motivation corrected in place.

Counted on the base (`8481f99`) before anything was written:

```text
$ git ls-files docs/audits | wc -l                                    50
$ git ls-files docs/audits | grep -c 'round-[0-9]'                    45
    less docs/audits/data/round-75-track-cost.md, an appendix         44
$ sed -n '/^## Round history$/,/^## Verification Log$/p' \
    docs/design/directions.md | grep -c '^| '                         45
    one header, so                                                    44 rows
    of which links into ../audits/                                    43
$ grep -c '(audits/' docs/README.md                                   45
```

The gap, from the new guard against the unedited documents:

```text
$ python3 -m pytest tests/unit/test_the_round_history_names_every_audit.py -q
E  AssertionError: no row in the round-history table of
E   docs/design/directions.md links to: docs/audits/guard-census-round-64.md,
E   docs/audits/planted-defect-walk-round-72.md, docs/audits/round-83.md
E  AssertionError: docs/README.md links to no:
E   docs/audits/guard-census-round-64.md, docs/audits/round-83.md
E  AssertionError: docs/design/directions.md: text names
E   optimization-walkthrough-06.md, target is case-study-06-macro-micro.md;
E   text '25' opens round-24.md; text '26' opens round-24.md; text names
E   optimization-walkthrough-06.md, target is case-study-06-macro-micro.md
3 failed, 3 passed in 0.10s
```

Written: three rows — `64 · the guard census`, `72 · the planted-defect
walk`, `83` — each summarised from that document's own first paragraph;
two `docs/README.md` links; rows 25 and 26 unlinked with their text kept
verbatim, because rounds 25 and 26 have no audit file and never did
(`round-27.md:127` records the sections being folded into this table);
both `optimization-walkthrough-06.md` link texts (`:5`, `:1446`) made
their target's name. Table 44 rows → 47, README 45 links → 47.

| mutation | what reddened; each reverted from a `/tmp` copy, 6 green after | run |
|---|---|---|
| stage `docs/audits/round-99.md`, no links (acceptance 1) | both coverage clauses, naming `round-99.md` | 2 failed, 4 passed |
| the same, plus a row linking `../audits/round-99.md`, text `99` | the README clause alone | 1 failed, 5 passed |
| delete `round-99.md`, keep the row (acceptance 2) | `..._points_at_a_file_that_exists`, naming that row's target | 1 failed, 5 passed |
| round 83's row text `83` → `84`, target unmoved | text clause \[directions.md\]: *text '84' opens round-83.md* | 1 failed, 5 passed |
| README census text → `guard-census-round-46.md` | text clause \[README.md\]: *target is guard-census-round-64.md* | 1 failed, 5 passed |
| the guard's own `round-\d+` → `round-\d{9}` | `test_the_scan_is_not_vacuous`: *only 0 round documents* | 1 failed, 5 passed |

**Vacuity.** Row 6 is the clause's own falsification: with the
enumeration returning nothing the other five clauses are green, so the
scan asserts ≥ 40 round documents, ≥ 40 table links and ≥ 40 README
audits links before it agrees to anything.

**No guard here failed to discriminate**, but one hazard was designed
around: `_tracked()` is `lru_cache`d, so a mutation that changes the
index mid-process would be read from a snapshot taken before it
(`UX-573` was bitten by exactly this). Every mutation above ran in a
fresh interpreter.

**Verification.**

```text
$ make test-touching
43 file(s) selected · 858 passed, 4 skipped in 22.01s
$ make lint
All checks passed!
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_round_history_names_every_audit.py -q
6 passed in 0.05s
```

**Deviation.** The full suite is the orchestrator's; this track ran the
selector only. `tests/tiers.py` and `tests/ci_reference.json` are
untouched, so the new file's tier and CI second are the merge's to add —
0.05 s single-process. Status stays 🔴 for the same reason.
