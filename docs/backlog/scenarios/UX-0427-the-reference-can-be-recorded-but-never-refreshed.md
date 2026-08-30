# UX-427: the CI reference can be recorded but never refreshed

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 68, three red CI runs on PR #187 | **Serves:** every contributor, at the point CI tells them a file is not in the reference | **Topic:** guards

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
  *Revisited and reversed by `UX-441` (round 70)*: reading the log was
  not a route it had. The document is 370 lines and it printed after
  the suite, so on two reds of round 69 the failing assertion was off
  the end of the tail. The artifact is now the only copy CI keeps, and
  the step prints one line naming it.
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

## Outcome (round 68, 2026-08-30) — 🟢 Done

### The gap, measured

```console
$ python3 - <<'PY'   # the reference against the tree
test files present but absent from the reference: 2
   tests/unit/test_the_agent_configuration_holds.py
   tests/unit/test_the_process_is_measured.py
PY
```

Reported intermittently on three of five runs of PR #187, and
unanswerable: the step's own advice is *"re-record with `--record`"*,
and CI's junit dies with the runner.

### After

`ci.yml` runs `--record -` on every 3.11 run, with `always()`. Run
`33318288027` printed the document, and it carries both:

> **Superseded by `UX-441` (round 70).** The `always()` half stands; the
> `-` does not. CI now records to `${{ runner.temp }}/…json` and uploads
> it as `ci-reference-candidate`, because printing the document after
> the suite put it between the reader and every failure it followed.

```text
"tests/unit/test_the_agent_configuration_holds.py": 1.43,
"tests/unit/test_the_process_is_measured.py": 0.2,
```

`1.43` is corroborated: run `33316532360` reported the same file at
`1.4s` through a different code path (the unreferenced-file branch),
one runner and twenty minutes apart.

### Two entries appended, not a re-record — and the reason is in the output

The obvious move is `--record` over the whole document. **This run was
not fit to record from**, and the instrument `UX-423` added on the same
day is what says so:

```json
"spread": { "files": 305, "shift": 1.0, "min": 0.1,
            "p25": 0.833, "p75": 1.353, "max": 28.4 }
```

A run where some file read **×28.4** its recorded value is not a
baseline. Re-recording from it would have replaced 369 known-good
numbers with one contended afternoon's — including
`test_the_order_the_page_has.py`, which this item's Out of Scope
explicitly refused to silence.

So the two absent entries were appended and everything else left alone,
with the provenance written into the document's own `note` field. That
is a departure from how the reference is meant to be maintained and it
is recorded as one, in the file a later round will read.

### The second sample this refresh was not supposed to provide, provided anyway

| run | `test_the_order_the_page_has.py` | verdict |
|---|---|---|
| reference | 11.14s | — |
| 392 (`51b6c76`) | 20.6s, ×1.51 after ×1.22 | reported |
| 394 (`2527114`) | **13.64s**, ×1.22 of the reference | quiet |

Ordinary variation on the second reading. Run 392's 20.6s was
contention, which is what the comment on PR #187 argued from that run's
IQR of 0.52 before this run existed. Nothing to change in the rule, and
`UX-423`'s record now has a second sample that says so.

### Mutations

**None applied, and that is a gap.** This item is a workflow step and a
data file: the step either prints the document or it does not, and the
run above is the evidence that it does. The clause that would need
falsifying — *a CI run prints a document covering every test file* —
cannot be mutated from here, because mutating `ci.yml` proves nothing
until CI runs it. `UX-426`'s section 7 is exactly about this class of
claim. The next run against this reference is the test, and it is the
one that closes the acceptance test's second clause.

### Deviation from the Required Fix

- **The Required Fix said "refresh the reference from that output".**
  Two entries were appended instead, because the output's own `spread`
  showed the run was unfit to be a baseline. The Required Fix assumed
  any run's document is a refresh; it is not, and the instrument that
  reveals that shipped this morning.
- **None.** The acceptance test's second clause — "the drift step green
  on the run after it" — was open when this Outcome was first written
  and is now met: run `33318972985`, job `99277452407`, `test (3.11)`,
  head `ba452ce`, conclusion **success**. The drift step carries no
  `continue-on-error`, so a green job is a green step. Neither appended
  file was reported.

  `test (3.10)` also passed on that run, so `UX-428`'s race did not
  recur — it remains filed, not fixed, and intermittent.
