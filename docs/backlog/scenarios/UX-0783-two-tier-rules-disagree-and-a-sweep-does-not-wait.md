# UX-783: two tier rules disagree about one file, and a sweep does not wait for what it killed

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-773 (the sweep), UX-418 (the tier record) | **Serves:** the round that moves a file to satisfy one guard and reddens another | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

Three findings, all from `UX-773`'s verifier, all in the same corner.

**1. Two tier rules contradict each other for one file.**
`test_the_tiers_are_a_partition.py` places by *construction* — a file
matching `BOOTS_A_BROWSER` may not sit in the small tier, and its
docstring says explicitly that this direction needs no measurement.
`test_a_slow_file_says_which_file.py` places by *duration* — a
`MEDIUM` entry must record at or above `MEDIUM_FLOOR_S` (1.0s).
`UX-773`'s new guard is both a browser file and fast:

```console
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_killed_browser_does_not_outlive_the_worker.py -q --durations=0
0.61s call ...      # three runs: 0.61, 0.63, 0.61
```

so it reds one guard in `MEDIUM` and the other out of it. Round 108
read the duration rule as the deciding one, moved the file out, and
reddened the construction guard — the exact "runs a tier and commits"
mistake `CLAUDE.md` names. No third file is affected: of 37 browser
guards in the reference, none other records under 1.0s, which is why
the contradiction had never fired.

**2. `UX-773`'s own guard passed only in the order it was run.**
`Browser.__enter__` sweeps, then returns early if this worker already
holds `UX-523`'s shared browser — making no profile root of its own.
The guard's closing assertion was `after == before + 1`, true only
when `_SHARED` is empty, which is true only when the file runs alone.
Under `-n auto` a worker runs many files, and 38 of them import the
same helper.

**3. The sweep signals and does not wait.** `_kill_orphan` sent
`SIGKILL` and returned; `shutil.rmtree` ran on the next line while the
processes were still alive. The launch path hid it — a fresh entry
spends ~0.3s booting Chrome, which is long enough for the pids to go.
The reuse path returns immediately and does not:

```console
# reuse case, before the fix
AssertionError: assert not ['16201', '16221'] == _pids_using(<profile>)
# same case with a 1.0s probe delay inserted
2 passed
```

## Required Fix

1. The two tier rules agree, in code rather than by convention: a
   browser file in `MEDIUM` recorded below `MEDIUM_FLOOR_S` is the two
   rules agreeing, not drifting. Bounded — at or past `LARGE_FLOOR_S`
   it is still a wrong list, because construction says "not small",
   never "any tier will do". The exception is a named function both
   the guard and its own bound clause call; a clause restating the
   condition inline is a guard reading itself (it passed a mutation
   that dropped the bound — see Outcome).
2. `test_a_second_entry_sweeps_the_first` is parametrized on whether
   the worker already holds a shared browser, and asserts the root
   count each path actually produces (`Browser._reused`).
3. `_kill_orphan` waits, bounded, for the pids it signalled to leave
   `/proc`, so the sweep's postcondition holds when it returns and
   `rmtree` does not race a live Chrome.
4. `UX-773`'s Acceptance Test drops `pgrep -f bga-geometry | wc -l`.
   It is machine-wide (82 on this container, never 0) and cannot
   separate this launch's leak from any other guard's browser.

## Out of Scope

- Changing `UX-523`'s shared-browser reuse. It is what makes the
  suite affordable, and the guard was wrong about it, not it about
  the guard.
- Re-measuring the other 37 browser guards. None is near the boundary
  this row is about; a sweep of the reference is `UX-418`'s machinery,
  not this.

## Acceptance Test

```console
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_killed_browser_does_not_outlive_the_worker.py tests/unit/test_a_slow_file_says_which_file.py tests/unit/test_the_tiers_are_a_partition.py -q
```

Green here; red when the reap wait is removed, when `_sweep_stale()`
moves after the shared-reuse early return, when the browser exception
loses its upper bound, when the exception is removed, or when the file
is moved back out of `MEDIUM`.

## Outcome

### The gap, measured

All three were invisible to the way each thing had been run. The tier
contradiction needs a browser file under 1.0s and there was never one
until `UX-773` added it. The order-dependence needs two files in one
worker. The reap race needs an entry that does not spend 0.3s booting.

```console
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_killed_browser_does_not_outlive_the_worker.py -q
1 passed          # alone, green, nine times out of nine
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_page_has_geometry.py tests/unit/test_a_killed_browser_does_not_outlive_the_worker.py -q
AssertionError: expected only the second entry's own root (before=0+1), got 0
```

### The close, measured

`Browser` carries `_reused`, set where `__enter__` returns a shared
browser, so a guard can tell the two paths apart instead of assuming
one. `_kill_orphan` waits for the pids it signalled (`REAP_TIMEOUT_S`
= 2.0s, a refusal-to-hang bound; measured, they clear under 40ms).
`_excused_in_medium()` is the one place the two tier rules meet.

```console
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_killed_browser_does_not_outlive_the_worker.py -q
2 passed          # three consecutive runs, 1.24-1.25s
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py tests/unit/test_the_tiers_are_a_partition.py -q
159 passed
```

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| M1 | the reap wait removed from `_kill_orphan` | `..._sweeps_the_first[True]` |
| M2 | `_sweep_stale()` moved after the shared-reuse early return | `..._sweeps_the_first[True]` |
| M3 | `_excused_in_medium` loses its `LARGE_FLOOR_S` bound | `test_the_browser_exception_does_not_reach_above_the_large_floor` |
| M4 | the exception removed entirely | `test_the_record_agrees_with_the_tier_it_is_in` |
| M5 | the file moved back out of `MEDIUM` (round 108's own mistake) | `test_every_browser_guard_is_listed` |

M1 and M2 redden the **reuse** parameter only — which is the whole
point: that is the case the guard could not previously see.

M3 is the one worth reading back. The first version of the bound
clause restated the condition inline and **passed** the mutation that
dropped the bound — a guard checking its own copy of the rule rather
than the rule. Extracting `_excused_in_medium()` and calling it from
both is what made M3 red.

### Deviation from the Required Fix

None. One decision inside item 1: the exception is downward-only
rather than a blanket "browser files are exempt from the record
check". A blanket exemption would have covered all 37 browser guards
and quietly stopped catching a `MEDIUM` file that grew past the large
floor, which is a real thing that guard is for.
