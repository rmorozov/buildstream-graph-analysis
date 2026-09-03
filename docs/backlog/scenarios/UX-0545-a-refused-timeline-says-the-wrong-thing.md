# UX-545: a refused timeline tells the reader the snapshot has no build log

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-530` (which fixed the degraded case), `UX-194` (the dead-control rule), `UX-321` (an absence is a fact to publish) | **Found by:** `UX-530`, whose scope was the degradation | **Serves:** anyone whose capture is over a ceiling | **Topic:** viewer

## Motivation

`UX-530` gave the export a ladder: over a ceiling it carries
`--planes 1` and the handoff sentence says so. When even that does not
fit, `export()` refuses and writes `timeline_omitted` into `run.json`.

**Nothing in `bga/viewer/` reads `timeline_omitted`.** The page falls
through to the no-timeline branch, and `renderQuestions` tells the
reader:

```text
This snapshot carries no build log, so there is no timeline to open
here. `bga snapshot -- bst build TARGET` captures both planes.
```

which is false twice over: the snapshot has a build log, and capturing
again will produce the same refusal. It is `UX-321`'s rule inverted —
an absence published and then described as a different absence.

`UX-530` fixed the *degraded* case only, and said so.

## Required Fix

The refusal reaches the reader in its own words: what was refused, the
ceiling it hit, and what a reader can actually do about it — the
recipe `export()` already writes, rather than the capture advice.
`timeline_degraded` and `timeline_omitted` are two states and the page
distinguishes them.

## Out of Scope

- Raising the ceiling, or adding a grain — `UX-430` and `UX-530`'s own
  deviation cover those.

## Acceptance Test

A capture over both rungs, served and exported: the page names the
refusal, and a mutation that drops the reader reddens rather than
falling back to the no-build-log sentence.

## Outcome (round 81, 2026-09-03) — 🟢 Done

**Premise:** held — nothing in `bga/viewer/` read `timeline_omitted`; the discriminator turned out to be `timeline_recipe`.

### The gap, measured

```text
$ git grep -n timeline_omitted ca825c3 -- bga/viewer/ | wc -l
0
$ git grep -n timeline_degraded ca825c3 -- bga/viewer/
bga/viewer/app.js:829:        timelineDegraded: run.timeline_degraded,
bga/viewer/perfetto_page.js:78:      timelineDegraded: run?.timeline_degraded,
```

One of the two states was read. The other reached `renderQuestions`'s
no-timeline branch, which says `This snapshot carries no build log`.

### After

A two-plane capture (`pages.two_plane_snapshot`) with
`TRACE_TRACK_BUDGET` one track under what `--planes 1` draws, so both
rungs refuse — exported, then booted:

```text
tracks: whole=7  --planes 1=4  ceiling 3
has_timeline           False
timeline_recipe        bga view /tmp/.../20260821T120000Z --perfetto
questions lead, data-omitted="refused":
  This file has the build log and refused the timeline: the whole
  timeline - the timeline draws 7 tracks, over this export's 3-track
  ceiling - Perfetto draws a row per track, and the byte size (0.0 MiB)
  is well inside its own ceiling; `--planes 1`, which leaves Plane 2's
  process lanes out - the timeline draws 4 tracks, over this export's
  3-track ceiling - ... . Capturing again refuses the same way; run
  `bga view /tmp/.../20260821T120000Z --perfetto` instead. That serves
  this run and hands the timeline to Perfetto over a deep link, ...
  The queries below are what to ask it there.
served run.json, same capture:
  has_timeline True, no timeline_omitted, no timeline_recipe
```

**The discriminator is `timeline_recipe`, not `timeline_omitted`.**
`export()` writes the recipe only for a timeline it rendered and
refused (`if omitted and trace is not None`); a run that captured no
Plane 2 gets `timeline_omitted` from `plane2.absence()` and no recipe,
and keeps the capture sentence. The refusal is export-only: `UX-296`
keeps the render off the server's startup path, so a served reader of
the same capture still has its timeline.

`renderQuestions` takes `timelineOmitted`/`timelineRecipe`; `app.js`
passes them. `perfetto_page.js` is untouched — it reads the served
`run.json`, which carries neither key.

### Close, measured

```text
$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_a_refused_timeline_says_it_was_refused.py -q
6 passed in 2.51s          (single process; medium tier)
$ make test-touching
12 file(s) selected · 311 passed, 3 skipped in 12.85s
$ pytest <26 files naming renderQuestions/questions.js> -n auto
510 passed, 12 skipped in 47.50s
```

### Mutations verified red and reverted (3)

| # | mutation | what reddened | count |
|---|---|---|---|
| M1 | the reader deleted (`const refused = null`) | the refused page says "carries no build log" again | 1 red, 5 green |
| M2 | `app.js` stops passing the two keys | the same sentence — the guard reads the wiring, not the renderer | 1 red, 5 green |
| M3 | discriminate on `timelineOmitted` instead | the no-Plane-2 run is told it was refused | 2 red, 4 green |

No guard of this item failed to discriminate; M3 is the direction that
proves it.

### Deviation from the Required Fix

None. The ceiling is unchanged and no grain was added; `export()` was
not edited at all — the refusal it already published now has a reader.
