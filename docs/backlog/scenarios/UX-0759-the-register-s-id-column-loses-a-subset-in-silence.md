# UX-759: the register's id column loses a subset in silence

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-744 (the register and its pin) | **Serves:** the round that reads the register to learn what an earlier round closed | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-744` closed the case where a round's ids go *entirely* missing:
`DASH_ROUNDS` pins today's two `—` rows, so a round that empties reds
whichever layer ate it. Its verifier then found the boundary — drop
*some* of a round's ids and nothing notices:

```console
$ # commit_signal() drops 3 of round 90's 11 ids, then --write
$ grep '^| 90 |' docs/audits/round-register.md
| 90 | 2026-09-05 | UX-665, UX-666, UX-667, UX-669, UX-670, UX-672, UX-673, UX-674 |
$ python3 -m pytest tests/unit/test_a_run_is_priced.py -q
33 passed in 0.88s
```

A truncated, wrong id list commits with every guard green, because
both checks only look at rows that go fully empty.

**A fourth source exists and the tool does not read it.** Round 85's
`—` is not unknowable the way round 64's is. Its commit reports
*"Eighteen rows closed"* by count, but `docs/audits/round-85.md`'s own
Decomposition table names all eighteen — `UX-604, UX-610, UX-612,
UX-613, UX-614, UX-615, UX-616, UX-617, UX-618, UX-619, UX-620,
UX-621, UX-622, UX-623, UX-624, UX-625, UX-626, UX-627` — matching
the count exactly. `UX-744`'s three declared sources are `closed.md`,
the commit, and the ledger; `round-N.md` was never one of them.

## Required Fix

1. Read each round's own document as a fourth source, so a round that
   names its ids in a table is not recorded as `—` because its commit
   message did not repeat them. Round 85 stops being pinned.
2. Give the id column a check that catches a partial loss. Two ids
   attributable to a round from different sources disagreeing is the
   signal; a single best-effort regex over commit prose cannot be its
   own witness (`UX-744`'s whole independence finding).
3. **The inverse check:** drop a subset of one round's ids at the
   scan and confirm the new check reddens naming that round — the
   mutation above, which is green today.

## Out of Scope

- Round 64's `—`. It has no record anywhere in this branch's
  reachable history; a fourth source does not help it, and it stays
  pinned.
- The waiver for undocumented rounds, which is `UX-757`'s.
- Re-deriving the commit scan a second way. `UX-744` established that
  two implementations of one scan is the shape `UX-752` was filed on.

## Acceptance Test

The register carries round 85's eighteen ids from its own document,
`DASH_ROUNDS` names only 64, and the subset-drop mutation reddens
where today it reports `33 passed`.

## Outcome

_Not started._
