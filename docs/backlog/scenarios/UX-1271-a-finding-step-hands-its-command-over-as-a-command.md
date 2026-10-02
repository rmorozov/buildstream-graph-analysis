# UX-1271: a finding's Next line runs its command into prose, with no copy control, and the High step names enum words

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), finding R2 | **Serves:** R1 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §R2).

UX-1256's steps render as one paragraph: "Next: a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated — try --capacity N with a higher N, or bga sweep to find the real knee point bga sweep @20260303T091500Z". The command follows the sentence with no separator, wraps mid-command at 1440 ("bga blast layer00/mod010.bst" / "@20260303T091500Z") and has no copy control, where the decision's run-next list draws the same command per §1d. The High finding's sentence is the attribution hint verbatim: enum tokens (§4g), and `--capacity N` without the command that takes it (`bga analyze`). The run's own saturated resource is known (builders 3.99x of 4).

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A finding's step draws its command with the §1d shape (one monospace line, copy control) on its own line; the wait-category step names the saturated resource in reader words and the command a flag belongs to.

## Out of Scope

Which step a finding carries (UX-1256); the fixture for it (UX-1264).

## Acceptance Test

On this page every finding command is a `code` element with a copy control and does not wrap at 1440; no finding text contains PROCESS/DOWNLOAD/UPLOAD or a bare `--capacity`. Mutation: render the command as text, and the guard reds.
