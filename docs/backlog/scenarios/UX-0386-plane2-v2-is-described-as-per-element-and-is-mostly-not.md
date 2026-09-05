# UX-386: `plane2/v2` is described as per-element, and mostly is not

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-297 (plane2/v2), UX-378 (two more run-level blocks), UX-381 (the layout that made the shape readable) | **Serves:** anyone opening a `plane2.json` after reading what it is | **Topic:** contracts | **Area:** bga

## Motivation

Review 6, checklist item 2: every published contract has a home, and
the review asks whether the *prose* around it is still true.

Both documents that describe `plane2/v2` say the same thing:

```text
docs/design/architecture.md
  | `plane2/v2` | Plane 2's report: the per-element reductions a
                  capture computed, and nothing else (`UX-297`) |

docs/README.md
  | `plane2/v2` | `bga capture`, at `plane2.json` beside a run - what
                  Plane 2 measured, as per-element reductions (`UX-297`) |
```

Measured on `tests/fixtures/macro_micro/plane2.json`, keying each
top-level block by whether it is a map over element uids:

```text
top-level keys                    24
keyed by element                   3   binary_cost, by_element, opens_captured
run-level                         21   by_binary, configure_phase, cpu_time,
                                       declared_vs_used, element_attribution,
                                       invocation_correlation, matched_count,
                                       max_concurrency, open_count,
                                       open_records_note, peak_memory,
                                       per_element_parallelism, process_count,
                                       redundant_operations,
                                       redundant_operations_coverage,
                                       spine_policy, static_binary_disclaimer,
                                       static_census, stream_coverage,
                                       wall_span_s, wrapped_command_exit_code
```

Three of twenty-four. The sentence has been wrong since `UX-297`
retired the record list and kept everything else — the "and nothing
else" was about the **per-process records**, which is what that item
removed, and it reads as a claim about the *shape* of what is left.

`UX-378` and `UX-379` added two more run-level blocks
(`process_outcomes`, `resource_pressure`), so the ratio moved further
in the round that found this.

The cost is not cosmetic. A reader who wants the host's peak memory,
the build's process count, or whether the spine ran will not open a
file the documentation says holds per-element reductions — and those
are the three questions a Plane 2 report is most often opened for.

## Required Fix

One sentence per document, true of what the file holds. The natural
line, and the one the file's own shape already draws: **`plane2/v2` is
a Plane 2 report about one build — run-level measurements, with the
per-element reductions among them.** Both halves named, since a reader
comes for one or the other.

`UX-297`'s clause is worth keeping and worth attaching to what it was
about: the per-process record list is gone, which is a statement about
what was removed rather than about what the document is.

## Falsification

A guard that reads the fixture's `plane2.json`, partitions its
top-level keys into element-keyed and run-level, and asserts that any
prose describing the contract names both classes. Today the partition
is 3/21 and both sentences name one class.

The other direction, so the fix is not "call it a bag of things": the
element-keyed blocks are still named as such, because
`bga correlate`'s whole join is built on them.

## Out of Scope

- Reorganising the document. The shape is fine and a consumer pins it;
  this is about the sentence that describes it.
- `analyze/v4`'s own element/run split. `UX-382` declared that one, and
  whether `plane2/v2` should follow the same rule is a real question
  and a later one — its Out of Scope says so.

## Outcome (round 62, 2026-08-29) — 🟢 Done

### The gap, measured

Re-measured on the committed fixture rather than taken from the filing,
and unchanged: **3 of 24** top-level blocks are keyed by element uid —
`binary_cost`, `by_element`, `opens_captured` — and 21 answer for the
whole run.

### After

Both halves named, in every document that describes the contract:

```text
architecture.md   "Plane 2's report about one build: run-level
                   measurements, with the per-element reductions among
                   them - 21 of its 24 top-level blocks answer for the
                   whole run and 3 are keyed by element uid..."

docs/README.md    the same claim with the same numbers, plus what a
                  reader after the host's peak memory, the build's
                  process count or whether the spine ran is looking for

bga/schemas.py    `plane2_coverage.source`, which said the same wrong
                  thing behind `UX-346`'s `?` door
```

`UX-297`'s clause is kept and attached to what it was about — the
per-process record list — rather than reading as a claim about the
shape of what is left. A clause holds it there: citing `UX-297` without
saying it is the record list that went reddens.

**The filing named two documents and there were three.** The third is
`bga/schemas.py`'s own sentence, reached by a reader who opens the `?`
door instead of a document, and it carried the identical wrong claim.
Found by looking for the sentence rather than for the files.

### Falsification

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | the architecture row restored to the old sentence | 3 of 16 |
| M2 | `docs/README.md` restored to the old sentence | 2 of 16 |
| M3 | the fix over-corrects and drops the per-element half | 1 of 16 |
| M4 | `UX-297` cited without saying what it retired | 1 of 16 |
| M5 | the schema's own sentence keeps the old claim | 2 of 16 |
| M6 | the live row names the retired id instead | 5 of 16 |

Baseline: 16 passed. M3 is the direction that makes this a correction
rather than a swap: a sentence naming only the run-level half sends the
reader after `bga correlate`'s join somewhere else, which is the same
defect from the other side.

### Deviation from the Required Fix

- None. The Required Fix's proposed sentence is the one used; the third
  instance is an addition to its scope rather than a departure from it.
