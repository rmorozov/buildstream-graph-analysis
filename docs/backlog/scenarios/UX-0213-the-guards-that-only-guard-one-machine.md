# UX-213: the guards that only guard one machine

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-206 (whose acceptance these were), UX-202

## Motivation

Round 21's dominant finding was guards that cannot fail. Round 23's
verification found the class alive in the newest tests, wearing a
new disguise: **guards pinned to a capture that exists on exactly
one machine.**

`tests/unit/test_focused_graphs_not_a_dag_viewer.py:28` and
`tests/unit/test_the_page_that_answers_why.py:30` hardcode

    REAL = "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/run"

— a timestamped snapshot that is not in git and that no CI workflow
creates. Nine tests skip with "no real capture here" everywhere but
the sibling's container. Among them are the two mutation guards
UX-206's acceptance names: `test_the_widths_are_the_published_share`
and `test_depth_is_hops_not_position_in_the_list` — the guard for
the transitive-closure bug UX-206's own log brags about catching.

Proven, not argued: with `flex-grow` set uniform in `pathBox`
(`views.js`) and `"depth": depth` hardcoded to `1` in
`bga/blast.py`, **the entire relevant test set stays green** in a
fresh checkout — 6 passed, 8 skipped in the focused-graphs file, a
236-test wider sweep all green. The synthetic 1,202-element test
asserts fold counts but no widths; nothing asserts depth on any
committed fixture. "Six mutations, each red" was only ever true on
the machine that had the capture.

The UX-202 exposure is milder but the same shape: the "every
number is a published field" walk runs against the golden fixture
*and* the real capture — and the real half silently skips, so half
the declared coverage is aspirational.

## Required Fix

The named mutation guards must fail on fixtures that are **in the
repository**: assert widths against `share_of_path` and depths
against the payload on the synthetic/golden fixtures (both carry
the needed fields), keeping the real-capture variants as extra
coverage where the capture exists. Alternatively (or additionally)
commit a small real capture the suite can always reach. Either
way, the acceptance mutation — uniform widths, flattened depth —
must redden a test that runs on a fresh clone and in CI.

## Out of Scope

- Shipping the full 20260821T170127Z capture (size dictates the
  choice; the guard question is independent of it).
- The skip mechanism itself — skipping on a genuinely absent
  optional input is right; the defect is that the *only* guard for
  an acceptance lives behind one.

## Acceptance Test

On a fresh clone with no `.bga` anywhere: `flex-grow` made uniform
reddens a width guard; `depth` hardcoded reddens a depth guard;
the UX-202 published-field walk runs (not skips) against at least
one committed payload carrying `signals.critical_path_detail` and
a blast tree. CI runs all of these unskipped.
