# Round 101: seven ids merged as tracks, and the ledger prices none of them

Opens at `339e6b2` (2026-09-06 15:10), "round 101: take the open
judgements before dispatching them". The next round's own material —
`agent-runs.md`'s round-102 rows — starts at `UX-667`'s first commit
(`312483c`, 17:15); everything reachable from `339e6b2` and not already
in that round-102 set closes seven ids: `UX-728`, `UX-737`, `UX-738`,
`UX-717`, `UX-716`, `UX-692`, `UX-677`. Every one of the seven has a
commit reading `... : merge the track` — a phrase that first appears at
`295bcaf` (15:57), inside this round, and continues through every
track merge from here on, including round 102's.

## What closed

`UX-728` + `UX-737` + `UX-738` (`d01097d`): three tracks, closed
together — "Three tracks each moved the same derived test-file count,
so the row is re-derived once after all merges" (`d01097d`); the CLI
now warns at startup when cwd and the imported `bga` disagree
(`UX-728`), the census detector sees a subprocess population
(`UX-737`), and `bga snapshot` says why it exited non-zero on a build
that could not write reports (`UX-738`).

`UX-717` (`531a3c4`): "correct the premise this row was filed on" —
`were-the-cores-busy` hangs off `capacity-recommendation`, not
`UX-676`, which does not publish a Finding the reachability gate reads.

`UX-716` (`9c4d7ab`): the guard-cost reference re-derived by
perturbation — 54 of the timed entries are in the class it names, not
2.

`UX-692` (`633b23a`): a seeded sweep over generated graphs found a
real, pre-existing defect with no planted mutation — filed as `UX-740`.

`UX-677` (`ee43f6a`): the max-jobs advisor lands, provably at or under
host cores at every window; replay pricing split off to `UX-739`.
`5f6b62f` ("Direction 18: landed") closes in the same window.

## Agents

`docs/audits/agent-runs.md` carries no row with `101` in its first
column:

```console
$ grep -n "^| 101 " docs/audits/agent-runs.md
$ echo $?
1
```

This is not the round-99 shape: seven ids closed by a track merge each,
and no ledger row prices any of them. Round 103's own commit names the
reason directly — `3805321` ("UX-703: close, and the round's five
ledger rows"): "Round 101's four are not here: their transcripts could
not be identified after a context rebuild, and a guessed row is worse
than a missing one." That commit counts **four**; this document's own
scan of `... : merge the track` commits in the round's range counts
**seven** (`UX-728`, `UX-737`, `UX-738`, `UX-717`, `UX-716`, `UX-692`,
`UX-677`). Nothing in the committed record resolves which four of the
seven `3805321` meant, or what happened to the other three's pricing —
this document states that gap rather than closing it.
