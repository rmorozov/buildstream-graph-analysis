# UX-441: the reference dump buries the failure it follows

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 69, twice, diagnosing two separate reds on `test (3.11)` | **Serves:** whoever reads the next red CI run, which under `UX-426`'s loop is everybody | **Topic:** guards

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

## Outcome (round 70, 2026-08-30) — 🟢 Done

### The gap, measured

One red suite, one report, the step run both ways. The suite is
`make test-small` with `UX-441`'s own guard mutated back to `--record -`
so it fails; the record command is the workflow's, verbatim:

```console
$ { python -m pytest tests/ -m small -q -n auto --junitxml=$T/junit.xml
    python tools/dev_tier_drift.py $T/junit.xml --record - \
      --source "local reproduction of the CI step" ; } > red-before.log
$ wc -l < red-before.log
314
$ tail -50 red-before.log | grep -c AssertionError
0
$ tail -5 red-before.log
    "p25": 0.714,
    "p75": 1.373,
    "max": 42.951
  }
}
```

**314 lines, and the failure is not in the last 50 of them.** That is
the two reds of round 69 reproduced on demand — the tail of the job is
the document, and the assertion is above it, unreachable through
`tail_lines`.

The document's size is not incidental to where it is printed:

```console
$ python tools/dev_tier_drift.py $T/junit.xml --record $T/ref.json | wc -l
1
$ python tools/dev_tier_drift.py $T/junit.xml --record -            | wc -l
155
```

(155 here because the fixture report covers 141 files; CI's covers 370.)

### After

`ci.yml` records to `${{ runner.temp }}/ci_reference.candidate.json`,
uploads it as the `ci-reference-candidate` artifact, and echoes one line
saying so. `if: always()` is untouched — `UX-427` chose it for a stated
reason and this item's Out of Scope keeps it.

```console
$ { <the same red suite> ; <the same step, --record to a file> ; } > red-after.log
$ wc -l < red-after.log
72
$ tail -50 red-after.log | grep -c AssertionError
1
$ tail -3 red-after.log
FAILED tests/unit/test_a_slow_file_says_which_file.py::TestTheRecordStepDoesNotBuryTheFailure::test_ci_records_to_a_file
============ 1 failed, 2925 passed, 19 skipped, 1 warning in 11.40s ============
recorded 230 file(s) to .../cand.json
Refresh tests/ci_reference.json from the ci-reference-candidate artifact on this run.
```

314 lines to 72; the assertion moves from *above the last 50* to
**twelve lines from the end**.

The `echo` is not decoration. Taking the document out of the log took
away the route the tool's own advice depends on — `--against` says *"re-record
with `--record` and commit"*, and until this item the numbers it asks
for were the next thing on screen. Now they are an artifact, so the step
has to name it; `test_the_log_says_where_the_document_went` is the guard
that keeps it named.

### The guard, and the six mutations that reddened it

`tests/unit/test_a_slow_file_says_which_file.py::TestTheRecordStepDoesNotBuryTheFailure`,
five clauses. The one that decides is
`test_a_recorded_run_prints_a_line_and_not_the_document`, which **runs
the tool both ways on one report and counts the lines** — a workflow
text scan alone would be an instrument reading a proxy (fixing guide §5)
for "the log stays short". The four workflow clauses tie CI to the mode
that measurement covers.

```text
M1 back to --record -                     red: test_ci_records_to_a_file
M2 the record step is gated on green      red: test_it_still_runs_when_the_suite_fails
M3 the artifact is not uploaded           red: test_the_document_is_still_a_click_away
                                          red: test_the_log_says_where_the_document_went
M6 the step names no artifact             red: test_the_log_says_where_the_document_went
M4 --record PATH prints the document too  red: test_a_recorded_run_prints_a_line_and_not_the_document
M5 --record - stops printing it           red: test_a_recorded_run_prints_a_line_and_not_the_document
```

M5 is the clause guarding its own discriminator: if the two modes ever
print the same amount, the counting clause decides nothing, and it says
so rather than passing.

One clause needed a second attempt: `--record\s+(\S+)` read the path as
`${{`, because `${{ runner.temp }}` contains a space. It failed loudly
rather than passing over the wrong string, which is why it was caught in
the first run and not by a mutation.

### Documents this made wrong

`UX-427`'s Outcome asserted *"`ci.yml` runs `--record -` on every 3.11
run"*, and its Out of Scope refused the artifact as *"a second mechanism
for the same fact, and reading a log is a route this session already
has"*. Reading the log was not a route it had. Both annotated in this
commit (fixing guide §3.6).

### Deviation from the Required Fix

Of the three options the item offered — a `::group::`, an artifact, or
printing before the suite — the artifact was chosen. `::group::` folds
only in the web view and not in a fetched log, which is how these reds
were read; printing before the suite would record numbers the suite has
not produced yet. One addition beyond the Required Fix: the `echo` naming
the artifact, because removing the document from the log broke the
tool's own advice, and that breakage is this item's to fix.

### The suite

```console
$ make test-touching
261 passed in 5.54s

$ make lint
All checks passed!

$ make test
5336 passed, 26 skipped, 1 warning in 292.27s (0:04:52)
```

The five new clauses cost 0.15s on
`test_a_slow_file_says_which_file.py`; the file stays in no tier list,
which is where its measurement puts it.

### What CI itself has not shown yet

The Acceptance Test asks for a *job* whose suite fails. This branch's
own runs are the first place that can happen, and the reproduction
above is the same two commands in the same order on the same report —
not the runner. If a red on this branch shows the failure outside the
last 50 lines, this item is not closed.
