# UX-740: a span under the epsilon grid becomes a zero-width segment, and nothing says so

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-692 (the sweep that found it), UX-53 (the single duration definition), UX-110 | **Serves:** anyone whose build has a fast element, and every figure computed from a segment width | **Topic:** analysis | **Shape:** judgement | **Area:** bga

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

**Corrected here, before the fix.** Two claims above are wrong, and
both change what the fix is:

- The threshold is **half** the grid, not the grid — and it is a
  threshold on *possibility*, not a rule. Round-to-nearest on the two
  endpoints independently collapses a span iff both land on the same
  grid point, which needs the span to lie wholly inside one rounding
  bucket; under `epsilon/2` is necessary and not sufficient. Measured
  on a three-span synthetic at `epsilon_us=50000`, each span starting
  on a grid multiple:

  ```console
  task                          raw dur  normalized dur_us
  half.bst|BUILD|BUILD|0          24999                  0
  over.bst|BUILD|BUILD|0          25001              50000
  sub.bst|BUILD|BUILD|0               1                  0
  violations: []
  ```

  25 ms of real work reports as zero, and `normalize_trace` returns no
  violation for it.

- **The committed fixtures do not carry the defect.** Their zeros are
  zero in the raw trace, not erased by quantization:

  ```console
  run                       eps  spans  <=eps  ==0      min
  host_cpu/run            50000     11      2    2        0
  macro_micro/run         50000     11      2    2        0
  with_timeline/run       50000     11      2    2        0
  (the other 9 committed run dirs: 0 under grid, min 200,000)
  ```

  The two are `toolchain.bst` (`element_kind: import`) and `all.bst`
  (`element_kind: stack`) — a copy and a no-op, which really did take
  under a millisecond. Those zeros are honest. So no committed
  fixture's expected numbers need re-deriving, and the fix needs a
  case that does not exist in the tree yet.

## Required Fix

**The judgement is taken: route B — keep the arithmetic, publish the
fact.** Route A (floor a non-zero duration to one grid unit) is
rejected on a measurement, not a preference. On the synthetic above,
flooring turns 25,000 µs of real work across two elements into
100,000 µs of reported `execution_on_chain_us`:

```console
as shipped             horizon=   6000000 sum=   6000000 I4=True exec_on_chain=3000000
route A (floored)      horizon=   6000000 sum=   6000000 I4=True exec_on_chain=3100000
```

A 4x overstatement — and `I4` holds under both, because idle absorbs
the difference. No existing invariant would have caught route A. A
grid of 50 ms cannot express 25 ms of work; rounding it to zero
understates by 25 ms, rounding it to 50 ms overstates by the same, and
only one of the two is the documented rule Part 3.2 already carries.

So:

1. Keep `quantize_timestamp` and `normalize_timestamps` exactly as
   they are. Part 3.2's round-half-up rule is not the defect.
2. Detect the erasure where it happens, in
   `bga/normalize/timestamps.py::normalize_timestamps`: a span with
   `finish_us > ts_us` whose quantized width is 0. That is the
   discriminating predicate — it is true for an erased span and false
   for `all.bst`'s honest zero, which the fixture table above shows is
   the only kind in the tree today.
3. Publish it, per element and as a run-level count, through
   `bga/schemas.py`'s analyze contract and `bga/analyzer.py` into the
   report — the element is
   *unmeasurable at this epsilon*, said rather than rendered as zero.
   `UX-376`'s census is the precedent for the vocabulary; there is no
   existing "unmeasurable" term in `bga/` (`grep -rn "unmeasurable"
   bga/` returns one unrelated comment), so this row introduces it.
4. Three things are settled here so the track has nothing to guess:
   the run-level figure is a **count of elements**, not a share; the
   epsilon in force is stated beside it, because "unmeasurable"
   without the resolution is not a statement; and the key names
   follow `bga/schemas.py`'s existing conventions rather than
   inventing a namespace — the track picks them and says which.
5. A guard in `tests/unit/` reds when an erased span reaches a
   published figure with nothing said about it. Build the case; do not
   reuse a committed fixture, which by the table above cannot
   exercise this.

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

## Outcome

**Route B, taken and built.** `bga/normalize/timestamps.py::
spans_below_resolution` names the erased spans;
`bga/analyzer.py::_build_duration_resolution` publishes them;
`bga/report/json.py` and `bga/report/text.py` carry them to the two
readers; `bga/schemas.py` documents the key and puts it in
`ANALYZE_RUN_DEPENDENT_KEYS`, so absence means the run had none.

**The gap measured.** Three spans at `epsilon_us=50000`, each starting
on a grid multiple:

```console
task                          raw dur  normalized dur_us
half.bst|BUILD|BUILD|0          24999                  0
over.bst|BUILD|BUILD|0          25001              50000
sub.bst|BUILD|BUILD|0               1                  0
violations: []
```

**One claim in the Motivation corrected by the guard, not by reading.**
`test_the_boundary_is_half_the_grid`'s first draft placed its spans a
second apart rather than on the grid and did not red: a 24,999 µs span
starting at 2,000,001 µs straddles the bucket boundary at 2,025,000 and
survives. Under half the grid is **necessary and not sufficient** — the
phase decides. So the predicate is run per span and never read off the
duration, and both docstrings say so.

**The close measured.** On the three-span run:

```console
{"epsilon_us": 50000, "element_count": 2,
 "elements": ["half.bst", "sub.bst"], ...}
```

On `tests/fixtures/macro_micro/run`, whose two zero-width spans are
zero in the raw trace: `{}`.

**Mutation table.** Guard `tests/unit/test_a_span_under_the_grid_says_
so.py`, 10 clauses; each mutation applied, run, reverted from a
pristine copy, re-run green.

| mutation | reddened | count |
|---|---|---|
| drop the `finish_us <= ts_us` skip — any zero-width counts | `test_an_honest_zero_is_not_a_finding`, `test_the_predicate_is_not_duration_below_epsilon` | 2 of 10 |
| predicate becomes `dur_us <= epsilon_us` | `test_the_boundary_is_half_the_grid` | 1 of 10 |
| `spans_below_resolution` never called | 7 clauses | 7 of 10 |
| the terminal drops the line | `test_the_disclosure_reaches_the_terminal` | 1 of 10 |
| the document drops the key | `test_the_disclosure_reaches_the_published_document` | 1 of 10 |

The first is the one that matters: it is the guard that would have been
written by reading "a zero-width segment reached a published figure",
and it reds on `macro_micro`'s correct data. The discrimination clause
is what keeps the other nine honest.

**Deviation.** No `examples/06` capture is committed, so the
real-capture half of "measure before choosing" was answered on the 12
committed run dirs instead: 3 carry zero-width spans, all of them
`stack`/`import` elements zero in the raw trace, and none is erased.
The defect is reachable — the synthetic generator produces it on its
first shapes — but no committed fixture exhibits it, so the guard
builds its own case, as the Required Fix directed.
