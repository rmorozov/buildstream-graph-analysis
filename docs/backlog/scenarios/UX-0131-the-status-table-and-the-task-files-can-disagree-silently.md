# UX-131: the status table and the task files can disagree, silently

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — (third recurrence of the class)

## Motivation

Round 13 found **five** status-table rows contradicting their task
files — UX-114/115/116/120 shown 🔴 Not Started while their files read
🟢 Done with full verification logs (the final commit of the range
never touched the table), and UX-100 shown 🟡 while UX-120's work
closed it. Round 11 found the inverse (UX-85: table 🟢, file 🔴).
Round 12 found row *wording* drift. Three rounds, three shapes of the
same defect: two hand-maintained copies of one fact.

The repo's own conclusion (round 12) applies verbatim: every
hand-maintained correspondence has drifted within days; every
mechanically-checked one has held. The emoji and its file's line-3
status are mechanically comparable today.

## Required Fix

1. Fix the five rows (done directly by round 13's own commit — this
   task is the guard, not the data).
2. A test that parses every `UX-NNNN-*.md`'s line-3 `**Status:**`
   emoji and the README table's row status and fails on mismatch,
   naming the item — same family as the filename-padding and
   findings-table guards. Row *summaries* stay prose (they legitimately
   compress); only the status marker is pinned.
3. The fixing guide's checklist gains "update the row when you update
   the file" with a pointer to the test that will catch you.

## Out of Scope

- Generating the table from the files (a bigger change; the guard
  makes drift visible, which is the actual requirement).

## Acceptance Test

Mutation both ways: flip a file's status → suite red naming the item;
flip a row's emoji → red; restore → green. The five repaired rows pass
on the first run of the new test.
