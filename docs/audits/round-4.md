# Audit round 4

> Moved out of [`docs/design/directions.md`](../design/directions.md) during the round-11 documentation housekeeping. Rounds 7-10 were always separate files; rounds 2-6 had accumulated inside the design doc, which made it an argument about direction *and* a changelog. The text below is unedited apart from heading levels.

## What the fourth round found (2026-08-17)

The round's centre was the **plane seam**, the previous round's own item
1, and it produced a design decision rather than a defect - which is what
that item was: an open product question, not a bug.

### The seam: settled by measurement, built as `UX-51`

The question was whether the planes should become one capture or stay two
with an explicit join. Three measurements decided it before any code was
written:

| question | measured answer |
|---|---|
| would a merged capture add anything? | **no** - `UX-24`'s `run --wrapped-log` already emits both artifacts from one `bst build` |
| does a join key exist, and is it exact? | **yes** - 9 of 9 Plane 2 elements matched Plane 1 UIDs, zero mismatches; the two that did not join run no build commands |
| can the horizons be merged at all? | **no** - `architecture.md`'s standing argument; a "merge" would be a join with a misleading name |

So the contract between the planes is one string, and `bga correlate` is
a third consumer neither plane knows about. The caveats that made this
look intractable - `UX-27`'s `occupancy_ratio`, `UX-36`'s buckets, `I9` -
were never in the way, because a join does not need them reconciled.

The thing worth carrying forward is *why the answer was cheap*: every
piece had been built for another reason (`UX-23` tagged processes to fix
a pid-collision bug; `UX-24` added dual capture for a Chrome Trace view),
and the seam turned out to be one join away rather than one architecture
away. **Before designing across a seam, measure what already crosses it.**

### `examples/07`, and closing an evidence gap I had flagged myself

`UX-46` shipped in round 2 with a caveat in its own doc: every
cross-element dependency in `examples/06` is decorative, so the only
true-negative evidence was `toolchain.bst`, and a detector that flagged
*everything* would have looked identical. Round 4's item 3 was to fix
that, and `examples/07-declared-vs-used-dependencies` does: two elements
with identical declared dependencies, differing only in whether their
source includes the header, correctly separated (`1/5` files opened
versus `0 of 5`).

Worth noting as method: this gap was found by the task's own author, in
the task's own doc, and would have stayed a footnote if the doc had not
been written to say what the evidence *could not* show. A caveat you
write about your own work is only useful if something later reads it.

### The cross-check sweep, re-run

Round 3's sweep is now a standing check. Across five runs - three real
captures, the new dual capture, and the synthetic scale fixture - **40 of
40 quantity pairs agree**, up from 22 of 24 when the sweep first ran. It
costs seconds and it has already caught one serious defect (`UX-50`), so
it is worth re-running whenever a derived quantity is added.
