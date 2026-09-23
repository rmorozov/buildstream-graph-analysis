# UX-912: the timing reference is unrepresentative on four files, and the base-carry miss makes branches pay for it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-442, UX-476, UX-503, UX-803 | **Found by:** round 132 — one `test (3.11)` run reported four files whose records the runner disagrees with, none named by the diff | **Serves:** every branch charged for a cost `main` carries | **Topic:** guards | **Area:** tools | **Shape:** judgement

## What the gate actually costs, measured 2026-09-21

The tier gate is not a nuisance on the side of the run. It **suppresses
the jobserver measurement entirely**, and that went unread for two runs
of `#248`.

`bst-examples` — the job that builds `examples/11-serial-giant` in both
arms and prints `giant.bst`'s peak width, the only instrument that can
close `UX-913` — declares:

```yaml
bst-examples:
  needs: [test, bst-smoke]
```

with no `if: always()`. So any red in the `test` matrix skips it. On run
35617305041 the suite passed (`9031 passed, 172 skipped`) and only the
tier gate failed, on one file the branch does not touch:

```text
tests/unit/test_the_documented_invocations_parse.py 16.7s against 9.2s recorded, x1.53
```

and the job list records the consequence:

```text
bst-examples          skipped
bst-tests             skipped
bst-smoke             skipped
flake-ledger-adopt    skipped
tier-reference-adopt  skipped
touch-map-adopt       skipped
```

`ci.yml:1141` calls `bst-examples` "not correctness-gating (a failure
here doesn't mean ...)". The dependency is the other way round: a gate
that **can only read runner noise** (`CI_DRIFT_SECONDS`' 5s floor, and
`UX-908`'s own record of six runs landing on both sides) decides whether
the corner-case data is gathered at all. The three adopt jobs are the
same shape, so a noisy run also stops `main` from adopting the reference
that would have excused it — the miss feeds itself.

**Two separable defects, and the second is cheap.** The base-carry miss
below is the reason the branch is charged. But `bst-examples` being
downstream of it is independent of who pays, and would be fixed by the
`always()` that the steps immediately either side of the gate already
carry:

```yaml
- name: The branch's own diff, ...      if: always() && matrix... == '3.11'
- name: Tiers match CI's own record ... if: matrix... == '3.11'       # <- no always()
- name: Leave it for the next run       if: always() && matrix... == '3.11'
```

**Retracted before it was written down.** "Main never saves a base
carry" was the first hypothesis and it is false. Run 35605347763's
`test (3.11)` job records step 15 `Tiers match CI's own record of them`
**success** and step 16 `Leave it for the next run` **success**, at
13:5x; `#248`'s run at 15:12 still reported no reachable base carry
~70 minutes later. `carry()`'s own docstring says it is written on every
`--against` run "including the runs that find nothing", so a clean main
run leaves one too. What a red main run does skip is the gate step —
7 of the last 12 `main` push runs failed — but a prefix `restore-keys`
would fall back to an older carry, so sparseness alone cannot produce
"not found". The reachability question is still open, and the Actions
caches API is 403 through the agent proxy, so it needs either a run that
prints the cache id or an owner-side read.

## Motivation

`UX-911` is one file. This is the population it sits in. One run,
`35552785970` on `9481d275`, shift x1.18, reported four files at once:

```text
slower than CI's own record of them:
  tests/unit/test_the_size_ledger_only_shrinks.py      15.2s  against 7.4s   x1.75
  tests/unit/test_the_styleguide_names_its_guards.py    7.0s  against 0.1s   x42.27

over both gates on 2 consecutive runs, nothing in the diff naming them:
  tests/unit/test_a_drawing_is_graded.py               17.5s  against 6.5s   x2.30 (UX-908)

over both gates on this run only:
  tests/unit/test_the_documented_invocations_parse.py  17.7s  against 9.2s   x1.63
```

A third file joined them on `89f3edd3`, run `35578708249`, on the
slowest runner any of these has seen:

```text
this run x1.18, 1 file(s) slower than ci_reference.json records:
  tests/unit/test_the_size_ledger_only_shrinks.py  14.7s against 7.4s  x1.69
```

The obvious excuse does not apply. `POPULATION_CLASS` scales
`expected` for a guard whose cost follows a directory's size, and two
files are in it; this one is not a candidate, because it runs
`dev_sizes.py` against a `tmp_path` package with a faked `pylint`
rather than against the tree. Its cost follows how many subprocesses
it launches - one per case - so a record taken when the file had fewer
cases is stale for a reason the reading has to name before the number
is adopted.

The diff that run carried was four documentation files. Timed against
a clean `origin/main` worktree on one machine, one interpreter, the
two confirmed files read:

```text
        test_the_size_ledger_only_shrinks.py    branch 9.52s   main 9.02s
        test_the_styleguide_names_its_guards.py branch 4.23s   main 3.42s
```

Within this container's own noise. The absolute seconds are not CI's —
local I/O here is slower than the runner's, which is why `--record` on
a developer machine writes the wrong clock (`UX-418`, `UX-447`) — but
the *comparison* is the measurement, and it says neither file is the
branch's.

The gate says so itself, in the same run:

```text
Every run is read against the one recording run, so agreeing runs are
evidence the reference entry is unrepresentative as much as evidence the
file got slower - and `git diff origin/main` touches neither these files
nor anything that names them
```

**Why `main` never pays.** `UX-803` excuses a file the base branch's
own last run already read past both gates, and on a pull request that
needs `main`'s carry restored from a cache. Every failing run on this
branch reported it absent:

```text
Cache not found for input keys: tier-carry-refs/heads/main-, tier-carry-refs/heads/main-
tier_carry_base.json: no carry from the base branch's own runs reachable, so a file
crossing the gates here is read as this branch's until one is (UX-803).
```

`main` saves under `tier-carry-refs/heads/<default>-<run_id>` and the
base restore asks for prefix `tier-carry-refs/heads/<default>-`, which
should match.

**Narrowed, not settled.** Two of the three hypotheses are ruled out
by four readings of `actions/cache` across three refs. Two of them are
the *perf* carry - a different prefix through the same action and the
same `<name>-<run_id>` key shape - because that is what the available
logs show restoring; the tier carry's own same-ref restore is inferred
from the gate reporting a two-consecutive-run window, not read:

```text
main  run 35536366563  step 16 "Leave it for the next run"  success 20:57:02
main  run 35536366563  restore, own ref                     HIT
        Cache hit for restore-key: perf-carry-refs/heads/main-35511368643
#246  run 35564652560  restore, own ref                     HIT
        Cache hit for restore-key: perf-carry-refs/pull/246/merge-35554538952
#246  run 35569523700  restore, base ref                    MISS
        Cache not found for input keys: tier-carry-refs/heads/main-,
                                        tier-carry-refs/heads/main-
```

So the key's prefix form works — it is the form that hits, twice, on
two different refs — and `main` does run its save step. **A restore
succeeds within a ref and fails across one**, which leaves cache
scoping and rules out the key and a missing save.

**And the narrowing itself was wrong — retracted 2026-09-22 by
`UX-923`.** In all four readings above the ref and the restore's
`path` co-vary: both same-ref hits name the same `path` their save
wrote, and the one cross-ref miss names a different one. `actions/cache`
v6 sends `version: sha256(paths|method|salt)` beside the key, from the
literal `path:` input on both sides, and the service matches both — so
`tier_carry_base.json` asked for `a3a89e94..` where every save wrote
`d1e90db5..`, and no key could have hit. The version is printed at
`core.debug` only, which is why four runs read a key problem.

**And scoping is not the defect either — measured 2026-09-22.**
`UX-923` made the restore report itself below the gate; on run
35686105692, `event=pull_request` on #255 and so `github.ref` =
`refs/pull/255/merge`, the check run's annotation reads `tier carry:
the default branch's carry restored`. A pull request run does read a
`refs/heads/main` entry, so `UX-803` is not inert on pull requests and
the carry needs no route the repository controls.

## Required Fix

Two parts, in this order, because the second is worthless without the
first.

**Decide how the base carry travels — done in `UX-923`.** The
decision this row framed as cache against artifact was answered by
measuring instead: the cache was never the defect, the restore's
`path` was. `UX-923` carries the fix, its guards and what it leaves
open. Nothing here is owed on this part.

It is the second gate, not the first. `over_gate` needs an absolute
`seconds - expected >= CI_DRIFT_SECONDS` (5.0s), so a stale cell only
reaches the carry at all once the file's own reading crosses that
floor - measured in `UX-911`, run `35564652560` read the same file at
4.27s against a 0.12s expectation and the step returned `tiers ok` at
`dev_tier_drift.py:1148`, before `--base-carry` was read at `:1153`.
So the four files above are four *different* distances from the floor,
and only the ones that clear it can be charged to a branch. The miss
decides who pays; the floor decides whether anyone does.

**Refresh the reference.** Take a CI run's own `ci-reference-candidate`
artifact and adopt it, so the record is what the runner reads. Never
`--record` locally. `UX-911`'s file is excluded from this: make that
scan cheap first, then record the result, or the refresh banks a 45x
regression as normal.

`UX-924` blocks this, filed from the `UX-908` thread and confirmed by
reading the code: `adopt()` takes `times = candidate.get("files")`,
and `files` is `median_low` of that candidate's own samples, so a full
flat window adopts the committed value back onto itself. The normal
adopt route would bank the frozen medians rather than the run's
readings, which is the opposite of a refresh. Land `UX-924` first, or
bypass `adopt()`. (The structure is read here; that row's own 37-commit
and 399-of-566 figures are its measurement, not re-taken.)

For each of the other three, the reading decides: a file whose cost
grew for a reason (`test_a_drawing_is_graded.py` is already `UX-908`)
is a defect and keeps its own row; a file whose record was simply
taken on a quieter runner is a reference to refresh.

**Two figures above moved in round 131** (`UX-908`). Its excursions do
not rise: the ledger's four ratios are 1.701, 2.142, 2.245 and 2.114,
one step on 2026-09-15 where the file went 26 -> 36 tests, then a band
spanning 6%. And its `ci_reference.json` entry is 13.86 now, not the
6.5 the run above reads against, so that row's x2.30 is x1.05 today.
`UX-908` also names why the unattended route never refreshed it —
`UX-924`.

## Out of Scope

`UX-911`'s scan, which has its own row and its own fix. `UX-908`'s
bisect. Changing what any of the four guards assert, or which tier
they sit in. Raising a record for a file whose growth nobody has
read — a grown cell is a defect before it is a number to adopt.

## Acceptance Test

The base carry arrives: one `test (3.11)` run on a pull request whose
log reports a restored `tier_carry_base.json` rather than
`no carry from the base branch's own runs reachable`, with the `main`
run it came from named in the Outcome.

`tests/ci_reference.json` refreshed from a CI artifact, and one
`test (3.11)` run on a branch carrying only this change reporting
`tiers ok` with no file in the confirmed list.

A guard holds that the refresh came from CI: a reference whose
`measured_on` does not name a `github-actions` source is refused.
A mutation writing a developer machine's source must redden it.

## Outcome

**Round 138, 2026-09-23**

**Premise:** held — three of the four records were a quieter runner's
reading, and the adopt route has replaced them; the fourth is below.

### The gap, and the refresh: `git show <sha>:tests/ci_reference.json`

`UX-924`'s code (`c8b2f781`) made each adopt bank the run's own
reading; five adopts since (`c19560d6` `e5b8f3db` `c2fbf2b6`
`461c9c6b` `0c166828`) moved 426/282/483/298/500 entries each.

```text
                 run 35552785970   c8b2f781       dcbe4615 files [samples]
size_ledger      15.2 vs 7.4       7.38 [x5]      7.0   [14.83, 6.16*, 6.82, 7.0*, 11.28]
styleguide        7.0 vs 0.1       0.14 [x5]      1.16  [1.23, 1.18*, 0.81, 1.16*, 1.12]
drawing_graded   17.5 vs 6.5      13.86 [x5]     13.87  [13.86, 13.86, 14.23, 14.71, 13.87]
invocations      17.7 vs 9.2       9.19 [x5]      9.64  [9.19, 9.19, 13.41, 9.64, 12.3]
* a small-tier junit: runs 35762184541, 35788690618 skipped `Test (with a timing report)`
```

`styleguide` reads 0.81-1.23 on the runner after `UX-911`, and its
record followed (x0.70-1.06). `drawing_graded` agrees (x1.00-1.06).
`invocations` has three real readings, 9.64-13.41, and two carried
copies the next two adopts replace; no ledger row in 6 gate runs
since 35755437814 (`UX-929`'s Outcome). All four are CI readings: the
adopt job reads only a CI run's candidate.

**`size_ledger` still disagrees, and not for a cost growth.** Its
full-suite readings are 6.82-14.83 (and the ledger's 12.3-12.7);
the median 7.0 is held there by the two small-tier readings, a run
with the medium and large tiers absent. The file itself did not grow
since its 7.38 was taken on 603850ed — alternated, one container:

```text
python3 -m pytest -q tests/unit/test_the_size_ledger_only_shrinks.py
603850ed copy (8 tests)    17.38s  14.42s  15.11s
HEAD copy    (10 tests)    16.96s  13.60s  16.33s     load average 15 on 4 cores
```

So it is a reference to refresh, and its route admits readings from a
run the gate does not read — `UX-943`'s defect, measured on one entry.

### The carry arrives — Acceptance Test, clause 1

```text
$ GET /actions/runs/35798639535/jobs  (pull_request, 71eb9d5d)  test (3.11)
12 What the last run of the default branch found   success 23:53:42
16 Tiers match CI's own record of them             success
$ GET /check-runs/106983666251/annotations
notice | tier carry: the default branch's carry restored
```

The newest `tier-carry-refs/heads/main-*` save before 23:53:42 is run
35797680418's (8d25211e), `Leave it for the next run` done 23:42:16;
the log line naming the hit key is behind `curl: (56) CONNECT tunnel
failed, response 403`, so the run is named from the timestamps.

### Clause 2 and 3

The gate step is green on 8 of 8 main runs since `c8b2f781` that ran
it, and on PR runs 35798639535 and 35794009831. The provenance guard
exists: `test_a_slow_file_says_which_file.py::TestCiIsReadAgainstItsOwnRecord::test_the_committed_reference_is_in_one_of_those_two_states`.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | `measured_on` rewritten to `a developer machine, -n auto` | that clause, 1 of 1; restored, 1 passed |

### Deviation from the Required Fix

No artifact adopted by hand: the adopt route is the refresh (403 on
artifacts here; `UX-924` argues against a one-run `--record`). No
run yet on a branch carrying only this change — this branch's PR
run is the first. The preamble's `bst-examples` coupling is not in
the Required Fix and had nothing to skip: no main run since
`c8b2f781` was red on the gate alone.
