# UX-998: a bookkeeping finding is one line in a ledger, swept once a round

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-994, UX-996 | **Blocks:** UX-999 | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 15:03: "for bookkeeping we can invent some kind of batching to compress amount work" | **Serves:** every round, through the cost a bookkeeping row pays today | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

A bookkeeping drift (a stale figure, a doc naming a retired flag) is filed
today as a full task file with five sections and an Outcome, and worked
as its own track and verifier: the ledger's bounded median is 228k tokens
and 33 min, plus 70k for the verifier (`dev_process_bands.py --runs`).
Round 139 alone moved a census bound, `CENSUS_FLOOR` and `HANDFUL` by one
each to add one guard file (`UX-996`'s Outcome).

## Required Fix

A bookkeeping finding is one line in `docs/backlog/bookkeeping.md`: what
drifted, where, and the command that shows it. Once a round the
`architect` bundles the open lines that fit the `UX-994` cap into one
batch track: one worktree, one commit, one verifier, one CI run. A line
unswept for three sweeps is promoted to a row or dropped with a reason.

## Out of Scope

The retro that turns repeated lines into automation (`UX-999`).

## Acceptance Test

To be named by the `architect`'s Decision.

## Decision

The `architect`, round 140, at `398b4db9`.

```text
Route:     docs/backlog/bookkeeping.md holds one list item per finding; only the new
           tools/dev_bookkeeping.py --add writes a line; --sweep prints open lines oldest first
           with the sweeps survived; --mark changes a status and refuses to leave a line open
           at its third sweep; .gitattributes gives the ledger merge=union; UX-999 reads --json.
           Line: - r<filed> · <status> · <class> · `<path>[:<line>]` · <what drifted> · `<command>`
           status: open | swept r<N> UX-<id> | promoted r<N> UX-<id> | dropped r<N> <reason>;
           class [a-z][a-z0-9-]*, a new one needs --new-class. Derived, never written:
           key = sha1("<path> · <what>")[:7]; sweeps = distinct N > filed in non-open statuses.
           A round's batch is one row whose Required Fix is the --sweep output.
Rejected:  a markdown table - a `|` in a command must be escaped, so it no longer pastes
           a committed BK-NNNN id or counter - parallel filers collide; derivable (UX-996)
           a flag on dev_close_task.py (1254 lines) - the ledger is not the index
           a push-check gate on age - only a sweep commit raises an age
Files:     tools/dev_bookkeeping.py; docs/backlog/bookkeeping.md; .gitattributes;
           tests/unit/test_a_bookkeeping_finding_is_one_line.py; tests/quality_reference.json
           (its first row); docs/contributing/rules.md (§2: a drift you notice is a line,
           anything else a row); fixing-guide.md (§2.5, a §6 row, the sweep in §7a);
           .claude/agents/architect.md (the sweep in the rules it holds)
Guard:     tests/unit/test_a_bookkeeping_finding_is_one_line.py on fixture ledgers: names each
           malformed line; two lines one key fails; an open line's path exists; no open line
           past three sweeps; promoted names a task file; --add round-trips and refuses an
           unknown class; --mark refuses leaving an aged line open; the real ledger parses
Mutation:  SWEEP_LIMIT 3 -> 4 reddens the survival clause; loosening the command pattern
           to (.+)$ reddens the format clause
Class:     optimization - a finding stops costing its own track: bounded median 228k / 32.7 min
           over 34 runs, mechanical 249k / 38.9 min over 46 (dev_process_bands.py --runs 153),
           plus a 70k verifier; k findings a round cost one batch row
Split:     one bounded track, parallel with the others; a batch counts as one row on the cap
Question:  none
```
