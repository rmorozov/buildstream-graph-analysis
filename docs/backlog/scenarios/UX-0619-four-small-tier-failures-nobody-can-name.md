# UX-619: four small-tier failures nobody can name

**Priority:** High | **Status:** 🟢 Done Open | **Depends on:** UX-618 (which would have named them), UX-418 (the backstop) | **Found by:** round 84, on three consecutive commits | **Serves:** every session whose PR goes red for no reason it can find | **Topic:** guards

## Motivation

**Round 85 corrected this filing. Two of its four evidence lines were
false, and the failure was reproducible the whole time.** What round
84 wrote is kept below the correction, because the mistake is the
finding.

The four names, from a reproduction at the failing commit:

```text
$ git clone … repo097 && cd repo097
$ git fetch origin 097792a && git checkout FETCH_HEAD
$ python -m pytest tests/ -m small -q -n auto -rf
4 failed, 4007 passed, 39 skipped in 37.61s

tests/unit/test_the_fast_check_holds_what_the_suite_holds.py::…::test_an_agreeing_tree_still_reports_zero
tests/unit/test_the_loop_stays_fast.py::…::test_check_reports_a_clean_tree_as_clean
tests/unit/test_the_loop_stays_fast.py::…::test_the_index_says_what_its_rows_say
tests/unit/test_the_loop_stays_fast.py::…::test_a_hand_edited_count_is_reported_and_then_restored
```

4 + 4007 + 39 = 4050, CI's own collection; CI's 4 + 4002 + 44 differs
only by the five skips a runner without `bst`/`bwrap`/`cc` takes.

**The cause is `UX-617`, one commit early.** At `097792a`
`docs/backlog/scenarios/README.md` carried a stale derived header —
`614 scenarios: **9 open**` against a directory holding 615 — which is
exactly the defect that commit's own message describes, and four
guards read that header. `6febb53` fixed those two lines, which is why
everything after it is green.

The two false lines:

| what the filing said | what the runs say |
|---|---|
| three consecutive pushes failed the backstop identically on all four interpreters | **once.** `6febb53` was red on 3.11 only, at step 14 `Tiers match CI's own record of them` — a different step doing its job. `069947a` was **green** |
| not reproducible on any tree | reproducible in 38 s. The local columns were measured on the working tree and on clones of the *merged* branch, never on `097792a` — every one already had the corrected header |

So the fourth commit's green was not a mystery: the fix had landed two
commits before it. Nothing was undiagnosable; the wrong commit was
tested. The row stands as the record of that.

### What round 84 filed

Three consecutive pushes failed CI's small-tier backstop identically,
on all four interpreters, and the fourth passed with a change that
cannot affect any test outcome.

```text
097792a  4 failed, 4002 passed, 44 skipped
6febb53  failed, all four interpreters
069947a  failed, all four interpreters
4a24cb7  success — diff is ci.yml, Makefile, one task file
```

```text
working tree            4028 passed, 22 skipped
full clone              4011 passed, 39 skipped
shallow clone (as CI)   4010 passed, 40 skipped
CI                      4002 passed,  4 failed, 44 skipped
```

## Required Fix

The four are named and root-caused. Done: they are `UX-617`'s stale
derived header, read by four guards, fixed one commit later.

The enumeration the Required Fix offered as a fallback was done anyway
and is worth keeping, because it retires the `tier_carry.json`
hypothesis on three independent grounds: the cache restores at step 12
and the backstop is step 7; it is `if: matrix.python-version == '3.11'`
while all four interpreters failed; and it lands in `runner.temp`,
outside the tree, where nothing but `dev_tier_drift.py --carry` reads
it. **There is no CI-only input** behind this.

## Out of Scope

- Re-running to make it go away — declined, and it was never needed.
- `UX-618`'s instrument — landed. It did not name these four (the
  reproduction did), but it is why the next occurrence needs no
  reproduction.
- `6febb53`'s 3.11 drift-gate red, which is a different failure and
  undiagnosed — its log is behind a host this environment cannot
  reach. Filed as `UX-621`.

## Acceptance Test

The four names, and a local reproduction of at least one. Both above.

## Outcome

**Round 85**, 2026-09-04. Root-caused, and the filing was wrong twice.

### The four, named

```text
$ git clone … repo097 && git fetch origin 097792a && git checkout FETCH_HEAD
$ python -m pytest tests/ -m small -q -n auto -rf
4 failed, 4007 passed, 39 skipped in 37.61s
```

- `test_the_fast_check_holds_what_the_suite_holds.py::…::test_an_agreeing_tree_still_reports_zero`
- `test_the_loop_stays_fast.py::…::test_check_reports_a_clean_tree_as_clean`
- `test_the_loop_stays_fast.py::…::test_the_index_says_what_its_rows_say`
- `test_the_loop_stays_fast.py::…::test_a_hand_edited_count_is_reported_and_then_restored`

4 + 4007 + 39 = 4050, CI's own collection. CI's 4 + 4002 + 44 differs
by the five skips a runner without `bst`/`bwrap`/`cc` takes.

### The cause

`UX-617`, one commit early. At `097792a`
`docs/backlog/scenarios/README.md` read `614 scenarios: **9 open**`
against 615 rows — the defect that commit's own message describes —
and four guards read that header. `6febb53` fixed the two lines:

```text
$ git checkout 6febb53 && pytest …test_the_loop_stays_fast.py \
      …test_the_fast_check_holds_what_the_suite_holds.py -q
45 passed in 11.75s
```

### What the filing got wrong

| it said | the runs say |
|---|---|
| three consecutive pushes failed identically, all four interpreters | **once.** `6febb53` was 3.11-only at step 14, the tier-drift gate — a different step. `069947a` was **green** |
| reproducible on no tree | 38 seconds. The local columns were taken on the working tree and on clones of the *merged* branch, never on `097792a`, and every one already carried the corrected header |

The fourth commit's green needed no explanation: the fix landed two
commits before it. **Nothing was undiagnosable — the wrong commit was
tested**, and the row was filed rather than the measurement redone.
That is the finding, and it is why the Motivation is corrected in
place rather than replaced.

### The enumeration, kept

Done as the Required Fix's fallback and worth keeping: **there is no
CI-only input**. `tier_carry.json` is retired on three independent
grounds — it restores at step 12 against a step-7 failure, it is
`if: matrix.python-version == '3.11'` while all four failed, and it
lands in `runner.temp` where nothing but `dev_tier_drift.py --carry`
reads it. `GITHUB_*` is read nowhere in `bga/`, `tools/` or `tests/`;
the `test` job installs no buildstream at all, so the 2.7.0/2.8.0
difference cannot touch it.

### Deviation from the Required Fix

**None.** Both halves were delivered: the names with a reproduction,
and the enumeration.

### No mutation

Nothing was built. The instrument this needed (`UX-618`) landed in
round 84; what closed this was reading a commit nobody had read.
