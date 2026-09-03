# UX-555: `--no-trace` tells a two-plane run it kept no Plane 2 log

**Priority:** Low | **Status:** 🟢 Fixed & Verified | **Depends on:** `UX-545` (which fixed the branch beside this one) | **Found by:** `UX-545`'s track, one branch over from its own fix | **Serves:** anyone who exports without a timeline on purpose | **Topic:** viewer

## Motivation

`tools/bga_view.py:1203` is the fallback for "no timeline in this
file". It reads `plane2.absence() or "this run kept no raw Plane 2
log, so there is no timeline to carry"`.

For a complete two-plane run exported with `with_trace=False`,
`plane2.absence()` returns `None` — there is no absence to describe —
and the `or` swallows it into a sentence that is simply false: the run
*did* keep a raw Plane 2 log, and the reason there is no timeline is
that the caller asked for none.

This is `UX-545`'s shape exactly, one branch over: an absence
described as a *different* absence. `UX-545` fixed the refusal path,
where two states shared one key; this is the third state sharing it.

## Out of Scope

- `UX-545`'s refusal path, which is closed: this row is only the
  `with_trace=False` branch beside it.
- Making `--no-trace` reachable from more callers: declined, because
  the sentence is wrong whether or not a caller reaches it, and
  widening the surface is a separate question from telling the truth
  on it.

## Required Fix

The three states are distinguished, and each says its own reason:
the caller asked for no trace, the run has no Plane 2 to draw, and
the timeline was refused for its size. A mutation swapping any two
must redden.

## Acceptance Test

`export(run, path, with_trace=False)` over
`tests/fixtures/with_timeline` — a run that demonstrably *has* a raw
Plane 2 log — and the published sentence names the flag rather than
the run.

## Note on reachability

No caller in `bga/` passes `with_trace=False` today, so the sentence
is unreachable outside tests. That is why this is Low and not Medium,
and it is also why it survived: `UX-326`'s axis reads what the tool
prints, and nothing prints this.

## Outcome (round 81, 2026-09-03) — 🟢 Done

### The gap, measured

A run with **both** halves of Plane 2 beside it — report and raw log —
exported with `with_trace=False`:

```text
sibling_plane2 : True
sibling_raw_log: True
absence()      : None

has_timeline    : False
timeline_omitted: 'this run kept no raw Plane 2 log, so there is no timeline to carry'
```

`absence()` is `None` because there is no absence, so the `or` reached
its right-hand side and told a run holding a raw log that it kept none.

### After

Three states, three sentences, one export each:

```text
(a) asked for no trace, run HAS Plane 2 (absence() is None):
    This file was exported with `with_trace=False`, so no timeline was
    rendered for it. That is the flag and not the run: whatever Plane 2
    this capture kept is untouched beside it, and exporting again
    without the flag carries the timeline.

(b) no Plane 2 to draw, with_trace=True:
    Plane 2 was not captured for this run, so there is no per-process
    detail. `bga snapshot -- bst build TARGET` captures both planes.

(c) refused for size, with_trace=True:
    the whole timeline - the timeline draws 7 tracks, over this
    export's 1-track ceiling - Perfetto draws a row per track, ...
```

(b) is unchanged — `bga/plane2.py` still owns the absences, so the
terminal and the page cannot drift (`UX-329`). (c) is `UX-545`'s, also
untouched. Only the fallback split.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | the pre-fix `or` line restored | `test_the_flag_is_named_not_the_run`, 1 red / 3 green |
| A2 | (a) and (b) swapped | that clause **and** `..._gets_the_absence`, 2 red / 2 green |
| A3 | (a) given (c)'s words | `test_the_flag_is_named_not_the_run`, 1 red / 3 green |
| A4 | (b) given (c)'s words | `..._gets_the_absence`, 1 red / 3 green |
| A5 | (a) collapsed onto `NOT_CAPTURED` exactly | that clause **and** `..._are_three_different_sentences`, 2 red / 2 green |

`test_the_three_are_three_different_sentences` did **not** redden on
A1–A4 and is worth the note: a *swap* keeps three distinct strings, so
pairwise-distinctness is blind to it. It discriminates only on a true
collapse (A5). The clause that carries A1 is the one naming the flag —
distinctness alone would have shipped this defect.

### Deviation from the Required Fix

None to the fix. **The Acceptance Test's fixture premise is wrong**:
`tests/fixtures/with_timeline` is Plane 1 only —
`plane2.absence()` there returns `NOT_CAPTURED`, not `None` — so
exporting it with `with_trace=False` never reached the false sentence.
The guard builds the state instead (`pages.two_plane_snapshot` plus a
`plane2.json`) and asserts `sibling_raw_log() is not None` and
`absence() is None` before testing, so a fixture that stops reproducing
the defect fails loudly rather than passing vacuously.

A fourth state exists and got its own sentence rather than a false one:
`with_trace=True`, Plane 2 present, nothing rendered
(`TIMELINE_DID_NOT_RENDER`).

```text
$ make test-touching
96 file(s) selected · 1762 passed, 44 skipped in 113.16s (0:01:53)
$ make lint
All checks passed!
```
