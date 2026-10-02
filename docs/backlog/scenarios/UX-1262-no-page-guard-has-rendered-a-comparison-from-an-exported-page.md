# UX-1262: `pages.export_uri` copies only the snapshot, so no page guard has ever rendered a comparison

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-163 verification of UX-1257 (2026-10-02) | **Serves:** R1, R4 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** test_the_decision_is_said_once.py

## Motivation

`pages.export_uri` copies only the snapshot, not the store or the earlier run, so no page guard has ever rendered a comparison; `test_the_decision_is_said_once` cannot see a store page.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     tests/pages.py's snapshot_copy/export_page/export_uri take `store=True`, which copies the fixture's whole project store (project.conf + `.bga/runs/*`, `_IGNORED` applied) and returns the copied newest run, so `bga_view.history()` finds @prev and the page carries compare.json; the said-once guard's two_plane case opts in and asserts `#chapter-compare` drawn.
Rejected:  store copy as the default for every store-shaped fixture (39 browser guards change page and pay a `bga compare` per export, unmeasured - not one track's blast radius); a committed store fixture (a second copy of what gen-synthetic writes).
Files:     tests/pages.py, tests/unit/test_the_decision_is_said_once.py
Guard:     test_the_decision_is_said_once on the two_plane store page: `#chapter-compare` present, no long sentence twice.
Mutation:  `store=True` copies the snapshot only: no compare.json, `#chapter-compare` absent, the guard reds.
Class:     bookkeeping (test infrastructure; it is the precondition UX-1277's guard needs)
Split:     first in the store/compare track; UX-1263 runs in parallel; UX-1277 after it lands.
Question:  Default taken; Ruslan may reverse: opt-in `store=True`, not the default for all store fixtures.

## Required Fix

`export_uri` copies the store and the earlier run; the said-once guard runs on a store page.

## Out of Scope

The compare lead itself (UX-1257).

## Acceptance Test

A store page renders `#chapter-compare` under the guard. Mutation: copy the snapshot only, and the guard reds.

## Outcome (2026-10-02)

### The gap, measured

`pages.export_uri(two_plane_run(...))` copied `<project>/.bga/runs/<stamp>/` to
`into/snapshot`: no `project.conf` above it, so `history()` returned `[]` and the
page had no compare.json. The new clause run against that copy (M1 below) reads
`compareChapter: false` on the two_plane page: 1 failed, 12 passed.

### The close, measured

`snapshot_copy`/`export_page`/`export_uri` take `store=True`: the whole project
(project.conf + `.bga/runs/*`, `_IGNORED` applied) is copied to `into/project`
and the same-relative newest run returned. The two_plane case opts in.

```text
$ PYTHONPATH=. python3 -m pytest -p no:xdist -q tests/unit/test_the_decision_is_said_once.py
13 passed in 4.91s
```

`#chapter-compare` present on two_plane, absent on golden/macro_micro; no long
sentence twice on the store page.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M1 | `if store:` -> `if False:` (snapshot copy only) | `test_the_store_page_draws_its_comparison[two_plane]`, 1 failed, 12 passed |
