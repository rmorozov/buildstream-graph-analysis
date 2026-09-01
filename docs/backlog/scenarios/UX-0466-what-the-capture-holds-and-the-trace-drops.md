# UX-466: nothing measures which captured field reaches a Perfetto slice

**Priority:** Medium | **Status:** 🟡 In Progress (stages 1-2 done) | **Depends on:** stage 3 needs `UX-465` · independent of `UX-464` | **Found by:** round 72, thread 1 of the audit — whether the maximum information Perfetto and `bga view` could analyse is captured, and whether the mapping to Perfetto's format is right | **Serves:** the reader who opens the trace expecting a field the capture holds and finds the track empty | **Topic:** contracts

## Motivation

Three planes write records; one trace is emitted from them. Nothing in
the suite reads both ends and says which captured field reaches a
slice, an arg, a counter or a track, and which is held and dropped.
`UX-356` did this for the *element join* — every field reaches a
reader — and found the gap worth a row. The same question has never
been asked of the trace.

Without that instrument, thread 1 can only be answered by reading
source and forming an impression, which is fixing guide §5's first
shape: a text scan that cannot tell what the code emits from what it
mentions. This round has already made that mistake twice.

## Required Fix

Three stages, in order. Stage 1 is the instrument every later claim
rests on.

1. **The field census.** `tools/dev_trace_coverage.py`: read a
   capture's own records — Plane 1's parsed log, Plane 2's hook
   records, Plane 3's spine records — and the trace emitted from it,
   and report per field whether it reaches the trace and as what
   (slice name, arg key, counter series, track, flow). Reads emitted
   artifacts on both sides, never source text. Run it over both
   committed fixtures and paste the table.
2. **The other direction.** Which of Perfetto's own carriers the
   emitted trace uses at all — counters, flows, async slices, instant
   events, process/thread descriptors, args — and which it does not,
   against the fields stage 1 reports as held-but-dropped. A field we
   hold and a carrier we do not use is a mapping gap; a field we do
   not hold is a capture gap, and they get different rows.
3. **What the planes could capture and do not.** Needs a real build to
   answer honestly, so it needs `UX-465`. Deferred until then rather
   than guessed.

Stages 1 and 2 land together; stage 3 is a separate commit.

## Out of Scope

- Adding any field to any plane. This item measures; what it finds
  gets filed.
- The viewer's rendering of the trace — `UX-467` asks whether the
  conclusions are sound, this one asks whether the data arrives.
- The Perfetto query library. `UX-368` and round 69 covered the
  queries; the question here is what the queries have to work with.

## Acceptance Test

```bash
python3 tools/dev_trace_coverage.py tests/fixtures/with_timeline
```

pasted, with a line per plane naming fields held, fields emitted, and
fields dropped, and every dropped field either filed as a row or
declared with a reason in the tool itself — `UX-376`'s rule, that a
census names what it could not assess.

## Outcome

**Round 72 · 2026-09-01 · Status: 🟡 Stages 1-2 done, stage 3 open**

Stages 1 and 2 landed. Stage 3 — what the planes could capture and do
not — still needs `UX-465`, and this round's own measurement is the
sharpest argument yet for why.

### Stage 1: the field census

`tools/dev_trace_coverage.py` reads a capture's JSON and the bytes
`bga timeline` writes, and matches **values**, not names. It never
opens a Python source file for the name of anything, which is the
failure it exists to avoid.

```text
$ python3 tools/dev_trace_coverage.py tests/fixtures/with_timeline
capture: tests/fixtures/with_timeline

Plane 1: 4 reached, 3 dropped, 50 unassessable
    DROPPED   graph.elements[].cache_key  (0/11 value(s) in the trace)
    DROPPED   run-context.pipeline_overhead[].phase  (0/4 value(s) in the trace)
    DROPPED   trace.spans[].task_key  (0/11 value(s) in the trace)
    reached   graph.dependencies[].predecessor  (10/10 value(s) in the trace)
    reached   graph.dependencies[].successor  (10/10 value(s) in the trace)
    reached   graph.elements[].element_kind  (3/3 value(s) in the trace)
    reached   graph.elements[].uid  (11/11 value(s) in the trace)
```

`task_key` is the declared composite case — the trace carries the uid
as a slice name and the rest elsewhere, so no whole task_key appears.
The other two are real: **the element's cache key and the pipeline
overhead's phase names reach no carrier at all.**

### Stage 2: the carriers

```text
    used    category           a tag a viewer can filter slices by
    UNUSED  counter            a numeric series over time (TYPE_COUNTER)
    UNUSED  counter-unit       the unit a counter series is measured in
    used    debug-annotation   a key/value pair hanging off one slice
    used    flow               an arrow from one slice to another
    used    instant            a named point in time
    used    process-track      a row grouped under a process
    used    slice              a named interval on a track
    used    thread-track       a row grouped under a thread
    used    track              a named row
```

### The headline, and it is a population result

```text
$ python3 tools/dev_trace_coverage.py --carriers
(a clone) 1 capture(s) can draw a timeline, 6 cannot
  cannot: tests/fixtures/ample_capacity    no build.log: an imported run directory, not a snapshot
  cannot: tests/fixtures/macro_micro       no build.log: an imported run directory, not a snapshot
  cannot: tests/fixtures/one_source_many_elements no build.log: ...
  cannot: tests/fixtures/same_build_twice_cold no build.log: ...
  cannot: tests/fixtures/same_build_twice_incremental no build.log: ...
  cannot: tests/fixtures/shared_base_wide  no build.log: ...
  Plane 2: no capture that can draw a timeline carries its records, so
           nothing measures what it maps to
  carriers no capture exercised: counter, counter-unit
```

One of seven committed captures can draw a timeline at all, and it
carries no Plane 2 report. `macro_micro` has the Plane 2 report and no
log to draw from; `with_timeline` has the log and no Plane 2 report.
**So on a clone nothing measures what Plane 2 maps to, and the counter
path — `UX-310`'s whole subject — ships exercised by nothing in the
repository.**

It is a clone-side fact, not a tool-side one. On a machine that has
built the examples:

```text
$ python3 tools/dev_trace_coverage.py --carriers --local
(this machine) 15 capture(s) can draw a timeline, 6 cannot
```

with no missing-plane line and no unexercised carrier — every carrier
is used by some real capture, and Plane 2's fields are assessed. That
is exactly `UX-459`'s shape one level over, and exactly why stage 3
waits for `UX-465`.

For the record, Plane 2 measured on a real two-plane capture
(`examples/06`'s snapshot, an incremental run, which is why Plane 1's
fractions are low):

```text
Plane 1: 3 reached, 9 dropped, 33 unassessable
Plane 2: 2 reached, 1 dropped, 44 unassessable
    used    counter / counter-unit;   UNUSED  flow
```

No single capture exercises every carrier: this one has counters and
no flows, `with_timeline` has flows and no counters.

### What it declares rather than guesses

Four limits, all in the module docstring: numeric fields (the trace
rebases timestamps, so a match would mean nothing), single-valued
fields, composite fields the trace decomposes, and field numbers taken
from the emitter's own module. `UX-376`'s rule.

### Mutations applied

| # | Mutation | Went red |
|---|---|---|
| N1 | `decode` returns an empty vocabulary | `..._vocabulary_is_not_empty`, `..._more_than_one_carrier` |
| N2 | the annotation-name table is not merged in | `..._holds_names_from_more_than_one_carrier` |
| N2b | the category table is not merged in | the same clause |
| N3 | `_is_map` back to type-homogeneity alone | all three map/record clauses |
| N4 | `assess` stops excluding numbers | `..._numeric_field_is_unassessable` |
| N5 | flow detection removed | `..._carriers_it_reports_are_the_ones_in_the_bytes`, `..._two_carriers_are_exercised_by_nothing` |
| N6 | a capture that cannot draw one is counted as if it could | `..._names_the_captures_it_could_not_draw` |

### A defect the guard found in the instrument, and a clause that did not discriminate

- **`_is_map` collapsed records.** Its first version called a dict a
  map when its values were type-homogeneous. `{"start_us": 0,
  "end_us": 9}` passes that, so `wall_clock`'s schema was collapsed
  into data and the census reported seven Plane 1 drops that were
  really three. The guard's first run caught it. Fixed by requiring a
  key that no Python identifier could hold, which is a **spelling
  heuristic** and is declared as one, with its mirror failure mode
  (`{"fetch": ..., "build": ...}` reads as a record) pinned by a clause
  of its own.
- **`test_the_vocabulary_holds_names_from_more_than_one_carrier` did
  not discriminate.** It asserted a *shape* — lowercase, an
  underscore, no spaces — and N2 left it green, because slice names
  satisfy that shape too. Rewritten to name one string that exists in
  exactly one carrier and nowhere else, per carrier: a slice name
  (`app.bst [...]`), a category (`bst-builder`), an annotation key
  (`on_critical_path`). N2 and N2b then both redden it.

### Deviation from the Required Fix

Stage 3 is not done and the item stays open for it. Two of the Required
Fix's carriers were not separable in the emitted bytes and are folded
into the ten `CARRIERS` entries rather than listed apart: async and
nested slices are both `TYPE_SLICE_BEGIN` on a track, so "the trace
uses async slices" is not a question these bytes can answer.

### Known follow-up: the drift gate will name this file once

`tests/unit/test_the_trace_census_reads_both_ends.py` is new, measured
at 4.9s single-process, and added to `MEDIUM` in `tests/tiers.py`. It
is **not** in `tests/ci_reference.json`, whose 386 entries were
recorded before it existed, so the first CI run over this branch will
report it as *not in the reference at all* — the same thing that
happened to `test_a_candidate_is_confirmed_alone.py` in round 71.

Deliberately not hand-patched: the reference's own note says a value
comes from a CI run's `tier-reference` job divided by that run's shift,
and inventing one locally is the practice `UX-418` and `UX-447` exist
to forbid. The fix is one line once CI has named the number.

### Tier and suite

```text
$ make test
5536 passed, 28 skipped, 2 warnings in 296.88s (0:04:56)
$ make lint
All checks passed!
```
