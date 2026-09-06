# UX-736: the architecture's status table is a third copy of a guarded fact

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-131 (which guarded the first two copies), UX-657 (its priority twin), UX-88 | **Serves:** every reader who takes the architecture's history table as current | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

Architecture review 18, checklist item 1. `UX-131` fixed one fact
kept in two hand-maintained places, three times over, and the repo's
conclusion was that every hand-maintained correspondence here has
drifted within days. There is a **third** copy, and it has drifted:

```console
$ sed -n '683p' docs/design/architecture.md
| UX-60 | `I3` implemented; the FETCH-in-efficiency question **decided** and documented rather than deferred again - but not yet **applied**, because the answer cannot be one number per element and moves a certified floor in both directions | 🟡 Partial |

$ grep -n "^\*\*Priority" docs/backlog/scenarios/UX-0060*.md
3:**Priority:** Medium | **Status:** 🟢 Done | ...
```

The population, and how far it has drifted:

```console
$ # architecture.md rows `| UX-N | text | <marker> |`, against the task files
architecture.md status rows: 75 | with a task file: 75
disagreements: 1
   ('UX-60', '🟡 Partial', '🟢')
```

75 rows, one wrong. `test_the_table_status_matches_the_task_files`
reads `docs/backlog/scenarios/README.md` and `closed.md` and nothing
else, so this table is outside its population entirely — the same
shape review 16 found three times, a green guard reading the wrong
population. `UX-88` fixed a count at another line of this same
document for the same reason.

Note that the drift is one-directional here in a way the backlog's
is not: the architecture's marker carries a *sentence* ("Partial"
plus a paragraph of why), so it is not merely a marker that fell
behind — it is an argument that a later round settled and nobody came
back to.

## Required Fix

Widen `test_the_table_status_matches_the_task_files`' population to
this table, or state why the architecture's markers are a dated
record rather than a live claim and label them so.

**The decision, taken here: widen the guard.** 74 of the 75 rows agree
with their task files, which is a table being maintained as a live
claim and failing at it, not a dated record nobody was updating — date
it and you would be dating 74 sentences that are currently true, and
the drift would continue silently. The first route is also the
repository's own answer everywhere else, and costs one parse. If it is taken, the marker cell needs reading as
`marker + words` (`🟡 Partial`, not `🟡`) — the backlog's cells carry
the marker alone and a clause written for those returns nothing here,
which is how this table stayed unread. The linked-worktree exemption
`UX-561` added applies unchanged.

If instead these rows are the record of what was true when each
chapter was written, then they are `UX-511`'s shape: date the table
once, and say the live status lives in the backlog. Say which in the
Outcome, and if the second, say what a reader is meant to do with a
🟡 that the backlog closed.

`UX-60` itself is fixed by whichever route is taken; do not fix it
first and leave the table unguarded.

## Out of Scope

- Re-opening `UX-60`. Its task file is 🟢 with a verification log;
  this row is about the copy, not the answer.
- The row *summaries*. `UX-131` settled that prose compresses and
  only the marker is pinned.

## Acceptance Test

The architecture's table is held against the task files, or dated.
Mutation: flip one row's marker away from its file — red, naming the
id, the table's marker and the file's.
