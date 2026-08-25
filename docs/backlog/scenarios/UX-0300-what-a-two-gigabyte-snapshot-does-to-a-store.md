# UX-300: what a two-gigabyte snapshot does to a store

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** Direction 15, UX-167 (the prune keep-set), UX-188 (raw-log retention), UX-234 (the aggregate that should see sizes) | **Serves:** R1, R5, R7 | **Topic:** store

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

## Outcome

🟢 **Done.** Sizes are facts the tool states, and one of them is a
decision.

**The re-measurement the item asked for, and what it changed.**
`UX-188` kept the raw Plane 2 log by default on a measurement of
8-12% of a capture. Redone at 200,000 processes, the *compression* is
unchanged - 51,995,560 B of log to 4,679,800 B, **9.0%**, 11.1x - but
what it is a fraction **of** moved. `UX-297` took the per-process
records out of the report in this same round, so a snapshot is now:

```text
plane2.log.gz     4,679,800 B    99.0%
plane2.json          43,879 B     0.9%
run/                  1,599 B     0.0%
build.log               702 B     0.0%
                  -----------
                  4,725,980 B
```

**The decision: the default stands, and its sentence changes.** The raw
log is the ground truth the timeline is rendered from and, since
`UX-297`, the only place a per-process fact lives at all - dropping it
leaves a run whose timeline can never be rendered again. What was true
in `UX-188` ("8-12%, so keeping it is cheap") is no longer the reason;
the reason is that it *is* the capture. So `--no-keep-raw` now looks
like a small saving and is the whole one, and the capture says so out
loud whenever the log is more than half of what it just wrote.

**What states a size now.**

1. *Every capture*, not only past a threshold: `This snapshot: 4.5M.
   /p/.bga/runs: 9.0M over 2 snapshot(s).` A number every time is what
   lets a reader notice the run that grew; the 2 GB warning stays one
   line further down, because "you are past the point where this
   matters" is a different sentence from "this one cost 4.5 MB".
2. *The aggregate* (`UX-234`), which reads a whole store at once and
   until now said nothing about disk although the rows have carried
   `bytes` since `UX-159`. Per host class, a `snapshot_bytes`
   distribution and a `total_bytes`; at the **document** level, a
   `store_bytes` block. Outside `blended` on purpose: every other
   blended figure is refused across host classes because a duration
   measured on two machines is two populations (`UX-186`), and a byte
   is a byte - a reader asking what their disk holds must not have to
   pass `--blend`. It counts **every** snapshot, including those
   excluded from the timing distributions: a capture that failed is not
   a sample and still occupies its disk, and `measured_total` says
   which is which.
3. *`prune --max-store SIZE`*, the question a disk actually asks. Age
   and count are proxies for it: a nightly capture that grew from 4 MB
   to 2 GB makes `--keep 5` mean something different every month, and
   `--max-store 20G` means the same thing forever. Oldest-first,
   combined with the other rules as the stricter of the two rather than
   an override, and a store it cannot reach without deleting
   `@last`/`@prev` reports that rather than emptying itself - this item
   prices, it does not delete.

**Falsification.** Four mutations against the committed tree:

```text
P1  the budget deletes protected snapshots            2 guards red
P2  the store total forgets the failed captures       1 red
P3  the capture stops naming the raw log              1 red
P4  a size suffix is ignored (`2G` reads as 2 bytes)  7 red
```

**Out of scope, held.** Nothing deletes without being asked: `--prune`
is still a bare word that has to be typed, `--dry-run` still says what
would go, and the keep-set is unchanged - `test_prune_protects...`
and the `UX-167` guards are green untouched.

**Not done here.** The item's last line asks for a capture-side peak
RSS ceiling "beside `UX-297`'s". `UX-297`'s own ceiling is the clause
that did not land - the peak is set by the event sort before any fold
begins, and is recorded there as gated on an artifact consumable in
order. A ceiling here would be a second copy of that unmet claim, so it
waits for the same work rather than being asserted at whatever the
current number happens to be.
