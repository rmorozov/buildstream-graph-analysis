# UX-802: the baseline guard files spawn pyright sixteen times

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-697 (pyright in the baseline), UX-694 (the baseline's guards), UX-503 | **Found by:** round 110, PR #218's tier-drift gate on `test (3.11)` | **Serves:** R8 reading a red drift gate on a file whose claim did not change | **Topic:** guards | **Area:** tools | **Shape:** mechanical

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

Gap measured, this box (`-p no:xdist`):

```text
$ python3 -m pytest tests/unit/test_the_baseline_only_shrinks.py tests/unit/test_forced_stays_named_past_commit.py -q --durations=0
23 passed in 48.57s   # before, CI's own reading was 91.8s
```

`tools/dev_baseline.py` gained `--pyright-from PATH`: `main()` reads
`pyright_findings`' own shape from `PATH` instead of spawning, when
given. Every ruff/bandit clause passes it (`_pyright_fixture()`
writing `[]`); `TestPyrightEntersTheSameList`'s four clauses still
spawn (`spawn_pyright=True`). A fixture-backed `_run` also sets `PATH`
to `_minimal_bin()` — a directory of symlinks to exactly `ruff`, `git`,
`python3` (what `dev_baseline.py` itself spawns) — not the ambient
`PATH` minus pyright's directory: the verifier read that the first
version also lost `/root/.local/bin`'s `pytest`/`bandit` on this box.
A regressed clause that spawns pyright anyway now fails loudly
(`pyright` not found), and `TestTheMinimalBinHasNoPyright` asserts the
built `PATH` resolves `ruff`/`git` and not `pyright` directly.

Close measured, same command, with load (`uptime`) alongside each:

```text
load average: 17.24, 18.49, 15.32 -> 25 passed in 26.13s
load average: 19.34, 19.12, 15.05 -> 25 passed in 33.91s
verifier's box, load 24            -> 26-32s
```

Declined the Required Fix's literal wall guard against
`ci_reference.json` (a `<10s` assertion in the suite): 25-34s here at
load 17-19 makes a 10s bound flaky, not a defect, matching
`test_the_loop_stays_fast.py`'s own convention — wall-clock numbers
are a property of the machine and are not guarded directly; what's
guarded is the mechanism. What enforces the cost instead: the
mechanism guard above (a regression fails loudly, not slowly), and
CI's own drift gate (`dev_tier_drift.against`, unedited) — its rows
for these two files (50.7s/13.2s, refreshed round 110) now overstate
them until main's adoptions pull the medians down, and `against` never
flags a file *faster* than its row, so this fix cannot itself red it.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `dev_baseline.py`: `if args.pyright_from is not None` → `if False and args.pyright_from is not None` | every ruff/bandit clause across both files, each naming itself (`pyright` not found in `_minimal_bin`) | 19 failed, 6 passed in 24.50s |

Reverted from the scratchpad copy, `__pycache__` cleared, re-run
green: 25 passed in 26.13s (load 17.24/18.49/15.32).

**Deviation.** The Required Fix's wall guard against `ci_reference.json` was declined for the mechanism guard — a fixture-backed `--check` runs on a built PATH without pyright, so a regression that spawns again fails loudly — with the convention `test_the_loop_stays_fast.py` states and the 25–34 s readings at load 17–24 that made a 10 s bound a property of the box; the reference rows (50.7 s, 13.2 s) overstate the files until main's adoptions move them, and the drift gate never flags a file faster than its row. `--pyright-from PATH` on the tool is the third surface. One verifier hold (a PATH strip that removed the directory holding pytest; the decline off the record), fixed in a second commit (03d10d4c). Two commits, one verifier.
