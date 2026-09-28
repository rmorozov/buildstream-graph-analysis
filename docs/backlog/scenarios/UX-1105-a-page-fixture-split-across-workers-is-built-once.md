# UX-1105: a page fixture split across workers is built once

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-320 | **Found by:** PR #298's CI tier gate at `0f36aca0` - `test_the_page_conforms_to_its_sections.py` read 14.5s and 16.4s against 7.4s recorded | **Serves:** every branch whose CI tier gate reads this file | **Topic:** guards | **Area:** bga/viewer | **Shape:** mechanical

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

## Outcome

Gap measured: `pytest tests/unit/test_the_page_conforms_to_its_sections.py
-q -n 4 --dist load --junitxml=...` at `0f36aca0`, summed over its
testcases - 27.876s over 22 (wall 7.69s); the draft's 25.835s.

The Required Fix alone did not close it: the shared build with a
blocking lock read 25.568s. A worker waiting on the lock is charged the
wait in its first test's setup, so four workers arriving together still
sum four builds. What closes it is the lock **plus** overlapping the two
node probes (`_start`/`_finish`: exports stay sequential, since
`bga_view._capture` redirects the process-global stdout - two exports on
threads failed 3 of 10 runs with "printed nothing (exit 0)"), so the
one build costs the slower probe (macro_micro 4.19s, golden 1.56s).

Close measured, same command, three runs:

```text
junit sum 14.734s  wall 4.42s
junit sum 16.471s  wall 4.85s
junit sum 17.247s  wall 5.34s
-p no:xdist        4.467s     (was ~6s)
```

`make test` (`-n auto`, 4 cores): `1 failed, 10251 passed, 199 skipped
in 489.94s`, the file 7.192s over 24 inside it; the one red was this
branch's own helper name `_shared_root` matching `bga/report/_shared.py`
in `test_the_loop_stays_fast.py`'s wide-module set - renamed
`_session_root`, both files 70 passed.

Mutation table:

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| the shared directory | `_session_root` returns the per-worker basetemp | the file's junit sum at `-n 4 --dist load` | 26.301s, 27.800s, 27.913s |
| `_built_once`'s marker check | `if True:` (always build) | `test_racing_workers_build_once` | 1 failed / 2 (`built 4 times`) |
| `_built_once`'s lock | `flock` replaced by `pass` | `test_racing_workers_build_once` | 1 failed / 2, three runs (`built 4 times`, or a racer exiting 1) |
| marker written last | test `out.exists()` instead of `.done` | `test_an_unfinished_build_is_redone` | 1 failed / 2 (`'half' == 'built'`) |

Deviation: `--dist loadgroup` with an `xdist_group` mark on this file
was the first route, measured and rejected - the file alone summed
6.747s, but the full suite (`-n 4`, one run each, this container) went
from 515.04s wall under `load` to 773.87s under `loadgroup`. The fix
also overlaps the two probes, which the Required Fix did not name.
