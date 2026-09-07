# Round 104 — the verifier earned the round

Five rows closed, one reverted by CI, four filed. The round's subject
was the defect round 103 found five times — **a guard whose population
is narrower than the sentence it checks** — and it found two more, both
inside this round's own fixes, and both only because a verifier ran a
mutation the track had not.

## What closed

| row | what it does |
|---|---|
| `UX-750` | the context map's count rule inverted from a six-noun allowlist to a catch-all digit-run match. The denylist ships **empty** — an exhaustive scan finds `400 lines` was the only count, and the three `400` sentences are re-stated |
| `UX-751` | the `landed` clause reads `_ids_in()` like its `open` sibling. 15 statuses, 94 ids after range-expansion, all closed by two independent methods — zero sentences needed correcting |
| `UX-753` | the flow-axis rule read off the DOM by calling the real `exhibitAxis` with constructed ticks over a served `drawings.js` |
| `UX-755` | the gate itself. See below |
| `UX-756` | the spread's re-derivation condition stated once, in the guide that owns the cost row |

## The gate was lying, and the reason is arithmetic

`CLAUDE.md` says `make test` is the gate. On this container it reported
18 errors CI did not have. Round 103 diagnosed that as concurrent-track
contention and offered a quiet-box re-run as proof. **That was wrong.**

BuildStream sizes its 5% cache reserve against `disk_usage().total`,
never `.free`. On a 270.55 GB filesystem the reserve is 13.53 GB against
13-17 GB free, so `free - reserved` straddles zero and `bst` refuses
with `Cache too full` before any subprocess runs — the capture then
reports `Processes traced: 0`. A quiet box does not change the disk,
which is why the re-run "confirmed" the wrong thing.

The margin is a live variable. Clearing 1.5 GB of dead `/tmp/pytest-of-root`:

```text
free 15.30 GB   free-reserved +1.776 GB
free 16.89 GB   free-reserved +3.361 GB
```

The row's own premise — isolated passes, in-suite fails — did not
reproduce either: the file now fails alone too. The filing had captured
the margin at one moment. Fixed with a repo-owned `$XDG_CONFIG_HOME`
carrying absolute values; at a deliberately-lowered margin, `7 passed,
18 errors` without it and `25 passed` with. The verifier's control
proved the file content load-bearing: an *empty* config directory fails
exactly like the broken one.

Six other real-`bst` files carry the same defect (`UX-760`), so the
gate is one-eighth repaired, not repaired.

## The recurring shape, twice more

`UX-753`'s first attempt guarded nothing. Its verifier deleted the
`middle.length === 1` gate outright — a direct violation of the rule —
and all 16 tests stayed green. The negative clause's population was 7
axes, every one of which failed the *edges* gate independently, so it
discriminated an accident rather than the rule. The fix needed a
constructed axis driven through the real `exhibitAxis`.

`UX-744`'s first two attempts claimed an independence they did not
have. A check that calls back into the production code inherits that
code's failure modes however many layers down you push it: corrupting
`commit_signal()` itself left 32/32 green with a real round's ids
silently gone. Only a value pinned *outside* the code under test caught
it.

## What CI caught that nothing else could

`UX-744` merged, and CI reddened it. Two findings, neither visible from
a worktree:

1. **A round cannot commit the register that describes it.** The
   derivation reads commit subjects, so this round's own closing commit
   created a row for itself and the document was stale on arrival.
2. **CI derives a different register than the branch does.** On
   `ff41d19` CI reported `—` rows `['53','85']` against the branch's
   `['64','85']`. `main` is fully contained in the branch, so ancestry
   is not the explanation, and no mechanism was established.

Reverted and reopened with both written into the row. The session's own
error is the reason CI found it rather than the gate: **the batch
`make test` was skipped before pushing** — the failure mode `CLAUDE.md`
names first. Run afterwards, it was clean.

```text
7668 passed, 83 skipped, 1 warning in 355.84s
```

## What was filed

`UX-757` (the four rounds the register names have no document),
`UX-758` (the edge-mark test reads a merged name, in `drawings.js` and
mirrored in the guard written to read it), `UX-759` (the register's id
column loses a subset in silence, and round 85's ids sit in its own
document), `UX-760` (six more files build against the broken reserve).

## Agents

Twelve runs, 3,158k, six implementer and six verifier, all on `sonnet`.

| | |
|---|---|
| implementer | 6 runs, 2,174k — `UX-744` 634k and `UX-755` 684k are the two that were sent back more than once |
| verifier | 6 runs, 984k — 45% of the implementer spend, and it held three of six rows |

Three tracks were held by their verifier and reworked; a fourth was
sent back for a wrong count. Every held row was held on a mutation the
track's own table did not contain. The rows are in
[`agent-runs.md`](agent-runs.md), derived by `dev_track_cost.py --ledger`.

Every worktree opened between one and twelve commits behind the named
base — `UX-510`/`UX-614`'s pattern again, caught every time by the
brief's own first instruction. Merging cost **1.0 commits per item**,
against the 1.46-1.83 the `decompose` skill prices.
