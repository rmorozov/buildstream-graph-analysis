# Round 121 — the first day on a real project: a FIFO bound onto its own host path, kinds that never read, and the three rows review 24 left

Run on 2026-09-15, after round 120 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

The user ran the merged tool on a real project (elements behind a
junction, GNU Make 4.4 on the host) and hit two things on the first
build: `bwrap: can't mkdir parents for .../my_project/.bga/tmp/trace-
*/bind/jobserver: read-only file system` on the first cmake element,
and "bst show gave no element kinds" so every decision read
`unknown_kind`. Two `researcher` reads ground-truthed both: the FIFO is
the one mount `UX-846` never reached, bound onto its own host path and
only under fifo-style auth (make 4.4, never this box's or CI's 4.3);
the kinds read drops every option of the user's own command and, when
it does succeed, keys the map by `bst show`'s junction-qualified name
while the shim looks up the project-relative one. No example has a
junction. Four filings, plus the three rows review 24 left open.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-869` `UX-870` `UX-871` `UX-866` `UX-867` `UX-868` | disjoint surfaces: the shim's mount, the tracer's read, the map's spellings, the guide's keys, the map's labels, a Chrome case |
| 2 | `UX-872` | after 869 and 871: a junctioned example under `bga snapshot --jobserver auto` in CI |

## What closed

(in progress)

## Agents

no agents launched at this commit: the tracks start after the pull
request opens, and their rows land in the ledger as they finish.
