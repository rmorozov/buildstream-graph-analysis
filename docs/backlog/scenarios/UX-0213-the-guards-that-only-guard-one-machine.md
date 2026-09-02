# UX-213: the guards that only guard one machine

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-206 (whose acceptance these were), UX-202 | **Topic:** guards

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

## Outcome

**Reproduced first, on a tree with the capture moved aside** — which is
what a fresh clone and every CI runner see. With `flex-grow` made
uniform in `pathBox` *and* `"depth"` hardcoded in `bga/blast.py`, both
at once:

| | mutations applied | result |
| --- | --- | --- |
| before | uniform widths + flat depth | **25 passed, 10 skipped, 0 failed** |
| after | uniform widths + flat depth | **3 failed** (`[committed]`), 11 passed, 8 skipped |
| after, capture present | same | **6 failed** (both fixtures), 0 skipped |

The filing said nine tests skip; the measurement across the two files
is ten. Nothing else in `tests/` was pinned to that path.

**The golden fixture already carried what both drawings need**, which
is why this cost a parametrisation rather than a new fixture: a
three-element critical path with distinct shares (0.43 / 0.36 / 0.21),
and — from `base.bst` — a three-level blast tree (`base` 0, `lib` 1,
`app` 2). Every guard the `UX-206` acceptance names now runs as
`[committed]` and `[real-capture]`, the second skipping where the
capture is absent. Extra coverage, never the only coverage.

**A third pinned guard the filing did not name.**
`test_plane2_coverage_is_published_and_declared` was in the same
condition — the entire Plane 2 half of `UX-202`'s evidence header
guarded on one machine. What it actually needs is the *store's shape*:
a `run/` directory with `plane2.json` beside it. That is cheap to
assemble from the golden fixture in `tmp_path`, so it does, and the
real capture became a second test rather than a precondition. Both
mutations redden it: `bga view` not passing the sibling report, and
`analyze` not publishing the coverage.

**`UX-202`'s no-arithmetic guard was in better shape than the filing
suggests.** Its parametrisation already ran against the golden fixture,
so computing `idle_us` in the viewer reddens `[golden]` on a
capture-free tree — verified. What was aspirational there was the
*second* parametrisation's coverage, not the mutation guard itself.

**And a guard so the class cannot return quietly.**
`TestTheGuardsGuardEverywhere` asserts the fixture matrix contains at
least one entry with no skip mark, and that `git ls-files
--error-unmatch` finds it. Restoring the matrix to the shape UX-213
found it in reddens both of its tests; pointing the committed entry at
an untracked path reddens the first. A skip on a genuinely absent
optional input stays right — what is now impossible is an *acceptance*
whose only guard sits behind one.

Tests: 22 → 24 in the focused-graphs file (10 more actually run on a
fresh clone), plus one in the UX-202 file. Five mutations, each red.

**Deviation from the Required Fix:** none. The alternative it offered —
committing a small real capture — was not needed, because the fixtures
in the repository already carry the fields.
