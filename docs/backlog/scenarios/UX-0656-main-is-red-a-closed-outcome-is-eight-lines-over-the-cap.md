# UX-656: main is red — a closed Outcome is eight lines over the cap

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-643 (whose Outcome it is) | **Found by:** architecture review 16, running `make test` on `a5030a4` | **Serves:** anyone whose branch cannot go green through no fault of its own | **Topic:** process

## Motivation

`make test` on the review's base is red on a clause that has nothing to
do with the review:

```console
$ python3 -m pytest tests/unit/test_the_register_is_terse.py::TestOutcomes -q
E   AssertionError: UX-0643-a-reader-role-that-demotes-rather-than-hides.md:
E   Outcome is 88 lines, cap is 80 - the gap measured, the close measured,
E   the mutation table, the deviation
E   assert 88 <= 80
1 failed, 159 passed in 0.22s
```

```console
$ python3 -c "
import pathlib
t = pathlib.Path('docs/backlog/scenarios/'
                 'UX-0643-a-reader-role-that-demotes-rather-than-hides.md'
                 ).read_text()
print(len(t.split('## Outcome', 1)[1].split('\n## ', 1)[0].strip().splitlines()))
"
88
```

`UX-643` closed in round 88 (`e4d39fc`). The cap is `OUTCOME_CAP = 80`
from `UX-497` on, stated in `CLAUDE.md`'s register and enforced here —
two copies of one number, and this is the enforced one going red.

It is a red gate, so it is the same shape as `UX-644`: every branch cut
from this tip fails a clause it did not cause, and the session that
meets it first has to work out that the failure is not theirs. That is
the cost, not the eight lines.

## Required Fix

`UX-643`'s Outcome comes to 80 lines or fewer, keeping the four things
the cap's message names — the gap measured, the close measured, the
mutation table, the deviation. What comes out is narrative, which is
what the register says goes in `git log` and the task file's body
rather than the Outcome.

## Out of Scope

- The cap itself. Declined: `UX-497` argued 80 and 159 other closed
  Outcomes fit it, so one row over is a row to trim, not a bound to
  raise.
- The rest of `UX-643`, which is closed and verified.

## Acceptance Test

`python3 -m pytest tests/unit/test_the_register_is_terse.py -q` is
green, and the Outcome still names the mutation table and the
deviation.

## Outcome

Already closed when this row was filed, by the commit that caused it.
Review 16 read the base it branched from (`a5030a4`); the fix landed at
`24408cd` on the same branch while the review was running.

The cause was an amendment to `UX-643`'s Outcome naming the clause
deferred to `UX-650`. The fix was not to trim it: a clause deferred to
another row belongs in **Out of Scope**, which carries no cap and is
where a later round looks for it. Moved there.

```text
Outcome lines                             88 -> 79   (cap 80)
tests/unit/test_the_register_is_terse.py  182 passed
```

**Kept rather than deleted as a duplicate.** The row records that a
review running against a moving branch reports the base it read, which
is the correct behaviour and not a defect in the review — the
alternative, a review that re-reads its base mid-run, would report
findings no commit ever had.
