# Round 106 — the agent workflow's own loop, and the guards that read a citation

Run on 2026-09-07. Eight rows closed, three filed. The user ordered
it: workflow rows first, features and bugs after. Four `implementer`
tracks in parallel on `sonnet`, each read by a `verifier` before
merge — the mandate `UX-761` put in the guide last round, exercised
for the first time on a full round.

**Every one of the four tracks was held, and every hold was on
something the track's own report asserted and a verifier's own commands
disproved.** Three of the eight rows are that pattern; two of the eight
did not exist when the round opened, because CI found them.

## What closed

| row | what it does |
|---|---|
| `UX-757` | rounds 99-102 documented from committed material, each claim cited; round 101's unpriceable agents waived by name |
| `UX-763` | fixing guide §7a — what closing a round owes, in order, gate last |
| `UX-765` | both tier readings dated, with a guard reading the transcription against its source |
| `UX-766` | a forced baseline entry stays named across later, unrelated forces |
| `UX-767` | the push gate's channel boundary, stated as what is knowable |
| `UX-768` | the closing note is a file, not a shell word |
| `UX-769` | a count guard matches a number, not a task id |
| `UX-770` | the cost row carries a range, not a tie-break |

## The measurement that read a ledger blind to its own subject

`UX-767` reported **0 of 41** pushes used the channel its hook covers,
inferred from `agent-runs.md` carrying no push row. That ledger
structurally never records the session's own merging and closing —
`CLAUDE.md` says so outright — so its silence was not evidence of
absence. One counter-example falsifies it: `e513c31`, round 105's own
closing commit, pushed by an explicit Bash `git push`.

The false universal was already written into `fixing-guide.md` and the
hook's docstring as an established count. Both now say only what is
knowable: the mix is not recoverable from committed material, at least
one push used the covered channel, and CI is the backstop regardless.
**The decision never needed the count to be zero**, which is exactly
why the false absolute was avoidable.

## The guards that read a citation, not a claim

`UX-767`'s first guards checked for the string `UX-767`. The verifier
kept that citation in place and rewrote the boundary sentence to assert
the opposite — *"this hook catches every push on every channel"* — and
both stayed green. They now read the substantive terms, and the
reversal reds them.

Re-verified, the strengthened guards over-fit: a legitimate rewording
of the same true claim also reds them. That is a smaller failure than
the one it replaced and it merged, but it is a failure and it is
recorded here rather than discovered later.

## The fix that shipped the defect it was fixing

`UX-766` made a committed forced-baseline entry visible again. But
`write_baseline` kept a single `forced_by` slot that every `--force`
overwrote, so the next unrelated force would silently erase the first
while its lines sat unreviewed — the same silence, one cycle later. The
verifier found it by constructing the compounding case; no reading of
the diff shows it. Batches now accumulate, and an identity drops only
when it leaves `findings`.

## Two rows CI filed

**`UX-769`.** Four jobs red on one guard:

```console
AssertionError: the verify skill states the reference's row count (503)
$ grep -n 503 .claude/skills/verify/SKILL.md
148:**After adding a test file, do nothing.** `UX-503`: a file the
```

`assert str(rows) not in text` is a substring check, and the reference
reached 503 rows on CI while this container read 488. It matched the
task id the guard names in its own failure message. Latent on `main`
since `3ac4816`; it fires whenever an adopted count collides with a
cited id.

**`UX-770`.** Local wrote `median 38`, CI computed `median 37`, same
commit:

```console
as committed (94 modules):  '31-145 of 515 test files'   sizes[47] = 38
one module fewer (93):      '31-145 of 515 test files'   sizes[46] = 37
```

`sizes[len(sizes) // 2]` is not a median for an even population — at 94
modules it returns the upper of a 37/38 pair. The published integer sat
on a tie over a directory read with `rglob` while the suite runs. The
range survives the same perturbation, so the range is what the sentence
carries now — `UX-503`'s principle, reaching the figure that reddened
this round. Removing it exposed a second defect immediately: the
rewriter's pattern then matched only a prefix, leaving `, median 38`
behind where no guard could see it.

## What the host cost, three ways

None of these were test failures, and all three looked like one.

| | measured |
|---|---|
| `UX-760`'s reserve | `free 9.54 GB` against a 13.53 GB reserve = **-3.986 GB**, and 29 real-`bst` tests refuse before running. Clearing 3.3G of dead pytest dirs: `+2.239 GB`, all 29 green |
| `UX-741`'s wall clock | 385 orphaned Chromium processes holding **22.12 GB**, load 8.64. Reaped; the two spine clauses went `2 passed in 27.56s` |
| a proxy read | `make test 2>&1 \| tail -5` returns `tail`'s exit code. A run reported green here was never green; `.gate-covered` was correctly never written |

The third was mine, and it is the round's own subject: a proxy read in
place of the thing it stands for.

## Agents

Eight runs — four `implementer`, four `verifier`, all on `sonnet`.

| | |
|---|---|
| implementer | 4 tracks, every one held at least once, two held twice |
| verifier | 4 runs; three findings no diff-reading could reach |

The three findings that needed a constructed case rather than a read:
`UX-766`'s compounding force, `UX-767`'s meaning-reversal with the
citation intact, and `UX-763`'s 10-line commit body — which was
invisible in the diff and in the Outcome, and showed up only by running
`tools/dev_commit_bodies.py`, the tool CI runs.

Rows in [`agent-runs.md`](agent-runs.md), derived by
`dev_track_cost.py --ledger`.

## Filed, not fixed

`UX-771` — `verify/SKILL.md` and `decompose/SKILL.md` number sections
with the same convention and are cited the same way, and remain outside
the collision guard `UX-763` widened. Three of the five documents that
number sections are read.
