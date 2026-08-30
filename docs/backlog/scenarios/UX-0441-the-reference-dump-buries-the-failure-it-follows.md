# UX-441: the reference dump buries the failure it follows

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 69, twice, diagnosing two separate reds on `test (3.11)` | **Serves:** whoever reads the next red CI run, which under `UX-426`'s loop is everybody | **Topic:** guards

## Motivation

`UX-427` added a step that prints this run's per-file timings so the
reference can be refreshed from a real CI run:

```yaml
      - name: This run's timings, for refreshing the reference
        run: |
          python tools/dev_tier_drift.py "${{ runner.temp }}/junit.xml" \
            --record - --source "github-actions ubuntu-latest, test (3.11), -n auto"
        if: always() && matrix.python-version == '3.11'
```

`if: always()` is deliberate and right — a red run's timings are still
timings, and gating the record on success would lose exactly the runs
worth re-recording from. **But the document it prints is 370 file
entries**, and it prints them *after* the failure, so the tail of the
job log is the dump and nothing else.

Measured, twice in one round:

| red | what the tail showed | diagnosable from it? |
|---|---|---|
| `26f5db9`, tier drift | the drift message, then 370 lines | yes, barely — the message is 4 lines above the dump |
| `9675209`, cause unknown | 370 lines of reference, no assertion | **no** |

On the second the failing assertion was never reachable: `tail_lines`
is how the logs arrive, the dump is longer than any tail worth
fetching, and the round moved on with the cause unread. That is the
whole cost — a red nobody can diagnose is a red that gets re-run or
ignored, which is the habit `UX-426`'s loop exists to replace.

**This is the loop's own economics.** Batching verification into CI
only pays if the red is *readable*; a step that reliably buries the
failure taxes every red on the busiest job in the matrix.

## Required Fix

- **Keep printing it on failure**, and stop it burying anything.
  Options, to be chosen in the item: wrap it in a `::group::` so it
  folds by default; write it to a file and upload it as an artifact
  rather than to stdout; or print it *before* the suite rather than
  after.
- **Whichever is chosen, the failure stays the last thing in the log.**
  That is the property to hold, not the mechanism.
- A guard on the workflow, in the shape
  `test_the_workflow_runs_only_where_the_skill_says` already uses —
  the step exists, still runs on failure, and does not end the job's
  output.

## Out of Scope

- **Removing `if: always()`**: `UX-427` chose it for a stated reason
  and a red run's timings are the ones a refresh most wants.
- **Shrinking the reference**: 370 files is what the suite has, and the
  document is not the problem — where and how it is printed is.
- **How the logs are fetched** — a reader with the browser open can
  scroll past it, and this item is about not making them.

## Acceptance Test

Take a job whose suite fails, and read the last 50 lines of its log:
the failing assertion is in them. A mutation restoring the ungrouped
trailing dump must redden the guard.

## Outcome

_Not started._
