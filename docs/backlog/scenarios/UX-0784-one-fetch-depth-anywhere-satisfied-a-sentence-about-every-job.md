# UX-784: one `fetch-depth: 0` anywhere satisfied a sentence about every job

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-781 (the clause this extends), UX-637 (the sweep) | **Serves:** the round whose gate is green on four jobs and red on the fifth | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-781` fixed `ci.yml`'s base-diff step and shipped with a Deviation
stating: *"with the workflow fixed nothing in CI is cut."* That was
wrong, and CI said so on the next push. `bst-tests` reddened on
`b42d874` with six failures, all the register guards:

```text
FAILED tests/unit/test_a_run_is_priced.py::TestTheRoundRegisterIsDerived::test_the_written_table_matches_the_derivation
  check ['... is a shallow clone - `git log` cannot see the whole history
  this derives from ... `git fetch --unshallow` first (UX-776)']
FAILED ...::test_the_real_checkout_is_complete
  AssertionError: this checkout is shallow
```

`bst-tests` runs the **whole** `make test` on a default-depth
checkout. Three jobs run pytest; only `test` asked for full history:

```console
$ python3 -c "…yaml…"      # jobs whose run steps contain `make test`
test             fetch-depth=['0']
bst-tests        fetch-depth=['-']
```

`test_ci_asks_for_the_history_these_guards_read` was green through all
of it. It asserts `"fetch-depth: 0" in workflow` — one occurrence
anywhere in the file satisfies a sentence whose subject is *the
machine that must not have a shallow clone*. The `test` matrix's
`fetch-depth: 0` was covering for the job that had none.

Same defect shape as `UX-781`'s own two: a guard whose population is
the file when the claim is about jobs. This is the third instance in
one round, which is why it gets a row rather than a line in a
Deviation.

## Required Fix

1. `bst-tests` checks out at `fetch-depth: 0`. It runs the whole
   suite; every history-reading guard in that suite is otherwise
   declining or reddening there.
2. `test_ci_asks_for_the_history_these_guards_read` gains a sibling
   that reads **jobs**: any job whose run steps contain `make test`
   must have a checkout asking for depth 0. The file-level clause
   stays — it is the cheap sanity check — but it is no longer the only
   one.

## Out of Scope

- `agent-config`. It runs one named file plus `dev_commit_bodies.py`,
  which deepens to 200 deliberately (`UX-781`'s own carve-out), and it
  does not run `make test`.
- Making the register guards *skip* on a shallow clone. `UX-781`
  declined that and the reasoning holds: a skip here buys silence in
  the job that most needs the answer. The fix is to stop cutting the
  history, not to stop noticing.

## Acceptance Test

```console
$ python3 -m pytest tests/unit/test_a_guard_that_reads_history_declares_its_depth.py -q
```

Green here; red when `bst-tests`'s `fetch-depth: 0` is removed, which
is exactly the state `b42d874` was pushed in.

## Outcome

### The gap, measured

The clause that was supposed to catch this asserted a substring:

```python
assert "fetch-depth: 0" in workflow
```

True since `UX-597` added it to the `test` matrix, and true while
`bst-tests` ran 8,021 tests on a 1-deep clone. The six failures were
all `UX-781`'s own message improvement doing its job — the assertion
now carries `check()`'s words, so the log said "is a shallow clone"
instead of listing 55 round numbers and leaving the reader to guess.

### The close, measured

```console
$ python3 -c "…"     # jobs whose run steps contain `make test`
test             runs `make test`, fetch-depth=['0']
bst-tests        runs `make test`, fetch-depth=['0']
$ python3 -m pytest tests/unit/test_a_guard_that_reads_history_declares_its_depth.py -q
14 passed
```

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M1 | `bst-tests`'s `fetch-depth: 0` removed — the exact state `b42d874` was pushed in | `test_every_job_that_runs_the_suite_asks_for_it` |

One mutation, because there is one claim: a job that runs the suite
has the history the suite reads. It reproduces the observed CI failure
from the workflow alone, without waiting for a runner.

### Deviation from the Required Fix

None. `UX-781`'s Outcome is corrected in place rather than left
standing — its Deviation asserted something this row disproved two
commits later, and a later round reads that file instead of the code.
