# UX-740: a span under the epsilon grid becomes a zero-width segment, and nothing says so

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-692 (the sweep that found it), UX-53 (the single duration definition), UX-110 | **Serves:** anyone whose build has a fast element, and every figure computed from a segment width | **Topic:** analysis | **Shape:** judgement | **Area:** bga

## Motivation

`UX-692`'s seeded sweep found this on its **first generated shapes**,
with no planted mutation — which is what the sweep exists to do. An
element whose duration sits at or under `trace_epsilon_us`'s
quantization grid collapses to a zero-width `EXECUTION_ON_CHAIN`
segment in `bga/normalize/timestamps.py::quantize_timestamp`.

Re-derived here independently of the sweep, on the generator's own
output:

```console
$ python3 -m tools.gen_synthetic_scale_run --layers 3 --width 3 --seed 1 /tmp/synprobe
trace_epsilon_us: 50000
spans at or under the epsilon grid: 2 of 11
   toolchain.bst|BUILD|BUILD|0              dur_us=1
   all.bst|BUILD|BUILD|0                    dur_us=1
```

**It is not a synthetic-data artefact.** The committed fixture that
most of this repository's guards read has it too:

```console
$ # tests/fixtures/macro_micro/run
eps=50000  spans=11  at/under grid=2  min dur=0
```

Two of eleven spans in a real capture are at or under the grid, and
the shortest is **zero**. So every figure derived from a segment's
width — attribution shares, the critical path's composition, anything
dividing by a duration — is computed over segments that silently have
none, on the fixture the suite trusts most.

The sweep's own I10 clause was deliberately scoped to spec Part 34's
literal text ("ordered, contiguous, non-overlapping"), all of which a
zero-width segment satisfies. That is why no existing guard catches
this: the invariant as written is *true*, and the defect lives in what
the invariant does not say.

## Required Fix

The judgement first, because two readings are defensible and they
lead to different code:

- **Quantization should not erase a span that happened.** Floor a
  non-zero duration to one grid unit, so a fast element is short
  rather than absent. Cheap, and it changes every figure computed
  over such elements — which is the point, but it means re-deriving
  the committed fixtures' expected numbers.
- **A zero-width segment is honest, and the defect is silence.**
  Keep the arithmetic and publish the fact: an element whose duration
  is under the resolution the capture can express is *unmeasurable at
  this epsilon*, said in the report rather than rendered as zero.
  `UX-376`'s "the census names what it could not assess" is the
  precedent.

Measure before choosing: how many elements in the committed fixtures
and in a real `examples/06` capture fall under the grid, and what the
attribution shares do under each route. State which and why in the
Outcome. Whichever is taken, a guard must red on a zero-width
`EXECUTION_ON_CHAIN` segment reaching a published figure.

## Out of Scope

- `trace_epsilon_us`'s value. Why the grid is 50 ms is `UX-110`'s
  axis; this row is about what happens to a span below it.
- The synthetic generator's 1 µs endpoint convention. It exposed the
  defect; it did not cause it, as the `macro_micro` measurement above
  shows.

## Acceptance Test

A capture containing an element under the grid produces either a
non-zero floored segment or a stated refusal — not a silent zero.
Mutation: put a sub-grid element in a fixture and confirm the guard
reds before the fix and passes after.
