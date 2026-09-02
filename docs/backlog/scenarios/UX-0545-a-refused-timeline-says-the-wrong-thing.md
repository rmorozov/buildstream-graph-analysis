# UX-545: a refused timeline tells the reader the snapshot has no build log

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-530` (which fixed the degraded case), `UX-194` (the dead-control rule), `UX-321` (an absence is a fact to publish) | **Found by:** `UX-530`, whose scope was the degradation | **Serves:** anyone whose capture is over a ceiling | **Topic:** viewer

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
