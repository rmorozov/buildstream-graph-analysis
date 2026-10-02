# UX-1271: a finding's Next line runs its command into prose, with no copy control, and the High step names enum words

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), finding R2 | **Serves:** R1 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** test_a_command_renders_as_a_command.py::test_a_finding_step_draws_the_command_with_its_copy_control; test_every_finding_publishes_its_step.py::test_no_finding_says_an_enum_word_or_a_bare_flag

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §R2).

UX-1256's steps render as one paragraph: "Next: a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated — try --capacity N with a higher N, or bga sweep to find the real knee point bga sweep @20260303T091500Z". The command follows the sentence with no separator, wraps mid-command at 1440 ("bga blast layer00/mod010.bst" / "@20260303T091500Z") and has no copy control, where the decision's run-next list draws the same command per §1d. The High finding's sentence is the attribution hint verbatim: enum tokens (§4g), and `--capacity N` without the command that takes it (`bga analyze`). The run's own saturated resource is known (builders 3.99x of 4).

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Route:     Two parts. (1) renderStep in sections.js draws step.command through controls.js commandLine (code.next-command plus a copy-step button), in its own block under the "Next:" sentence, using tables.js copy as the writer. (2) The three resource_wait hints in _shared.py drop the PROCESS/DOWNLOAD/UPLOAD enum words and say `bga analyze --capacity N`; findings.py's wait-category step names the saturated resource in reader words (builder slots, downloads, uploads) from the run's capacity facts, and the trailing "`bga sweep`" moves out of the sentence into the command.
Rejected:  CSS nowrap on the inline code: no copy control, and §1d's "one shared control" (UX-429) is broken again; rewriting the enum words in the viewer: the text report and JSON would keep them.
Files:     bga/viewer/sections.js (renderStep), bga/viewer/style.css (step command block), bga/report/_shared.py (RESOURCE_WAIT hints), bga/findings.py (wait-category step text), tests/unit/test_a_command_renders_as_a_command.py, tests/unit/test_every_finding_publishes_its_step.py, tests/unit/test_capacity_aware_hints.py, tests/unit/test_plane2_conditioned_capacity_advice.py, tests/unit/test_sweep_knee_point.py (text pins), tests/fixtures/golden/mixed_task_kinds/expected_output.json, tests/fixtures/with_timeline/analyze.json (regenerated)
Guard:     tests/unit/test_a_command_renders_as_a_command.py gains a findings site, holding the claim that a finding's step.command renders as code.next-command with a .copy-step sibling. tests/unit/test_every_finding_publishes_its_step.py holds the claim that, on golden, macro_micro and shared_base_wide, no finding title, detail or step contains PROCESS|DOWNLOAD|UPLOAD, or `--capacity` not preceded by `bga analyze`.
Mutation:  in renderStep, replace the commandLine call with el("code", {}, step.command): the findings site goes red. Restore "(PROCESS/DOWNLOAD/UPLOAD)" in one hint: the wording guard goes red.
Class:     product
Split:     finding-text track, last. It writes findings.py and test_every_finding_publishes_its_step.py after UX-1264, UX-1265 and UX-1266. The walker checks for no wrap at 1440 on the 2,402-element page.
Question:  none

## Required Fix

A finding's step draws its command with the §1d shape (one monospace line, copy control) on its own line; the wait-category step names the saturated resource in reader words and the command a flag belongs to.

## Out of Scope

Which step a finding carries (UX-1256); the fixture for it (UX-1264).

## Acceptance Test

On this page every finding command is a `code` element with a copy control and does not wrap at 1440; no finding text contains PROCESS/DOWNLOAD/UPLOAD or a bare `--capacity`. Mutation: render the command as text, and the guard reds.

## Outcome (2026-10-02)

### The gap, measured

At base `b35c30e3`, `renderStep` (sections.js:151) drew `step.command` as a bare
`el("code", {}, …)` after a space inside the sentence's `<p>`: no
`next-command` class, no `.copy-step`. The new findings site, run against that
shape (M1 below), reads it: `2 failed, 16 passed`. `bga analyze
tests/fixtures/shared_base_wide/run --format json`, wait-category's step:

```text
a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated — whether raising capacity would help
depends on …, so this hint is unconditioned; `bga sweep` shows the shape of the curve either way
command: bga sweep tests/fixtures/shared_base_wide/run
```

and the default hint read "try --capacity N with a higher N" with no command.

### The close, measured

`renderStep` draws a sentence `<p>` and, under it, `p.step-command` holding
`controls.js:commandLine(step.command, { copy })` (tables.js `copy`): a
`code.next-command` (`white-space: pre`, scrolls in its own box) and a
`.copy-step` sibling. The same step now reads:

```text
builder slots were saturated (1.97 of 2 busy on average) — whether raising capacity would
help depends on …, so this hint is unconditioned
command: bga sweep tests/fixtures/shared_base_wide/run
```

The saturated resource is the busiest of `occupancy.resource_occupancy` against
its capacity (configured builders for PROCESS, else the peak), named builder,
download or upload slots. The three resource-wait hints in `_shared.py` start
"builder slots, downloads or uploads were saturated"; the default advises
"try `bga analyze --capacity N` with a higher N, or `bga sweep` to find the real
knee point". `_capacity_step`'s fallback therefore reads (backticks stripped):
"builder slots, downloads or uploads were saturated — try bga analyze --capacity
N with a higher N, or bga sweep to find the real knee point". Both committed
analyses regenerated: one `attribution_hints.resource_wait_us` line each.
The 1440 no-wrap check on the 2,402-element page is the walker's. A scrolling
`code.next-command` is a focusable class, so it joins the one ring rule
(`test_a_keyboard_journey_reaches_every_chapter`) and styleguide §4.2's focus row
(`test_the_accent_does_only_its_listed_jobs`). Open: `xl_both` reads 1,194
controls against the 1,192 budget (+2 copy controls); the bound is §3e's, not
raised here.

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| M1 | `renderStep` draws `el("code", {}, step.command)` | findings site, golden + macro_micro, 2 failed, 16 passed |
| M2 | `commandLine(step.command)` with no `copy` | findings site, 2 failed, 16 passed |
| M3 | "(PROCESS/DOWNLOAD/UPLOAD)" into the unknown-capacity advice | wording guard, 4 failed, 12 passed |
| M4 | "a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated" restored | wording guard, 6 failed, 10 passed |
| M5 | default advice "try --capacity N with a higher N" | every-hint clause, 1 failed, 15 passed |
| M6 | step names `PROCESS`, not builder slots | resolved-hint + wording `[shared_base_wide]`, 2 failed, 14 passed |
| M7 | the sweep clause back in the step sentence | resolved-hint `[shared_base_wide]`, 1 failed, 15 passed |
| M8 | `code.next-command` out of the ring rule | selector + tab-ring clauses, 2 failed, 8 passed |
