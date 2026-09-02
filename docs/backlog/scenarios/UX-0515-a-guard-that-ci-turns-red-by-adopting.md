# UX-515: a guard the reference-adopt commit turns red

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-496` (samples), `UX-503` (the adopt step that first wrote them) | **Found by:** round 76, running the suite on the merge base | **Serves:** the next round, which would meet a red `main` and spend its first hour deciding whose it is | **Topic:** guards

## Motivation

`origin/main` is red, and no human commit made it so:

```console
$ git log --oneline -1
96970dc CI: adopt the tier rows this run measured (UX-503)

$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
    tests/unit/test_a_slow_file_says_which_file.py -q -p no:cacheprovider \
    -k test_recording_round_trips
FAILED ...::TestCiIsReadAgainstItsOwnRecord::test_recording_round_trips_and_says_where_it_came_from
1 failed, 121 deselected in 0.41s
```

Swapping only `tests/ci_reference.json` back to the merge base's copy
makes it pass, so the trigger is the adopted document and not the code:

```console
$ git show 6ef1db2:tests/ci_reference.json > tests/ci_reference.json
$ ... same command
1 passed, 121 deselected in 0.36s
```

The clause asserts that `--record` then `--against` on one report is
`ok`. That was true only while the committed reference carried no
`samples` key: `samples_for` then returned `[this run]` for every file
and `files` was the report verbatim. `UX-496` made `files` the **median
of the last five readings**, `--record` reads the committed reference as
its prior, and the first CI adopt wrote the `samples` key — so the
identity the clause depends on stopped holding, on a commit CI pushed
by itself.

The fixture makes it loud rather than marginal: `times` is
`tiers.recorded()`, a developer machine's seconds, and the carried
readings are CI's, so six files read as multiples of their record:

```text
tests/unit/test_snapshot.py  18.9s  against 0.1s recorded, x212.12
tests/unit/test_stream_merge.py  7.6s  against 0.0s recorded, x383.83
```

Neither the tool nor the adopt step is wrong. `--record`'s carrying is
what `UX-496` is; CI's gate compares a run against the **committed**
reference, never against a fresh `--record`, so no real verdict moved.
What is wrong is a clause standing on a property the tool no longer has
— the same shape as `UX-512` and `UX-513`, one axis further out: those
two read the working tree, this one reads a file CI rewrites.

## Required Fix

- The round-trip claim is stated for the case where it holds — a
  **first** recording, with no prior to carry — and asserted there.
- The case that broke it is asserted too, rather than left implicit: a
  recording made against a prior that carries readings has `files` from
  the median, which need not be this run's number.
- Neither `--record`'s carrying nor the adopt step changes. Both are
  right and `UX-496`'s Outcome has the runs.

## Out of Scope

- `UX-513`, the working-tree pair. Same family, different input, and
  folding them would make one row that closes on two measurements
  neither of which is the other's.
- Making CI's adopt step run the suite before pushing. That is a real
  question — it is how a robot commit reddens `main` at all — and it is
  a change to the workflow rather than to this clause: filed separately
  if this recurs.

## Acceptance Test

`tests/unit/test_a_slow_file_says_which_file.py` green against the
committed `tests/ci_reference.json` **and** against the merge base's
copy of it, both pasted. Mutation: drop the carry in `samples_for` — the
clause that states the carried case reddens.

## Outcome (round 76, 2026-09-02)

### The gap

`origin/main` red, reproduced in a clean worktree of it, and the pasted
run is in the Motivation above. The reference swap isolates the cause to
`tests/ci_reference.json` rather than to any code.

### The close

`test_recording_round_trips_and_says_where_it_came_from` asserted two
things at once, and only one of them survives `UX-496`. Split:

- `test_recording_says_where_it_came_from` — the CLI writes
  `measured_on` and the full file set.
- `test_a_first_recording_round_trips` — the identity, stated for the
  case where it holds: a recording with no prior to carry.
- `test_a_recording_against_a_prior_carries_its_readings` — the case
  that broke it, now asserted. A uniform doubling is a *clock shift*
  and rebases exactly, so it cannot show this; one file made six times
  slower on top of the shift can. `files` takes the lower of the two
  readings, so one slow run does not raise the bar.
- `test_the_prior_is_the_committed_reference_not_the_output_path` — the
  mechanism itself, which had no clause at all.

```console
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
    tests/unit/test_a_slow_file_says_which_file.py -q -p no:cacheprovider
125 passed in 1.94s

$ git show 6ef1db2:tests/ci_reference.json > tests/ci_reference.json  # no samples key
$ ... same command
125 passed in 2.15s
```

Green against the reference CI adopted and against the one before it,
which is the acceptance.

### Mutations

| # | mutation | result |
|---|---|---|
| M1 | `samples_for` stops carrying | 6 failed |
| M2 | carried readings not rebased by the shift | 2 failed |
| M3 | `median_low` → `median` | 2 failed |
| M4 | `--record`'s `prior` set to `{}` | **125 passed** → 1 failed |

M4 is the finding. The first pass left the whole file green: nothing
asserted that `--record` reads the committed reference, which is the
exact mechanism that turned `main` red. The fourth clause exists
because of that mutation, and it stands on the `spread` key — the half
present whether or not the prior carries `samples`, so the clause holds
against both references.

### Deviation from the Required Fix

None. Neither `samples_for` nor the adopt step changed; the guard did.
The Out of Scope note about CI adopting without running the suite
stands as written — this is the first occurrence, and the fix here is
to the clause.

Tests: 124 → 125 in `tests/unit/test_a_slow_file_says_which_file.py`.
