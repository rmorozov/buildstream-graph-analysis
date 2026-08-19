# UX-131: the status table and the task files can disagree, silently

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — (third recurrence of the class)

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

## Fix Implemented

Three tests in `tests/unit/test_docs_links_and_commands.py`, because the
guard needs two preconditions before its comparison means anything:

- `test_every_task_file_declares_a_status` — a file with no marker would
  make the comparison vacuously pass for that item.
- `test_every_task_file_has_a_row_in_the_table` — a file with no row is
  the same invisibility by another route.
- `test_the_table_status_matches_the_task_files` — the guard itself,
  failing with `UX-N: table says X, <file> says Y` for every
  disagreement at once rather than the first.

Only the marker is pinned. Row *summaries* legitimately compress a task
into a sentence and stay prose, exactly as the task asked.

The fixing guide's Definition of Done now says "both, in the same
commit" with the three rounds of history that earned the sentence and a
pointer to the test that will catch it.

## Verification Log

Done 2026-08-19. Mutation both ways, on `UX-133` (🔴 in both places at
the time):

```text
# (a) flip the FILE to 🟢
E       UX-133: table says 🔴, UX-0133-spine-parser-hygiene-round-two.md says 🟢

# (b) restore, then flip the TABLE ROW to 🟢
E       UX-133: table says 🟢, UX-0133-spine-parser-hygiene-round-two.md says 🔴

# (c) restore both
14 passed in 0.88s
```

The five rows round 13 repaired pass on the guard's first run, and every
one of the 132 rows agrees with its file.

**It caught its own author within the hour.** Marking `UX-129`/`UX-131`/
`UX-132` done in this round, the table rows were updated and two of the
three task files were not:

```text
E       UX-131: table says 🟢, UX-0131-…-can-disagree-silently.md says 🔴
E       UX-132: table says 🟢, UX-0132-…-not-luck.md says 🔴
```

Which is the defect this task describes, occurring for the fourth time,
now with a red test instead of an audit round to find it.
