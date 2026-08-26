# UX-313: the record list is the floor that is left

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-297 (the pass this sits on top of) | **Serves:** R1 | **Topic:** capture

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
