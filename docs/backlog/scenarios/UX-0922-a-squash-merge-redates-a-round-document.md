# UX-922: a squash merge redates a round document, and the dateline guard reads the new date

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-782 | **Found by:** `main` went red on `test_a_documents_dateline_matches_its_own_first_commit[130]` the moment #249 was squash-merged, with no branch ever seeing it | **Serves:** every round document merged across a UTC midnight, which is every round whose PR lands late | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-782`'s guard asks whether a round document's own dateline matches
the date its file was **first committed**, so a document written after
the fact cannot claim an earlier date than the work it reports.

A squash merge keeps one commit and dates it when it lands. The
branch's own commits, and their dates, do not survive. So the question
the guard asks changes meaning at the merge: on the branch it reads
the date the document was written, on `main` it reads the date the
pull request was merged.

Measured on 2026-09-22, merging the five open PRs in one sequence:

```text
$ git log -1 --format=%ad --date=short 74fb2712   # the squash commit
2026-09-22
$ grep -m1 'Opens at' docs/audits/round-130.md
Opens at 2026-09-21
$ make test          # on main, 74fb2712
FAILED tests/unit/test_a_run_is_priced.py::TestARegisteredRoundsDateMatchesItsDocument::test_a_documents_dateline_matches_its_own_first_commit[130]
1 failed, 9153 passed, 178 skipped in 340.22s
```

The branch was green on its own head (`bc2c8741`: 9,154 passed) and
CI was green on all 20 checks there. The red exists only on `main`,
produced by the merge itself, so no gate on the branch could have
seen it — the push gate least of all, since the commit it covers is
not the commit that lands.

`main` red blocks every branch's push gate, so this is not a cosmetic
disagreement about a date.

## Required Fix

Name round 130 in `DATE_MISMATCH_WAIVER`, which is the mechanism the
guard already carries for a document whose dateline is true and whose
commit date is not. The document states 2026-09-21, which is the
round's work date **and** the date of its own commit on the branch;
only the squash commit is dated 2026-09-22. Re-dating the document to
2026-09-22 was rejected: it would make the document lie about when the
round ran in order to satisfy a guard about lying.

## Out of Scope

- Changing the merge convention. Squash is what this repository does
  (`#248` was the exception, and made a branch into merged history).
- Making the guard read a date out of the squash commit's message or
  the PR body. That is a real option and a wider one: it would have to
  parse a body this repository does not otherwise read, and it should
  be argued from more than one occurrence. Noted here, not filed, so
  the next round that hits this has one measurement to add rather than
  a hypothesis to inherit.
- The waiver growing one entry per late merge. If it does, that is the
  evidence the option above needs.

## Acceptance Test

`make test` green on `main`'s tree with the entry, and
`test_a_documents_dateline_matches_its_own_first_commit[130]` red
without it.

## Outcome

**The gap measured.** `main` at `74fb2712` (the #249 squash) fails one
guard: `1 failed, 9153 passed, 178 skipped in 340.22s`, and CI's four
`test` jobs fail with it. The document's dateline reads 2026-09-21,
`first_commit_date(130)` on `main` reads 2026-09-22.

**The close measured.** With round 130 named in `DATE_MISMATCH_WAIVER`,
`TestARegisteredRoundsDateMatchesItsDocument` reads 88 passed in 2.34s,
and `make test` on the whole tree is green.

**The mutation table.** Each applied alone, on this tree, and reverted:

| mutation | guard |
|---|---|
| drop the `"130"` entry | 🔴 `round 130: ... says 2026-09-21, but it was first committed on 2026-09-22` |
| waive round 129, whose dateline already matches | 🔴 `round 129 is waived for a mismatch that no longer reproduces` |
| move the entry to `"131"` | 🔴 round 130 unwaived again |

The second is the one that matters: the guard refuses a waiver that
guards nothing, so the entry cannot outlive the condition it names.

**The deviation.** None. The waiver is `UX-782`'s own mechanism used
for the case it was written for, with a reason naming the merge rather
than the document.
