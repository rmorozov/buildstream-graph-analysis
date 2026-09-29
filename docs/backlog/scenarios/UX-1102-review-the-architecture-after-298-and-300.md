# UX-1102: the architecture review is due once #298 and #300 have both landed

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** round 150's push gate (2026-09-28) | **Serves:** R8 | **Topic:** guards | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** test_the_review_has_a_cadence.py

## Motivation

`tests/unit/test_the_review_has_a_cadence.py` bounds the closed rows
between architecture reviews at 25. On round 150's branch (`1d5cf391`)
it read:

```text
29 scenarios have closed since review 28 (2026-09-27), against a bound of 25.
```

PR #298 is writing its own review for the same bound. Ruslan's call
(2026-09-28): merge #298 first, push #300 for review now, and run the
review once both have landed, so one review covers both rounds rather
than two colliding on the review log.

## Required Fix

After #298 and #300 merge, run the `review` skill against
`docs/audits/architecture-review.md`'s checklist over rounds 145-150 and
append its row to that log.

## Out of Scope

Fixing what the review finds: each finding is its own row.

## Acceptance Test

`tests/unit/test_the_review_has_a_cadence.py` passes on `main` with the
new row.

## Outcome (round 149, 2026-09-29) — 🟢 Done

**Premise:** held — the bound was passed by 4, on this branch at `b9e32288`.

### The gap, measured

```text
$ python3 -m pytest tests/unit/test_the_review_has_a_cadence.py -q -p no:xdist
E   AssertionError: 29 scenarios have closed since review 29 (2026-09-28), against a bound of 25.
1 failed, 8 passed in 0.10s
```

`closed.md` held 1038 rows against review 29's 1009: rounds 147-150's
29 closes had no review.

### After

```text
$ python3 -m pytest tests/unit/test_the_review_has_a_cadence.py -q -p no:xdist
9 passed in 0.08s
$ grep -c '^| UX-' docs/backlog/scenarios/closed.md
1039
```

Review 30 is the log's row and section, at 1039 closed rows (this
close included), distance 0. It filed five `r149` lines in
`bookkeeping.md` - two `coverage` guards reading a proxy
(`docs/README.md:97`'s *other ten*, `dev_process_bands.py`'s tokens
unit), one `coverage` record (`directions.md`'s round-148 verifier
clause), two `doc-drift` (`anonymized-bundle.md`'s *13 rows*,
`CLAUDE.md`'s shape figure) - and fixed nothing.

### Mutations verified red and reverted

None: the guard is pre-existing. Deleting the new row reproduces the
gap block above.

### Deviation from the Required Fix

None.

```text
$ make lint
clean: 575 finding(s) match tests/quality_baseline.json
$ python3 tools/dev_close_task.py --check
0 problem(s) over 10 propert(y/ies), 1060 backlog row(s)
```
