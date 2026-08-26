# UX-313: the record list is the floor that is left

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-297 (the pass this sits on top of) | **Serves:** R1 | **Topic:** capture

## Motivation

`UX-297` closed with parsing and pairing as one pass, and the
measurement then named what remains. On a generated 200,000-process
trace, inside one extraction:

```text
                        before     after
events parsed          247.4 MB      -      (400,000 dicts, gone)
records paired         249.0 MB   221.1 MB
folded, records freed   46.1 MB    42.8 MB
peak (end to end)      288.3 MB   259.5 MB
```

185.8 MB of that 221.1 is the record list. It exists for two reasons,
both real: `merge_record_streams` joins the two streams whole, and the
start order every downstream reader has always seen is sorted from it.
So extraction is `O(processes)` — a fifth of what `O(events)` cost, and
still not the `O(elements)` the item's title implied.

Windowing it is not obviously safe, which is why this is filed rather
than done. The pairing pass yields a record when its **END** arrives,
and a process alive for the whole build displaces its record
arbitrarily far from its start position; a reorder buffer sized for
that is the record list again. The join has the same question from the
other side: the spine's record for a process and the hook's are
microseconds apart in wall time, but nothing measured says how far
apart they are in *record-stream* order on a real dual-stream capture.

## Required Fix

Measure first, on a real spine+hook capture: the record-stream
displacement between a record's yield position and its start-sorted
position, and between a spine record and its hook partner. If both are
bounded by something a build can be argued about — rather than by its
longest process — a bounded reorder window and a windowed join replace
the list, and extraction becomes `O(concurrency)`. If they are not, the
finding is that the record list is the floor, and this item closes by
saying so in `UX-297`'s progress note instead of by shipping code.

## Out of Scope

- The pairing pass itself (`UX-297`, landed).
- Anything that changes the order a reader sees. The start order is the
  contract; a window that reorders output is not a memory win.

## Acceptance Test

Either: the two displacements are measured and stated, a window sized
from them lands, extraction's peak on the 200,000-process trace drops
below the record list's own 185.8 MB, the report digest is unchanged,
and a mutation that unbounds the window reddens the ceiling. Or: the
measurement says the displacement is unbounded, the numbers are written
into `UX-297`, and this item closes as answered.

## Outcome (round 45, 2026-08-26) — 🟢 Done, answered rather than built

The Required Fix offered two endings. This is the second: **the
displacements are not bounded by anything a build can be argued about,
so the record list is the floor**, and the numbers are written into
`UX-297`'s progress note as that branch asks.

Nothing about the extraction changed. What landed is the measurement
and a guard over it.

### The bound is real — that is what makes this a finding

Before concluding it is unreachable, it is worth showing it exists.
Synthetic traces, concurrency held at 8, the build getting longer:

```text
 processes  records  window  % of list
       500      500      10       2.0%
     1,000    1,000      12       1.2%
     2,000    2,000      12       0.6%
     4,000    4,000      12       0.3%
     8,000    8,000      13       0.2%
```

Flat. And with the build held at 4,000 processes, concurrency rising:

```text
 concurrency  records  window  % of list
           1    4,000       0       0.0%
           2    4,000       5       0.1%
           4    4,000       7       0.2%
           8    4,000      12       0.3%
          16    4,000      21       0.5%
          32    4,000      42       1.1%
          64    4,000      75       1.9%
```

Linear in concurrency, at roughly 1.2x. That is exactly the
`O(concurrency)` extraction the item hoped for.

### One process that never closes takes the whole list

```text
 long-lived  records  window  % of list
          0    4,000      12       0.3%
          1    4,001   3,992      99.8%
          2    4,002   3,992      99.8%
          4    4,004   3,992      99.7%
          8    4,008   3,992      99.6%
```

One is enough. More do not make it worse, because it is already the
list.

### Displacement 1, on this repository's real capture

`examples/06`, 813 records, 9 elements:

```text
records                              813
  paired (an END was observed)       663
  open   (no END ever arrived)       150
records out of start order           811 of 813

window over paired records only       83
window over open records             663
p50 73   p90 135   p99 151   max 153      (paired)
```

The filing guessed that "a process alive for the whole build displaces
its record arbitrarily far". The mechanism turned out to be sharper
than that, and structural rather than incidental: **every one of the
nine elements leaves open records**, 16 to 21 each, because BuildStream
tears the sandbox down around the element's shell and the hook never
sees it exit. They are all `no-observed-exit`, all `sh -c` wrappers and
`cmake -E cmake_echo_color` steps.

`stream_records` cannot know an open record exists until the stream
ends. So a buffer emitting in start order must hold every record that
starts after the earliest open one — and the earliest open one sits at
**start-sorted position 0**, the first process of the build:

```text
earliest open record, in start order   position 0 of 813
records a buffer would have to hold    813  (100.0% of the list)
```

### Displacement 2, on a dual-stream capture made for the question

The committed capture is hook-only, so one was made: `--trace-spine=on`
over a copy of `examples/06` renamed so its cache keys were cold. 813
hook records beside 813 spine records, 1,626 in all.

```text
displacement 1 (this capture)     window 1,474 of 1,626   90.7%

displacement 2 - spine record to its hook partner, in stream order
  spine records                     813
  matched to a hook partner         811
  spine-only (no partner)             2
  p50  1    p90  736    p99  1,346    max  1,414   (87.0%)
```

**The median is 1** — a spine record's hook partner is normally the very
next record, which is why a windowed join looks so plausible from the
p50. The tail is the same open records: the spine observes the exit
through `PTRACE_EVENT_EXIT`, the hook does not, so one half of the pair
is yielded in place and the other is flushed at the end of the stream.

Both displacements are bounded by the build, not by its concurrency.
The disjunction in the Required Fix resolves to its second branch.

### The guard

`tests/unit/test_the_record_list_is_the_floor.py`, ten clauses in two
classes. The first holds the half that is good news — the window does
not grow with the build, does grow with concurrency, and one long-lived
process takes essentially the whole list. The second holds the real
capture: every element leaves an open record, the earliest is at
position 0, and the paired records alone *would* have been windowable.

That last clause is the point of the file. It is not a guard against a
regression; it is a guard against a later round re-deriving this from
scratch, and it goes red if a capture ever stops leaving open records —
which is the one change that would make the question worth reopening.

### Mutations verified red and reverted (3), and two rejected

| # | mutation | reddened |
|---|---|---|
| U1 | a 200-deep **LIFO** buffer in `stream_records`, so the yield order is reordered | 8 of 10 — both window families and the paired-window clause |
| U2 | drop open records from the pass entirely | every-element-leaves-one, and the earliest-open clause |
| U3 | the synthetic long-lived process closes *inside* the build instead of outliving it | the one-long-lived-process clause |

**Two rejected rather than counted**, both instructive:

*A 200-deep FIFO buffer* — hold every record back 200 places before
yielding it. All ten clauses stayed green, and correctly so: a FIFO
delay shifts every yield index by the same amount and leaves the
*relative* order untouched, so the displacement each clause measures is
unchanged. It looks like it should perturb a window and it cannot. The
same buffer made LIFO is U1, and that reddens eight clauses — the
difference between the two is exactly the property the guard is about,
which is why the pair is worth recording rather than just the one that
worked.

*Yielding the open records start-sorted among themselves* — intended
for the earliest-open clause, and it cannot reach it. That clause
measures a record's position in **start** order, which is a fact about
the capture rather than about the order `stream_records` emits;
no change to yield order can move it. It is falsified by U2, which
removes the records themselves. Recorded because the mistake is easy
to repeat: a clause that reads sorted order is not falsifiable by
mutating the emitter.

### Deviation from the Required Fix

- The Required Fix's first branch (a bounded reorder window, a windowed
  join, extraction's peak below 185.8 MB, a mutation that unbounds the
  window) is **not built**, because the measurement it was conditional
  on came back negative. That is the branch the filing itself provided.
- The 200,000-process re-measurement named in the acceptance test was
  not run: it measures the peak of a design that is not being built.
  The displacement measurements are what decide the question, and they
  were taken on real captures rather than on a generated one.
