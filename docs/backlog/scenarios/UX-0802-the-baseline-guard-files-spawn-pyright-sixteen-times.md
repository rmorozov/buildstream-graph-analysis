# UX-802: the baseline guard files spawn pyright sixteen times

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-697 (pyright in the baseline), UX-694 (the baseline's guards), UX-503 | **Found by:** round 110, PR #218's tier-drift gate on `test (3.11)` | **Serves:** R8 reading a red drift gate on a file whose claim did not change | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

```console
$ # CI run 34248564619, test (3.11), the drift gate's line
4 file(s) slower than ci_reference.json records: tests/unit/test_the_baseline_only_shrinks.py 50.7s against 2.4s recorded, x23.15; tests/unit/test_forced_stays_named_past_commit.py 13.2s against 0.9s recorded, x16.27; ...
$ git show origin/main:tests/unit/test_the_baseline_only_shrinks.py | grep -c '"--check"'
14        # 16 after UX-789's clause
$ python3 -m pytest tests/unit/test_the_baseline_only_shrinks.py -q     # UX-789's track, this box
19 passed in 91.80s
```

`UX-697` made `dev_baseline.py --check` run pyright (26 s here) and
the two guard files call `--check` in a subprocess once per clause, so
each clause pays a whole pyright pass to test a ruff or a bandit row.
The reference recorded the files before `UX-697` (2.4 s and 0.9 s,
adopted at 06:18; round 109 merged at 13:54), so the first PR to touch
them reddened the drift gate twice over.

## Required Fix

In `tests/unit/test_the_baseline_only_shrinks.py` and
`tests/unit/test_forced_stays_named_past_commit.py` a clause that tests
a ruff or a bandit row runs `--check` with pyright's findings taken
from a fixture (a `--pyright-from PATH` the tool reads instead of
spawning, or the tool's own findings function monkeypatched in an
in-process call), and only the pyright clauses spawn it. A guard reads
each file's wall against `tests/ci_reference.json`'s row for it after
the refresh: under 10 s on CI.

## Out of Scope

- The reference's refresh itself — done in round 110 from CI's own
  readings, recorded in `docs/audits/round-110.md`.

## Acceptance Test

`python3 -m pytest tests/unit/test_the_baseline_only_shrinks.py tests/unit/test_forced_stays_named_past_commit.py -q`
under 15 s here (91.8 s before); mutation: a ruff clause spawns pyright
again — the wall guard reds naming the clause.

## Outcome

_Not started._
