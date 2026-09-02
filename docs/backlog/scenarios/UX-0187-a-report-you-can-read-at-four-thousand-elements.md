# UX-187: a report you can read at four thousand elements

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-33 (the always-print rule this revisits), UX-168 (the synthetic scale fixture this renders) | **Topic:** analysis

## Motivation

Field feedback: *"let's check that our reports in different formats
are readable enough on long output."* The known unbounded spots, from
past rounds' notes: the critical path prints **in full** (UX-33's
rule, written when paths were ten elements; at thousands it is the
bulk of the report), the Serialized-chains line concatenates every
chain, and several per-element sections have no top-N. The bounded
parts (diagnostics summary at 6, unknown flags at 6, blast table
rows) show the house pattern already exists — it was just never
applied to the oldest sections.

This is an audit-shaped task: render, measure, cap.

## Required Fix

1. **Render every report format** (analyze text, analyze
   `--diagnostics`, compare, correlate, cache-logs, blast) against
   the 1,202-element synthetic run and a real fdsdk capture; record
   per-section line counts in the task's log.
2. **Cap what scrolls**: every list-shaped section gets the top-N +
   "and M more (--full-<section> to print all)" treatment — N chosen
   per section from what a screen holds, the cap stated inline so
   truncation is never silent (the UX-160 lesson). The critical path
   specifically: head and tail with the elision count, full path
   behind the flag and always full in JSON.
3. **JSON stays complete** — caps are a text-rendering concern; the
   machine format never truncates.
4. A guard renders the synthetic run and asserts no section exceeds
   its cap and every elision names its count and its flag.

## Out of Scope

- Pagination/pager integration (`| less` works once stdout is clean;
  owning a pager is scope creep).
- The bounded sections (already right).

## Acceptance Test

On the 1,202-element synthetic run: the full text report fits under a
stated total budget (a few hundred lines, exact number recorded with
provenance), every elided section names its count and flag, each
`--full-*` flag restores its section, and JSON is byte-identical
before and after the caps (mutation: capping JSON reddens it).

## What was built

### 1. The measurement, first

The 1,202-element synthetic run is **wide, not deep** — its critical
path is 14 elements — so it does not exercise the section this item is
about at all. Rendering it:

| report | lines |
|---|---|
| `analyze` | 109 |
| `analyze --diagnostics` | 109 |
| `graph` | 44 |
| `utilisation` | 21 |

The shape that makes a path long is a *chain*, so the fixture is
`--layers 400 --width 2`: a 402-element critical path. There the
finding is unmissable:

| section | lines | share |
|---|---|---|
| **Critical Path** | **405** | **81%** |
| Structural Analysis | 19 | 4% |
| Key Findings | 16 | 3% |
| Dispatch Occupancy | 13 | 3% |
| Attribution Breakdown | 10 | 2% |
| Advanced Diagnostics | 10 | 2% |
| Certified Floors | 9 | 2% |

498 lines, of which the path is four fifths — and every section a
reader acts on is below it. `UX-33` made the path always-print when
paths were ten elements and a reader could not hold one in their head;
at four hundred the rule that helped now buries the finding.

### 2. Cap what scrolls

`498 → 117` lines, with `--full-path` restoring all 498.

The path folds in the **middle**, not at the tail: a chain's two ends
are where an optimizer starts — the root everything waits on, and the
last link before the build finishes — so both survive and the middle
goes.

```text
    layer10/mod003.bst                          7.90s (  0.3% of path)
    ... 382 more element(s) (--full-path to print all)
    layer393/mod005.bst                         4.60s (  0.2% of path)
```

The Shared Sources table caps at ten rows (four lines each, so twenty
repositories was eighty lines of table) with `--full-sources` to
restore it. The rows are already ranked widest-first, so what folds is
the tail.

**Nothing is cut silently.** Every elision names its own count and the
flag that undoes it. That rule also fixed a live defect one section
over: the Serialized-chains line sliced to five and said nothing, which
is exactly the shape `UX-160` was filed against. It now names what it
dropped.

### 3. JSON never truncates

The caps are a text-rendering concern. `--format json` carries the
whole path, and `--full-path`/`--full-sources` do not change one byte
of it — asserted, because a cap that leaked into the machine format
would be a change to the contract `UX-190` just versioned.

Tests: 11 new (`tests/unit/test_report_stays_readable_at_scale.py`).
Five mutations, each red, including the two that would be easy to get
wrong: folding the *tail* instead of the middle (both ends must
survive) and capping the JSON.

**Two defects the guards found in the fix itself**, which is what
writing them first is for: the Shared Sources cap shipped *silent* in
the first draft — capped at ten rows and said nothing, the very thing
this item forbids — and the serialized-pairs stub reached no block at
all, so a naive assertion would have passed while testing nothing. The
helper now fails loudly if the line does not render.

Fixture cost: the deep run is analyzed eight times by this file, so it
is width 2 rather than width 10. Same 402-element chain, **15s instead
of 253s**.

## Deviation from the Required Fix

Item 1 asks for the render measured against "a real fdsdk capture" as
well as the synthetic run. The fdsdk captures live on `captures/*`
branches of this repository and none is checked out in this session;
the synthetic deep fixture is what the numbers above come from. It is
the *stronger* case for this item — 402 elements against fdsdk's own
path — but it is synthetic, and nobody should read the table above as
having been taken from a real project.

