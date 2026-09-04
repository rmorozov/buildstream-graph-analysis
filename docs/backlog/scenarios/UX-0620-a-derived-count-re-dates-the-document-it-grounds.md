# UX-620: a derived count re-dates the document it grounds

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-247 (the log's rule), UX-233 (the count in the opening), UX-604 (the window this sits beside) | **Found by:** round 85, with `main` red | **Serves:** every session that runs the suite on a fresh clone | **Topic:** guards

## Motivation

**`main` is red.** A clean checkout of `5343bd6` fails:

```text
$ git clone … && git checkout 5343bd6
$ python3 -m pytest tests/unit/test_the_verification_log_is_true.py -q
FAILED …::TestTheLogIsNotStaleAboutItself::test_the_claimed_date_is_not_older_than_the_last_change
E   the Verification Log claims 2026-09-03 (after UX-569), and
    architecture.md was last changed 2026-09-04.
1 failed, 6 passed
```

The only change round 84 made to `architecture.md` is its **derived**
count:

```diff
-from 604 `docs/backlog/scenarios/` files, 75 …
+from 619 `docs/backlog/scenarios/` files, 75 …
```

That figure is written by `tools/dev_close_task.py --check --write`
from `git ls-files`. It is true by construction, and it cannot make a
grounding wrong — the grounding is a claim about the document's
*assertions*, not about a number the tree computes.

So the staleness clause reads the file's last-commit date as a proxy
for "have this document's claims drifted", and a derived figure moves
the proxy without moving the thing. Fixing guide §5, in a guard.

The coupling is not one-off: **every round that files or closes a row**
rewrites that count, re-dates the file, and demands a re-grounding
with nothing to re-ground. Round 84 filed nineteen.

## Required Fix

The staleness clause compares the claimed date against the last change
that touched something **other than** a derived figure. The derived
figures are already enumerated by
`tests/unit/test_a_counted_figure_is_derived.py`; the comparison reads
that enumeration rather than a second copy of it.

A commit that moves a derived figure *and* prose is a substantive
change and still counts.

## Out of Scope

- Re-grounding the log by hand this round — declined: nothing
  substantive changed since `2026-09-03`, and writing "checked" over a
  count bump is the unmeasured claim `UX-247` exists to prevent.
- Moving the count out of the opening (`UX-233` put it there on
  purpose).

## Acceptance Test

A commit that changes only the derived count leaves the clause green;
a commit that changes a sentence beside it turns it red.

## Outcome

**Round 85**, 2026-09-04. `main` was red; it is green, and the
exclusion that fixes it is held to its width.

### The gap, measured

```text
$ git clone … && git checkout 5343bd6 && pytest tests/unit/test_the_verification_log_is_true.py -q
FAILED …::test_the_claimed_date_is_not_older_than_the_last_change
E   claims 2026-09-03 (after UX-569), and architecture.md was last changed 2026-09-04
1 failed, 6 passed
$ git diff 0bc5aff..5343bd6 -- docs/design/architecture.md | grep -c '^[-+][^-+]'
2                    # one line, the derived count: 604 -> 619
```

### The close, measured

`_last_commit()` walks the log and skips a commit whose change to the
document was only a derived count, comparing the removed and added
lines **with the digits normalised away** rather than matching a
pattern against each line — a commit that edits the sentence *and* the
count would match such a pattern and must not be excused.

```text
$ pytest tests/unit/test_the_verification_log_is_true.py -q
13 passed in 0.17s
```

### Mutations

| mutation | result |
|---|---|
| every commit excused (exclusion too wide) | 1 red |
| no commit excused (the defect restored) | 1 red |
| comparison matches the count instead of normalising it | 2 red |
| uneven line counts excused | 2 red |

### The clause that had to be added to make two of those land

Written first as the exclusion alone, **two of the four mutations did
not redden**. Widening the exclusion does not fail the staleness
clause — it removes its date, and the clause *skips*. A guard switched
off silently is worse than one that is wrong, and this is the second
time this round's family of guards has shown that shape.

Two things fixed it. The comparison moved into `only_the_count_moved`,
a pure function tested directly against crafted line pairs — including
the count-and-prose-on-one-line case, which is the one a per-line
pattern waves through. And a non-vacuity clause asserts the exclusion
leaves *something* behind: in a clone with history, `_last_commit()`
must not be `None`.

### Deviation from the Required Fix

**One, and it is a narrowing.** The Required Fix said the comparison
should read `test_a_counted_figure_is_derived.py`'s enumeration rather
than a second copy. It does not: that module enumerates the *figures*
(`N \`docs/backlog/<dir>/\` files`), not the diff lines carrying them,
and importing a sibling guard to borrow a regex would couple two files
for one pattern. The pattern is one line here, with the rule stated
beside it. If a third derived figure joins the opening sentence this
is the place that needs it, and the non-vacuity clause is what will
say so.

### Tier and suite

`test_the_verification_log_is_true.py` small; 13 tests in 0.17s.
