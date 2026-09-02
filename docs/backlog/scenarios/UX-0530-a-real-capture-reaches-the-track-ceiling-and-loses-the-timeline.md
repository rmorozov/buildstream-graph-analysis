# UX-530: a real capture reaches the track ceiling, and the timeline is dropped whole

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-430 (the ceiling), UX-406 (the spine double-count that halves the room) | **Serves:** anyone capturing a C++ project with a few hundred processes per element | **Topic:** capture

## Motivation

```text
ex06 cold capture, Plane 2 records ×10 (offset pids): 8,130 processes on 11 elements
trace tracks       842 → 8,159          TRACE_TRACK_BUDGET 8,000  (bga_view.py:696)
export             timeline refused whole; recipe written           (bga_view.py:1033-1063)
```

About 740 processes per element is a real C++ shape, and the spine
(`UX-406`) counts every process twice, so the ceiling is met at half
that. `export()` refuses the whole timeline rather than trying the
degradations its own recipe names (`--planes 1`, a coarser grain).

## Required Fix

`export()` degrades before it refuses: `--planes 1`, then the
process grain the recipe names, then refusal — each step stated in
the page's handoff sentence. And the ceiling counts *processes*,
not slices, so the spine's second slice does not halve the room.

## Out of Scope

- Raising the ceiling — `UX-430` measured why it is where it is.

## Acceptance Test

The 8,130-process capture exports with a Plane-1 timeline and a
sentence saying why; mutation: remove the degradation step — the
export refuses again.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

`export()` rendered once and compared twice, and the recipe it printed
beside the refusal named the flag it had not tried:

```text
$ git show HEAD:tools/bga_view.py | sed -n '/elif (trace_tracks/,+5p'
        elif (trace_tracks or 0) > TRACE_TRACK_BUDGET:
            omitted = (f"the timeline draws {trace_tracks:,} tracks, over "
                       ...
$ git show HEAD:tools/bga_view.py | grep -c 'trace_with_planes(run, planes'
0
```

### After

`_degradation_steps()` reads `bga_timeline.PLANE_CHOICES` rather than
restating it, and `export()` renders each step until one fits. On a
capture of this item's own shape — 8,140 processes, four elements,
built by the new guard's `_snapshot` and exported for real:

```text
processes            8140 on 4 elements
both planes          tracks   8152  slices   8146
--planes 1           tracks      7  slices      6
TRACE_TRACK_BUDGET   8000
export               419155 B in 3.6 s
has_timeline         True   planes ['1']
timeline_degraded    The whole timeline did not fit - the timeline draws
                     8,152 tracks, over this export's 8,000-track ceiling
                     - Perfetto draws a row per track, and the byte size
                     (0.2 MiB) is well inside its own ceiling - so this
                     file carries `--planes 1`, which leaves Plane 2's
                     process lanes out: 7 tracks.
```

`renderQuestions` prefixes that to the handoff sentence, so a narrowed
page cannot be mistaken for a Plane 1 capture. Refusal is what is left
when every step is still over, and it names each — the whole timeline's
number and the narrowed one, joined by a semicolon.

**The ceiling already counts processes.** The item's premise — "the
spine counts every process twice, so the ceiling is met at half that" —
is **falsified** for the timeline. `_write_trackevent` opens one track
per `(element, pid)` *after* `merge_record_streams`, so the second
record is not a second row. Measured on the same capture recorded once
and twice:

```text
spine only   tracks 6014  slices 4810
spine+hook   tracks 6014  slices 4810
```

`UX-406` landed that join; nothing here had to. What was missing was a
guard, and `test_the_second_record_does_not_halve_the_room` is it — it
reddens when the join is removed. Export +220 B, all page.

### Mutations verified red and reverted (5)

| # | mutation | red |
|---|---|---|
| N1 | the ladder has only the whole timeline (the item's own) | 4 |
| N2 | the export narrows and does not say so | 2 |
| N3 | `UX-406`'s join removed, the spine's second record drawn | 1 |
| N4 | the handoff sentence ignores the step that was taken | 1 |
| N5 | every carried timeline claims it was narrowed | 2 |

### Deviation

The Required Fix names a third step, "the coarser process grain the
recipe names". The recipe names `--planes 1` and `--only-element`, and
`--only-element` needs the element a reader is investigating — an export
that picks one would hide the rest of a build silently. `bga timeline`
offers no other grain (`PLANE_CHOICES` is `both`/`1`), so the ladder is
two steps and reads the renderer's own list: a third grain added there
becomes a step here with no edit, and
`test_the_steps_are_the_renderers_own_choices` reddens if it does not.
The recipe now says which flag an export cannot take for you.
