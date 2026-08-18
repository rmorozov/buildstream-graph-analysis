# UX-104: the memory half of capacity advice is still an exercise for the reader

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-63 (measured per-task memory), UX-21 (the memory guard's threshold), UX-83 (the Plane 2 plumbing into analyze)

Direction 3, item 5 — see
[`design/directions.md`](../../design/directions.md).

## Motivation

The report's standing memory line is: *"its largest single process
peaked at 1902 MB resident - multiply by however many elements build
concurrently before raising `builders`"*. That multiplication is the
tool's job, and it has every input: per-element peak RSS (UX-63), the
host's memory (run context), the concurrency the run actually reached
(Plane 1), and — since UX-83 — a channel for Plane 2 data into
`analyze`'s capacity advice. Leaving it to the reader has a failure
mode in each direction: raise `builders` into swap (the worst build
slowdown there is, and one no CPU-side signal predicts), or leave
memory headroom unused out of caution.

## Required Fix

1. **The computed envelope**, in the capacity block whenever Plane 2
   memory data is present: from the run's measured per-element peaks,
   the memory cost of the observed concurrency and of each higher
   `builders` value — conservatively (concurrent peaks summed as if
   coincident, and say so), against host memory minus a reserve.
   Rendered as the one sentence the reader currently has to derive:
   *"4 builders of this shape peak at ~7.6 GB of 15.6 GB; 8 would not
   fit"*. This makes the UX-83 arbitration memory-aware too: "more
   builders" advice must clear both the CPU and the memory check.
2. **The trend/compare hook:** compare notes when the candidate's
   memory envelope grew materially (new or changed elements raising
   peak RSS), the same additive-JSON pattern as the marginal gate —
   a note, not a gate, until a noise band for RSS exists.
3. Sweep's knee annotation (UX-83) gains the memory ceiling: a knee
   above the memory-feasible capacity says which constraint binds.

## Out of Scope

- Swap detection at capture time (a different, host-level measurement).
- A hard gate on memory (no noise model yet; same discipline as
  everywhere else).
- Modeling memory *inside* an element's own `-j` (Plane 2 measures the
  element's whole tree; per-job attribution is not needed for the
  builders question).

## Acceptance Test

On the retained fdsdk dual capture: the capacity block prints the
envelope computed from the real 1902 MB peak and the run's real
concurrency, and the number matches the hand calculation the README
currently performs in prose. On `examples/06` (small peaks): the
envelope says memory does not bind before CPU does. Synthetic test: a
run whose measured peaks make `builders+1` exceed host memory gets
capacity advice that refuses the raise on memory grounds even where
CPU has headroom.

---

## Fix Implemented

All three items, plus the field the arithmetic needed and nobody had
recorded.

### The denominator, recorded at capture time

`UX-21` scoped memory auto-detection out because *"real per-task memory
measurement has no source in this ingestion pipeline"*. `UX-63` gave it
one, so the reason no longer held: `host_memory_mb` is now read from
`/proc/meminfo` by both run-context producers and carried in the run
directory. Deliberately not `os.sysconf`, which reports the host's pages
even inside a container with a lower limit — the same class of mistake
`host_cpu_count` avoids by preferring `sched_getaffinity`. Kept separate
from `memory_budget_mb`, which is what the operator *intends* to use: a
budget is a policy, this is a fact, and the operator's still wins where
set.

### 1. The computed envelope

`compute_memory_envelope` sums the N largest measured per-element peaks
for each N, against the host's RAM. Two decisions:

- **Conservative, and it says so.** As if the N heaviest elements built
  at once *and* peaked at the same instant. `compute_peak_memory`'s own
  note is emphatic that per-process peaks must not be summed; the same
  caution applies one level up, which is exactly why this is an upper
  bound. For "is it safe to raise `--builders`?", an upper bound is the
  useful direction to be wrong in.
- **No invented reserve.** A margin for the OS and page cache would be a
  threshold picked from nothing. `fits` is a strict comparison, and the
  payload says plainly that headroom below 100% is not the same as safe.

The projection runs to the measured population and no further — N
builders can only be N elements building at once. An earlier version
stopped two past the observed count, which is a number chosen from
nothing, and it hid a real ceiling three builders away
(`first_builders_that_does_not_fit` came back `None` on a run that
genuinely stops fitting at 5). Caught by a test written from the
acceptance rather than from the implementation.

Rendered as the sentence the README used to ask the reader to derive,
in `analyze` (finding id `memory-envelope`) and at the head of
`correlate`:

```text
Memory envelope: 4 builders of this shape peak at ~11.3 GB of 11.7 GB (97%);
5 would not fit
```

and on `examples/06` as measured, where the answer is the opposite and
just as useful:

```text
Memory envelope: 4 builders of this shape peak at ~0.6 GB of 15.7 GB (4%);
6 would still fit, so memory is not what binds first here
```

**The arbitration is memory-aware.** The RESOURCE WAIT hint checks
memory before anything else: an answer that clears the CPU check and
blows the memory one is advice to build into swap, which is the worst
build slowdown there is and one no CPU-side signal predicts. The
refusal is scoped to the *next* builder — a ceiling three away is a fact
for the envelope line, not a reason to refuse a raise that would fit.

The per-element `peak-memory` row no longer ends *"multiply by however
many elements build concurrently"*. Where the capture recorded the
host's RAM it points at the envelope above; where it did not, it keeps
the old instruction **and says why** it cannot do the arithmetic itself.

### 2. The compare note

`bga compare --baseline-plane2 A.json --candidate-plane2 B.json`:

```text
Memory envelope grew: 0.6 GB -> 11.3 GB (+10.7 GB, +1791%) against 11.7 GB of RAM
```

Two flags rather than one, because reusing the candidate's report for
both would compare a run against itself and always report no growth —
a check that passes because it cannot fail. A note, never a gate: peak
RSS has no measured noise band, and this codebase does not gate on a
threshold it has not measured.

### 3. The sweep knee

```text
Knee point (PROCESS): capacity 2 (diminishing returns beyond this)
  Memory: capacity 2 needs ~5.7 GB of 11.7 GB (48%) - memory is not what binds
  at the knee.
```

and, where it does bind, `MEMORY BINDS BEFORE THE KNEE`. The knee is a
replay-model answer and the replay model knows nothing about memory any
more than it knows about CPU (`UX-09`/`UX-14`) — a knee above the
memory-feasible capacity is a recommendation to swap.

### The acceptance, run

- **`examples/06`, real dual capture:** *"4 builders of this shape peak
  at ~0.6 GB of 15.7 GB (4%); 6 would still fit, so memory is not what
  binds first here"* — memory does not bind before CPU does.
- **Synthetic overflow:** the same capture with per-element peaks at
  2.9 GB against a 12 GB host produces *"4 builders … peak at ~11.3 GB
  of 11.7 GB (97%); 5 would not fit"*, a `high`-severity finding, and a
  capacity hint that refuses the raise on memory grounds.
- **fdsdk:** the retained captures predate `host_memory_mb`, so the
  envelope cannot be computed against them — the capture recorded the
  figure in `capture-context.txt` and never in the run directory. Every
  capture taken from now on carries it. Stated rather than worked
  around: back-filling the number from a sibling file would be reading a
  denominator the analysis contract does not have.

Tests: 11 new in `tests/unit/test_memory_envelope.py`. Suite: 1299 →
1310.

## Verification Log

Done 2026-08-18. The `examples/06` figures are a real dual-plane capture
taken for this task; the overflow case is that capture's own run
directory with the peaks and host memory rewritten, which is what the
acceptance asks for.
