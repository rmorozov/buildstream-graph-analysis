# UX-763: no document says what closing a round owes

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-744 (the register, reopened), UX-666 (the Agents table) | **Serves:** the session closing a round from memory because no list exists | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`CLAUDE.md`, `rules.md` and `fixing-guide.md` define a **task**'s
obligations exhaustively and a **stream**'s (`fixing-guide.md:465-490`).
None defines a **round**'s. The phrase "round document" appears once in
the three, at `fixing-guide.md:474`, and only as the audit stream's
output — not as something every round produces.

What a round actually owes is scattered, and only findable if you
already know where to look:

| obligation | where it is stated |
|---|---|
| a round document | nowhere, as a rule |
| its `## Agents` table | `UX-0666`'s Required Fix — a task file |
| a `docs/design/directions.md` history row | only as `UX-583`/`UX-591`'s guard |
| a `docs/README.md` link | the same guard |
| ledger rows | `CLAUDE.md:32`, per agent, not per round |
| `dev_close_task.py --check --write` | `decompose/SKILL.md:83-87`, as a batch's merge step |
| `dev_touching.py --spread --write` | `fixing-guide.md:69`, as a figure's owner |
| `CLAUDE.md`'s judgement/bounded split | nowhere |

Round 104 closed from a hand-assembled list and still missed two: the
history row and the README link, both caught by CI.

**The steps also have an order, and it is unwritten.** Appending the
ledger rows moved `CLAUDE.md`'s derived split and reddened its guard.
`UX-744` hit the same shape harder and says so in its own Outcome:
*"Regenerating last is the obvious answer — the index counts already
work that way (`UX-501`) — but the round document commit names the
round too, so 'last' has to be defined rather than assumed."*

**A fifth disagreeing record**, which `UX-744` did not count:
`docs/backlog/scenarios/README.md` carries narrative
`## UX-N..UX-M: the Nth round` headings through round 94 and none for
99..104, while `docs/audits/` has documents for 103 and 104.

## Required Fix

One section — in the guide, not a skill — that says what closing a
round requires and in what order, with the command for each step and
the reason the order matters. The ordering rule has to answer the
self-referential case `UX-744` named: a figure derived from the commit
history cannot be committed before the commits it must read.

Then either bring `scenarios/README.md`'s round headings up to date or
retire them, so the record stops disagreeing a fifth way.

**The gate's place in the order is now decided by a hook, and the
pipeline disagrees with it.** `UX-762` binds `make test` to the commit
that gets pushed. `CLAUDE.md:28` orders the round
`tracks -> verifier -> merge, one \u0060make test\u0060, close` — with **close** after
the gate, and close means the row moves, the derived counts, the ledger
rows and the round document. Every one of those is a commit, so on that
order the hook reds on the final push of every round, and the practical
response under time pressure is the escape hatch rather than a second
five-minute suite. `UX-762`'s verifier named this before it could bite:
the fix is correct for the sha mechanism and leaves the ordering
unresolved.

So the section this row writes must put **the gate last** — after the
closes, the ledger and the round document — or require a second run
after them. Round 105 closed itself that way and pushed with no
bypass, which is the reading to record.

## Out of Scope

- The register itself (`UX-744`, reopened) and the archaeology
  (`UX-757`). This row states the obligations; those two build the
  instrument that could check them.
- Retro-writing round documents for 99..102 — that is `UX-757`'s, and
  96..98 do not exist (`UX-744` established it from three sources).

## Acceptance Test

A session can close a round by following one list, and every item on
it names its command. Mutation: remove one obligation from the list
and the guard that owns it still reds — the list describes guards that
exist, it does not replace them.

## Outcome

**The gap, measured.**

```console
$ git show e8f3d58:docs/contributing/fixing-guide.md | grep -c "round document"
1
$ git show e8f3d58:CLAUDE.md | grep -c "round document"; git show e8f3d58:docs/contributing/rules.md | grep -c "round document"
0
0
$ git show e8f3d58:docs/backlog/scenarios/README.md | grep -n "^## UX-" | sort -t: -k1 -n | tail -1
1475:## UX-365..UX-373: the fifty-eighth round — the walk out to Perfetto (2026-08-28)
```

Highest narrative round heading is 94 (`UX-706..UX-711`, 2026-09-05);
this round is 106 — 11 rounds' headings never written, confirming the
Motivation's fifth disagreeing record.

**The close, measured.** `docs/contributing/fixing-guide.md` §7a
("Closing a round") lists the seven obligations in order, each with
its command and the guard that already owns it, and answers `UX-744`'s
self-referential case (a history-derived figure can't name the commit
that states it — solved by never letting step 2's "regenerate last"
pattern apply to anything that counts commits). `CLAUDE.md:28`'s
pipeline now reads `merge → close (... — fixing guide §7a) → one
make test, push`, gate last. `scenarios/README.md`'s round headings
are **retired**, not brought current: typing rounds 95-106's id
ranges and dates by hand is the disagreeing-record shape this row
exists to stop; a note at the table's end says so and points to
`UX-744`/`UX-757`; existing headings are unedited.

**Decisions this file did not already make, two caught by review:**
no `rules.md` line — the card is at its 80-line cap and the Required
Fix names no such line. The section collided twice, self-caught once:
first landed as `§4b`, which `docs/design/styleguide.md` already owns
(`4b`-`4f`), moved to `§8` and re-verified — but `docs/contributing/
style-guide.md` has its own real `## 8.`, invisible to `_ambiguous()`,
which only paired `STYLEGUIDE` against the union of the other two;
the orchestrator's review caught this one. Renamed to `§7a` (unused by
all three); `_ambiguous()` widened to pairwise overlap across all
three, and a new census guard (`TestTheIdSpaceGrowsNoSilentCollision`)
fails naming any id a future section repeats. Three of seven steps
named a tool and a `UX-` id with no guard file; all seven now name
one.

**Mutation table** (falsify skill; `/tmp` copies, reverted):

| mutation | guard | result |
|---|---|---|
| `README.md`: `**26 open**` → `**27 open**` | `test_the_index_counts_match_the_rows_they_index` | 1 passed → 1 failed → reverted, 1 passed |
| §7a's `## 8.` restored (`fixing-guide.md`) | `test_no_new_id_is_shared_across_the_three_documents` | 1 passed → 1 failed (names `'8'`) → reverted, 1 passed |
| §7a's item 2 bullet deleted, then the count mutation above, together | `test_the_index_counts_match_the_rows_they_index` | still 1 failed — reverted, 1 passed |

The third row is the Acceptance Test performed, not reasoned about:
with the obligation's own sentence gone from the guide, the guard
that owns it still catches the real violation.
