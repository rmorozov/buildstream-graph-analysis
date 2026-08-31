# UX-430: the trace budget counts bytes, and Perfetto spends tracks

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 69, an outside walk of `bga snapshot` → `bga view` → Perfetto, after a field report of the UI freezing on a real build | **Serves:** anyone who clicks "Open timeline in Perfetto" on a build big enough to be worth analysing | **Topic:** viewer

## Motivation

`tools/bga_view.py:601` holds the only bound the handoff has:

```python
TRACE_BUDGET_B = 4 * 1024 * 1024
```

It gates two things — whether the export inlines the trace, and whether
the served page uses `postMessage` or the `?url=` deep link.

Measured on a 1,202-element run with both planes, 14,424 traced
processes (`tools/bga_timeline.py`, trackevent format):

```text
                      measured        bound
trace bytes            795,371    4,194,304    19.0% of it
slices                  14,446            -
tracks                  15,650            -    nothing bounds this
counters                 2,001            -
```

**The trace is a fifth of its byte budget and carries more tracks than
slices.** `_write_trackevent` opens one process track per element and
one thread track per traced pid (`bga_timeline.py:1181`), so track
count rises with the process population, which is exactly what a build
worth tracing has a lot of.

Bytes are what the budget counts. Tracks are what the viewer spends —
Perfetto draws a row per track, and the reported freeze is a drawing
cost, not a transfer cost. The one number bga has cannot see the
quantity that decides whether the handoff opens at all.

**This is the fixing guide's §5 arriving on the design side**, where it
is easy to miss: the byte figure is real, cheaply obtained and honestly
reported. It is simply a measurement of a different thing. A capture
can pass this budget with room to spare and still be unopenable.

## Required Fix

- **Count the unit the consumer spends.** Bound the track count
  alongside the byte count, measured at the size `gen-synthetic` exists
  to probe rather than at eleven elements (§3f).
- **Give the reader the choice the size forces.** `bga timeline` and
  `bga view` expose no way to ask for less: `with_trace=False` is a
  Python kwarg with one caller in a test and no CLI surface, and there
  is no Plane-1-only or per-element option at all. A capture that
  exceeds the track bound should be able to hand over Plane 1 alone, or
  one element's Plane 2, rather than all or nothing.
- **Say which bound was hit, in the units of that bound.** A refusal
  reading "4 MiB" when the problem was 15,650 tracks sends the reader
  to compress something that is not the cost.

## Out of Scope

- **Whether Perfetto could draw 15,650 tracks faster** — that is
  Perfetto's business and this item does not file a bug there.
- **Lowering `TRACE_BUDGET_B`**: the byte bound is doing its own job
  correctly (transfer and inlining) and this item adds a second bound
  rather than retuning the first.
- **Merging pids onto one track per element** — a plausible fix that
  changes what the trace *means*, and it needs its own item because
  overlapping slices on one track is a different reading (`UX-188`
  chose the present shape deliberately).

## Acceptance Test

```bash
bga gen-synthetic /tmp/scale --seed 1
bga timeline /tmp/snapshot -o /tmp/two.pftrace     # both planes present
```

The emitter's result names a track count and the bound it was measured
against; a capture over the bound is refused, or narrowed, with a
message naming tracks. A mutation that doubles the per-pid track count
while leaving bytes unchanged must redden the guard — a guard that only
reads bytes passes that mutation, which is the defect this item is.

## Outcome (round 70, 2026-08-30) — 🟢 Done

### The two quantities, measured side by side

`tests/pages.py::scale_two_plane_snapshot` is new and is what made this
measurable: the seeded scale run (`bga gen-synthetic --seed 1`, 1,202
elements) wrapped as a **snapshot**, with a wrapped BuildStream log and
a raw Plane 2 log generated from its own `graph.json`, twelve processes
an element.

```console
$ bga timeline <snapshot> -o both.pftrace           # and the two narrowings
                  tracks   slices     bytes
  both planes     16,832   15,628   486,173
  --planes 1       1,205    1,204    72,079
  --only-element   1,219    1,216    73,017
```

**More tracks than slices, at 11.6% of `TRACE_BUDGET_B`.** Scaled from
that measurement the byte bound first bites at roughly 145,000 tracks —
nine times the population a field report already described as freezing
the UI. The one number the handoff had could not see the quantity that
decides whether it opens.

### What was added

**A bound in the consumer's unit.** `TRACE_TRACK_BUDGET` in
`tools/bga_view.py`, beside `TRACE_BUDGET_B`, carrying the table above
in its docstring. The export checks both and refuses in the unit that
was exceeded:

```text
the timeline draws 16,832 tracks, over this export's 8,000-track ceiling -
Perfetto draws a row per track, and the byte size (0.5 MiB) is well inside
its own ceiling
```

**The narrowing the size forces.** `bga timeline --planes 1` leaves the
process lanes out; `--only-element ELEMENT` keeps one element's. The
filter is applied to the **record list** every Plane 2 number folds
from, so the lanes, the exec-chain arrows and the concurrency counter
narrow together — a filter anywhere else would show one element's lanes
under the whole build's counter, and
`test_one_element_narrows_lanes_flows_and_counter_together` is the
clause that says so.

**The offer, where the size is reported.** `describe()` names both flags
after the track count, rather than leaving a reader to find them in
`--help` after the file will not open — and a run that is *already*
narrowed says what it narrowed to instead:

```text
  15628 slices, 3500 flows, 2000 counters on 16832 tracks. Open it with Perfetto …
  `--planes 1` leaves the process lanes out and `--only-element` keeps one
  element's, if this is more rows than Perfetto will draw.
```

The export's `timeline_recipe` note names them too, so the refusal and
the remedy arrive together.

### The number, and what is honest about it

`TRACE_TRACK_BUDGET = 8_000` is **one sample**, and its docstring says
so. Everything around it is measured; the threshold itself is sized
under the 16,832 that fixture draws because that is the population the
field report came from, and this repository has measured nothing about
what Perfetto costs per track. Its job is to make the reader choose —
`--planes 1` is a fourteenfold reduction on the same run — not to
predict a viewer nobody here has instrumented. **`UX-445`** is filed to
replace it with a curve.

### The guard, and the mutation the item named

`tests/unit/test_the_handoff_counts_what_perfetto_spends.py`, eleven
clauses. The one that decides asserts the **increment** Plane 2 adds:

```python
whole["tracks"] - plane1["tracks"] == elements + pids + 1
```

An increment rather than a total, so it states what the process
population costs without pinning what Plane 1 happens to open — and so
the item's named mutation reddens it.

```text
T1 a second track per pid, bytes unchanged   red: track_count_is_the_population,
                                                  one_element_narrows_together
T2 --planes 1 does not drop Plane 2          red: track_count_is_the_population,
                                                  plane_one_only_drops_the_lanes,
                                                  it_says_the_raw_log_is_still_there,
                                                  one_element_narrows_together
T3 --only-element filters nothing            red: one_element_narrows_together
T4 the narrowing is never offered            red: narrowing_is_offered_where_size_is
T5 the track bound is not checked            red: too_many_tracks_is_refused_in_tracks,
                                                  refusal_names_the_flags
T6 the track refusal talks about bytes       red: too_many_tracks_is_refused_in_tracks
T7 the byte bound is dropped                 red: too_many_bytes_is_refused_in_bytes
T8 the recipe names no narrowing flag        red: refusal_names_the_flags
```

**T1 is the item's acceptance mutation** — a second `thread_track` per
pid, which moves the byte figure by a rounding error. A guard reading
only bytes passes it; this one goes red on the first run.

All eight discriminated on the first pass.

### Deviation from the Required Fix

None. Two additions the work forced:

- **`scale_two_plane_snapshot`**, because no fixture in the tree could
  render a timeline at the size §3f requires the bound to be measured
  at. `two_plane_snapshot` is one element and one pid.
- **`UX-445`**, so the single-sample threshold is a filed question
  rather than a number in a docstring — which is where the last one hid
  (`UX-420`).

`docs/guides/cli.md` gains the two flags and the table.

### The suite

```console
$ make lint
All checks passed!

$ make test
5378 passed, 26 skipped, 1 warning in 293.89s (0:04:53)
```

The new file is tiered **medium** on landing (4.6s: two `gen-synthetic`
runs and six renders of the 1,202-element snapshot, which is the size
the bound is measured at and therefore not something to shrink).
