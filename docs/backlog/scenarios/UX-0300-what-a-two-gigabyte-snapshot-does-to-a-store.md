# UX-300: what a two-gigabyte snapshot does to a store

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** Direction 15, UX-167 (the prune keep-set), UX-188 (raw-log retention), UX-234 (the aggregate that should see sizes) | **Serves:** R1, R5, R7 | **Topic:** store

## Motivation

One field snapshot now weighs ~2 GB. Five of them are a laptop's
disk noticing; a CI runner capturing nightly is a quota incident
scheduled in advance. The store's retention thinking dates from
kilobyte snapshots: the raw log is kept by default because it
measured 8-12% of a small capture (`UX-188`) — at field scale it
is 400 MB per snapshot; pruning keeps aliases and the newest
healthy run but nothing thinks in bytes; and nothing on the
capture path states what was just written or what the store now
weighs.

The capture-side numbers, measured this round: the tracer holds
the full record list to write the monolith (479 MB per 400 k
processes, its own measurement); the post-build auto-compare
parses both runs' monoliths coexisting (~7-8 GB projected at field
scale, `bga/cli.py:371-388`) on the machine that just finished
building; and the merge path needs the raw log fully decompressed
to disk (~4.7 GB for the field capture's 400 MB gz).

## Required Fix

Sizes become facts the tool states and decisions read: the capture
summary prints what this snapshot weighs and what the store
totals; store rows already carry `bytes` — the aggregate
(`UX-234`) reports the distribution and the total; `bga snapshot
--prune` gains a bytes-aware mode (keep-set unchanged, but the
report says what deleting would recover); and the raw-log default
is re-argued **at scale** with the `UX-188` measurement redone on
a large capture — whatever the decision, its number is from a
gigabyte run, not a kilobyte one. Capture-side peak RSS on the
big-run input gets its ceiling beside `UX-297`'s.

## Out of Scope

- Automatic deletion beyond what prune already does with consent —
  deleting measurements without being asked is how evidence
  disappears; this item prices, it does not delete.
- Compression-format changes to the raw log (it is already
  gzipped; `UX-298` addresses the other artifacts).

## Acceptance Test

After a capture the summary states snapshot and store sizes
(asserted on fixtures); the aggregate payload carries per-store
byte totals and per-snapshot distribution; `--prune`'s report
names recoverable bytes and the keep-set survives unchanged
(existing guards green); the re-measured raw-log ratio on the
big-run fixture is recorded in this file's log with the decision
it supports.
