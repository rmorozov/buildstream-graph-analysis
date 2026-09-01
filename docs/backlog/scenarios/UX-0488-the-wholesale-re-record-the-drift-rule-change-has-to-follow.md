# UX-488: the reference is five hand-appends deep, and the re-record has to come after the rule change

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-476` items 1-3, which are what a candidate must be taken *after* | **Found by:** round 73, closing `UX-476` | **Serves:** the round that reads `spread`'s history off the reference's git log and finds one entry repeated five times | **Topic:** guards

## Motivation

`UX-476` item 4 asked for a wholesale re-record of
`tests/ci_reference.json` from one green run's `tier-reference` job,
retiring the hand-appends round 73 added. It is filed separately
rather than done there, for a reason that is about ordering rather
than effort:

**`UX-476` item 2 changed what `--record` writes.** `spread` now takes
its median over `shift_population` — the files the gate divides by —
and reports `shift_files` beside `files`. A candidate taken from a run
that predates that change carries the old quantity, which is precisely
the proxy `UX-476` filed. So the re-record has to come from a run that
already has the fix in it, and the commit that lands the fix cannot
contain that run's output.

The debt it leaves is the one `UX-458` could not read:

```console
$ for c in $(git log --format=%h -- tests/ci_reference.json); do
    git show "$c:tests/ci_reference.json" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("spread"))'
  done | sort -u | head
{'files': 314, 'shift': 1.34, ...}
```

One distinct spread across every commit, because every commit since
`UX-457` is a hand-append that copies the old one forward. `UX-458`'s
Acceptance Test — *"lists at least the agreed number of distinct
spreads"* — cannot be satisfied by appending at all.

The hand-appends to retire, all from round 73:
`test_emphasis_is_a_budget.py` 16.86,
`test_the_shape_conclusions_have_a_negative_case.py` 0.07,
`test_the_trace_census_reads_both_ends.py` 6.76,
`test_a_generated_project_builds.py` 0.17,
`test_a_candidate_is_confirmed_alone.py` 2.32.

## Required Fix

- **One candidate, whole.** From a green run's `ci-reference-candidate`
  artifact, or — `UX-476` added this — the `::group::` block in the
  same step's log, which is what a reader with an API client and no
  artifact access has. Never a local `--record` (`UX-418`, `UX-447`).
- **The run must carry `UX-476`'s `spread`**, so the document's second
  distinct spread is the quantity the gate actually divides by.
- **Both numbers stated** in the commit: the run's shift and the
  spread's, which `UX-476` measured 24% apart on one run before the
  fix and which should now be the same number.

## Out of Scope

- The rule itself — `UX-476` items 1-3 landed and this row does not
  reopen them.
- `CI_DRIFT_FACTOR` — sizing it is what a second spread makes possible,
  and it is the round *after* this one's question.

## Acceptance Test

```bash
python3 -c "import json;print(json.load(open('tests/ci_reference.json'))['spread'])"
```

showing a spread taken from the re-recording run — a second distinct
one in the document's history, with `shift_files` present — and
`git log -- tests/ci_reference.json` showing the append commits behind
it rather than beside it.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The document, whole

`tests/ci_reference.json` is replaced by run **33544888654**'s
`test (3.11)` candidate (head `3dd6e03`), read out of the
`::group::the same document, for a reader without the artifact` block
`UX-476` added — which is the route this row named, and its first real
use.

```console
$ python3 -c "import json;print(json.load(open('tests/ci_reference.json'))['spread'])"
{'files': 377, 'shift_files': 138, 'shift': 1.069, 'min': 0.094,
 'p25': 0.765, 'p75': 1.107, 'max': 5.709}
```

against what every commit since `UX-457` carried:

```console
{'files': 314, 'shift': 1.34, 'min': 0.105, 'p25': 0.796,
 'p75': 1.269, 'max': 7.257}
```

**The second distinct spread**, which is what `UX-458`'s Acceptance
Test could not be given by appending, and the first one carrying
`shift_files`. 390 files -> 397; the seven the appends never reached
are in it, including `test_the_capability_census_discriminates.py`,
which is the file the gate was failing on.

### The two shifts, and that they are one number now

`UX-476` measured the gate's shift and the recorded `spread`'s 24%
apart before item 2. Paired on run **33540660861**, whose gate line and
whose candidate can both be read:

```text
gate       396 file(s) measured against ci_reference.json (github-actions ubuntu-latest,
           test (3.11), -n auto), this run x1.04 from 138 file(s) over 1s, IQR 0.24
candidate  {'files': 375, 'shift_files': 138, 'shift': 1.039, ...}
```

`x1.04` and `1.039` — the same quantity over the same 138 files, which
is the identity item 2 was for.

### Deviation from the Required Fix

- **The candidate comes from a run that was red, not green.** The row
  says "from a green run's candidate", and that cannot be satisfied as
  written: the run is red *because* the reference is missing entries,
  and the reference cannot be refreshed without a run. The deadlock is
  in the wording rather than in the evidence — what "green" is standing
  in for is *the timings are trustworthy*, and on run 33544888654 the
  suite ran to completion and recorded all 397 files; the step that
  failed is the gate reading this document. Written down rather than
  worked around, because the next round will meet the same deadlock the
  next time a test file is added.
- **The re-recording run's own gate line is not quoted.** The API
  returns only a log tail and the drift step sits above it on that job,
  so the pairing above is from the immediately preceding run instead.
  `UX-476` built the `::group::` route so a reader without artifact
  access could get the *candidate*; the gate's own line has no such
  route, and that is worth a row of its own.

### The runs

```text
make test  5,688 passed, 27 skipped in 326.10s (0:05:26)
make lint  ruff + PyMarkdown, both clean
```
