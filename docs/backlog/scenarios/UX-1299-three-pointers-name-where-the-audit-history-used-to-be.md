# UX-1299: three pointers name a place in the audit and design history that is no longer there

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 36, checklist items 3 and 5 (2026-10-02) | **Serves:** contributors | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1293` moved the round table to `docs/audits/directions-history.md`;
two pointers still name the old place, and the new audits index
restates an order the review log does not have:

```text
docs/audits/architecture-review.md:5    "directions.md's round table has carried every round since"
                                        $ grep -c '^| \[[0-9]*\](' docs/design/directions.md          0
                                        $ grep -c '^| \[[0-9]*\](' docs/audits/directions-history.md  118
docs/design/in-step-parallelism.md:268  "status line at `directions.md:1822`"
                                        $ grep -n 'UX-841` to `UX-852`' docs/design/directions.md     2255
docs/audits/README.md:13                "architecture-review.md ... newest last"
                                        $ grep '^##* Review' docs/audits/architecture-review.md: 11 3 1 2 4 6 5 7 8 9 10 13-20, then 36 35 ... 21
```

The log table is newest last; the sections from review 21 on are
newest first, after review 20.

## Required Fix

The first two name `directions-history.md` and a heading rather than
a line number; the index says the log is newest last and the sections
are not in order (or the sections are reordered, which the
append-only rule argues against).

## Out of Scope

Reviews 12 and 29, which have a log row and no section (recorded by
review 30).

## Acceptance Test

The three greps above return the corrected text;
`test_the_round_history_names_every_audit.py` and the link guard stay
green.

## Outcome
