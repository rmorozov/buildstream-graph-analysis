# UX-1105: a page fixture split across workers is built once

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-320 | **Found by:** PR #298's CI tier gate at `0f36aca0` - `test_the_page_conforms_to_its_sections.py` read 14.5s and 16.4s against 7.4s recorded | **Serves:** every branch whose CI tier gate reads this file | **Topic:** guards | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

PR #298 was red on the tier gate: `pytest-xdist`'s default `--dist
load` scheduler splits `test_the_page_conforms_to_its_sections.py`'s
tests across workers, so its module-scoped `pages` fixture (two
exports and two node probes, ~6s) is rebuilt once per worker that
lands one of its tests - and junit sums those rebuilds as if they were
sequential. Measured here: the file alone at `-n 4 --dist load` sums
to 25.8s (wall 7.5s); on one worker it is ~6s.

## Required Fix

In `tests/unit/test_the_page_conforms_to_its_sections.py` only: build
`pages` and `exports` once per session across workers into a directory
every worker sees (`tmp_path_factory.getbasetemp().parent` under xdist, the basetemp
without it), under an `fcntl.flock` lock (stdlib; `filelock` is not
installed), with a completion marker written last so no worker reads a
half-built page; later workers read the files. Each worker still gets
its own parsed copy, so what a test observes is unchanged.

## Out of Scope

The distribution mode, the `Makefile` and `tools/dev_touching.py` -
`--dist loadgroup` was measured and rejected (Outcome). The other
files booting the same fixtures (`test_a_drawing_is_graded.py`,
`test_apparatus_in_its_place.py`, and more) - candidates on a measured
split, per file.

## Acceptance Test

`pytest tests/unit/test_the_page_conforms_to_its_sections.py -q -n 4
--dist load --junitxml=...` sums well under the 25.8s baseline;
`TestThePagesAreBuiltOncePerSession` races four processes on the
build and asserts it ran once. Mutation: a per-worker directory
returns the junit sum to ~26s; an always-build `_built_once` reddens
the race test.
