# UX-689: the architecture document moves into the area pages, one track at a time

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-688 (the pages), UX-569 (the prose its guards do not read), UX-568 (the spec's Part→guard index) | **Serves:** the reader pricing a change; the session restructuring without losing a sentence | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

```text
docs/spec/specification.md     3,051 lines · 16 guards · frozen outside Part 32 by rule · Part→guard index landed (UX-568)
docs/design/architecture.md    1,648 lines · 19 guards · guarded skeletons exact, prose drifting (UX-569, round 82)
```

The brief proposes restructuring both. The spec should not be
restructured: it is layered — the Part 32 registry, the Part→guard
index, the advisory-Parts note — and its five edge decisions are
taken (`UX-564`..`UX-568`); a rewrite would re-open them for no
reader. The architecture document is the one whose *prose* has
drifted, and the area pages (`UX-688`) are where each chapter's prose
belongs — beside the derived tables that keep it honest.

## Required Fix

A planned round of tracks, not a rewrite: one area per track under
the `decompose` skill's merge rules; each track moves the chapter's
mechanism prose into the area page, leaves a one-paragraph pointer in
`architecture.md`, and keeps the guarded skeletons (CLI table,
contract inventory, viewer table, verification log) where the guards
read them. The acceptance figure is the round-82 review's method run
before and after: no sentence lost, every link resolving, the 19
guards green throughout. `docs/backlog/areas/*.md` are generated views
`write_area_pages` rewrites whole on every `--check --write` (`UX-688`),
so a hand edit there is undone by the next run; each track's area page
is therefore a new **hand-written** `docs/design/areas/<area>.md`, and
the generated backlog page gets one derived `Mechanism:` line pointing
at it when that file exists.

## Out of Scope

- The specification's body — layered, not moved (§3.12 stands).
- `directions.md` — the history of the arguments; it is read as
  history.

## Acceptance Test

After the last track: `architecture.md` under 400 lines of pointers
and skeletons; every former chapter's sentences found in exactly one
area page; the 19 guards green; the link guard green.

## Outcome

### Track 1: the viewer axis (round 111, 2026-09-08)

**Decision:** `docs/backlog/areas/*.md` are generated (`write_area_pages`,
`UX-688`) and a hand edit is undone by `--check --write`; the
destination is hand-written `docs/design/areas/bga-viewer.md`, and
the generated page gets a derived `Mechanism:` line when it exists.

### The gap → the close, measured

```text
$ python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q
435 passed        # before and after, unchanged
$ wc -l docs/design/architecture.md
1648 → 1529        # chapter 235 → 81 kept, 163 moved to the new page
```

56 of 56 sentence-chunks land in the new page or the kept skeleton.
The Verification Log's newest entry is re-dated and re-anchored in
this commit (`test_the_verification_log_is_true.py`), same commit as
the substantive edit, per the log's own "the same commit" rule.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | Mechanism line always emitted | `..._carries_nothing` |
| A2 | Mechanism line never emitted | `..._carries_the_line` |

Not a committed guard: a scratch diff script (each chapter unit
flattened, checked as a substring of the new page or architecture.md)
dropped 50/56 → 49/56, naming the sentence deleted from a scratch copy.

### The series closed (round 114, 2026-09-12)

Six moves, one item each after the first (`UX-806`, `UX-807`, `UX-810`,
`UX-815`, `UX-816`), into five hand-written pages under
`docs/design/areas/`: `bga-viewer`, `tools-native_trace`, `bga-replay`,
`tools` (two chapters), `bga` (four chapters). Every move's sentence
diff was empty and every one's verifier reproduced it; the 21 guard
files read 437 before and after each.

```text
$ awk '/^## Verification Log/{exit} {n++} END{print n}' docs/design/architecture.md
1044   # at 2749a34a~1, before the series
490    # after UX-816
```

**Deviation.** The Acceptance Test's "under 400 lines of pointers and
skeletons" is not met: 490 stay, and what stays is what the Required
Fix said stays — the CLI table, the package structure, the two
contract inventories, the real-extensions table (its guard reads the
whole table under its own heading, so the chapter stayed whole rather
than move a pointer beside a copy), the frame and six pointers. The
figure was a guess at the skeletons' size; the skeletons are the 490.
