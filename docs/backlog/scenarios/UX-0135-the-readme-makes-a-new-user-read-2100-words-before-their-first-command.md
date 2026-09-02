# UX-135: the README makes a new user read 2,100 words before their first command

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-125/UX-126 (the flow it should lead with — both done) | **Topic:** docs

Docs polish round (round 14): simple, concise, consistent. The full
fresh-eyes read this and its siblings (`UX-136`..`UX-141`) come from is
in [`round-14`](../../audits/round-14.md).

## Motivation

Journey A's reader — a developer with a slow build — types their first
command on *their* project ~2,100 words / 196 lines into `README.md`.
The path there: intro → install → **three fixture demos with pasted
output** (lines 20-92) → a 60-line showcase of someone else's
freedesktop-sdk build (94-155) → a report-literacy course ("Reading the
report", 157-191) → finally "Use it on your real project" at line 193,
where the two-command flow this repo just built (`bga doctor` →
`bga snapshot`) sits in fifth position. The README teaches demonstration
before instruction, three times over, and its "New here?" pointer sells
the walkthrough as "the full end-to-end walkthrough" — which sounds
longer, not shorter, than what a new user wants.

Cut targets measured (420 → ~230 lines plausible without losing any
evidence): the `--large` fixture output and the thousand-element
synthetic add no user-facing concept the first fixture didn't; the
showcase earns half its length (keep the Key Findings block and the
three takeaway bullets); "Reading the report" is reference material
that belongs beside the reference; the Plane 2/3 sections re-prove what
the walkthrough's steps already show with the same captures.

## Required Fix

Reorder and cut, moving nothing that is not already stated elsewhere
(and moving it there where it is not):

1. New order: what it is → install → 30-second fixture → **doctor +
   snapshot on your project** → one halved real-output showcase → CI
   pointer → plane deep-dive pointers → docs/dev/license.
2. Cuts per the measured list above; "Reading the report" merges into
   the walkthrough/reference (whichever `UX-137` makes canonical for
   each bullet).
3. The line-10 plane sentence (90 words, two anchors) becomes one
   clause plus a link to docs/README's plane table.

## Out of Scope

- The cross-doc deduplication and terminology passes
  (`UX-137`/`UX-138`) — this task is one file's order and length.

## Acceptance Test

`wc -l README.md` ≤ 250; "Use it on your real project" is the section
immediately after the quick start; every command block the README still
carries passes the docs-commands test; nothing deleted here is absent
from the corpus (each cut's content grep-locatable in the file the cut
points to); `make lint-docs` and the link test pass.


---

## What was built

`README.md`: **420 → 245 lines** *(`UX-154`: this log first said 430; `git show 0acaff5:README.md | wc -l` is 420. The reduction is 175 lines, not 185.)*, reordered to what it is → install →
30-second fixture → **doctor + snapshot on your project** → one halved
showcase → CI pointer → plane pointers → docs/dev/license.

| cut | where it went |
|---|---|
| `--large` fixture output, the 1202-element synthetic block | one sentence naming both, with the round-2 link that explains why the big one exists |
| the second half of the freedesktop-sdk showcase | replaced by three takeaway bullets; the full report is the walkthrough's |
| "Reading the report" (36 lines) | **moved** to `cli.md`, where the reference lives, and linked from the showcase |
| Plane 2 section (67 → 24) | kept the two commands and what the plane answers; the pasted CPU/memory/parallelism blocks are the walkthrough's |
| Plane 3 section (34 → 17) | same shape |
| the CI section's gate table | `ci-comment.md`, which `UX-139` made the CI owner's page |

Nothing was deleted outright: every cut is either relocated (and the
link points at where) or was already stated in the file it now points
to. The line-10 plane paragraph became one clause plus a link to
`docs/README`'s plane table.
