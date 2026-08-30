# UX-427: the CI reference can be recorded but never refreshed

**Priority:** High | **Status:** 🟡 In Progress | **Found by:** round 68, three red CI runs on PR #187 | **Serves:** every contributor, at the point CI tells them a file is not in the reference | **Topic:** guards

## Motivation

`UX-420` designed `tests/ci_reference.json` around four ways it can rot
and answered each. The answer to two of them is the same sentence, which
the failing step prints:

```text
Make it faster, or - if it is meant to cost this - re-record with
--record and commit, which is how the reference stays true rather than
becoming an alarm nobody reads.
```

**Nothing puts CI's report where a contributor can record from it.** The
junit report is written to `${{ runner.temp }}/junit.xml` and discarded
with the runner. `UX-418` established that a local report cannot stand
in for it — not absolute, not scaled, not ranked. So the instruction is
unfollowable, and the reference has no route back to true.

Round 68 met the consequence. Round 67 added two test files and did not
refresh the reference:

```console
$ python3 - <<'PY'   # the reference against the tree
recorded on: github-actions ubuntu-latest, test (3.11), -n auto
test files present but absent from the reference: 2
   tests/unit/test_the_agent_configuration_holds.py
   tests/unit/test_the_process_is_measured.py
PY
```

Both sat under `MEDIUM_FLOOR_S` and so went unreported, until round 68's
new clauses grew one of them past it:

```text
run 390, test (3.11), head 4b2ba03
  369 file(s) measured ..., this run x1.03 from 112 file(s) over 1s, IQR 0.24
  1 file(s) slower than CI's own record of them:
    tests/unit/test_the_agent_configuration_holds.py  1.4s
      and not in the reference at all
```

That is the rule working exactly as `UX-420` specified — rot 1, *"a new
file arrives with no reference… so an unreferenced file over the medium
floor is reported"*. It is **intermittent**, because the threshold is
`MEDIUM_FLOOR_S × shift` and the file sits near it: red on runs 389 and
390, green on 391.

An alarm that cannot be answered is the state `UX-420`'s own closing
sentence warns about.

## Required Fix

Put this run's numbers where the next session can read them.

- **A CI step that prints the refreshed document.** `--record -` already
  writes it to stdout; nothing invoked it. It must run with `always()`,
  because the step that asks for a refresh is the one that fails the job.
- **Then refresh the reference** from that output, in a commit that says
  which run it came from.

## Out of Scope

- **Uploading the report as a build artifact**: a second mechanism for
  the same fact, and reading a log is a route this session already has.
  Worth revisiting if a human ever needs it outside a session.
- **Changing the unreferenced-file rule**: it is right, and it is what
  found this. Suppressing it would trade a true alarm for silence, which
  is `UX-418`'s defect exactly.
- **Re-recording to silence `test_the_order_the_page_has.py`**, reported
  on run 392 at 20.6s against 11.1s with the run's IQR at 0.52. That is
  a different question — contention or drift — and it needs the second
  sample this refresh will not provide.

## Acceptance Test

- A CI run prints a document whose `files` covers every test file in the
  tree, with no entry missing.
- `tests/ci_reference.json` refreshed from a named run, and the drift
  step green on the run after it.
