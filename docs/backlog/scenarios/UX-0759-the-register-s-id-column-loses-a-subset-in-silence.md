# UX-759: the register's id column loses a subset in silence

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-744 (the register and its pin) | **Serves:** the round that reads the register to learn what an earlier round closed | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Superseded by UX-744's landed shape (2026-09-07)

Everything below describes a register with an **ids** column. The one
that landed has none:

```console
$ head -5 docs/audits/round-register.md | tail -2
| round | date |
|---|---|
$ grep -rn DASH_ROUNDS tests/unit/ tools/ | wc -l
0
```

`UX-744`'s verifier reached the same conclusion this row did — a
best-effort regex over commit prose cannot witness its own losses —
and the fix was to stop deriving ids rather than to guard them. So
clauses 2 and 3 have no column to check and `DASH_ROUNDS` no longer
exists; the Acceptance Test below cannot be run as written.

What survives is clause 1 in the **date** column: round 64 is still
`—`, and this row's own Out of Scope already declines it. `UX-772`
covers the adjacent defect that `document_date()` reads a first date
rather than a dateline. This row is therefore a **decline**, not a
deferral, and closes as one — the reasoning is kept because a later
round reading `UX-744` will ask why the ids column is missing.

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

**Declined — round 107.** `UX-744` landed a register the column this
row guards does not exist in.

**The gap, measured.** Both checks looked only at rows going fully
empty; dropping 3 of round 90's 11 ids left `33 passed`. That reading
stands and was never wrong.

**What closed it instead.** `UX-744`'s verifier reached this row's own
conclusion — a best-effort regex over commit prose cannot witness its
own losses — and the fix taken was to stop deriving ids, not to guard
them:

```console
$ head -5 docs/audits/round-register.md | tail -2
| round | date |
|---|---|
$ grep -rn DASH_ROUNDS tests/unit/ tools/ | wc -l
0
$ grep -c 'ids' tools/dev_round_register.py
1
```

The single `ids` hit is the module docstring saying why there is no
such column.

**The mutation table is empty and that is the finding.** Clause 3
asked for a subset-drop mutation over the id column. There is no
column, so there is nothing to mutate — a row whose acceptance test
cannot be *run* is declined, not deferred, and saying so is the
decision the fixing guide asks for rather than leaving it 🔴 forever.

**What survives, and where it went.** Clause 1 wanted `round-N.md` as
a fourth source. In the date column that need is real and `UX-772`
carries it: `document_date()` takes a document's first `YYYY-MM-DD`
whatever it means. Round 64 stays `—` and this row's own Out of Scope
already declined it — it has no record in reachable history.

**Deviation.** The whole Required Fix, declined rather than
implemented. The reasoning is kept above the Motivation rather than
deleted, because a round reading `UX-744` will ask why the ids column
is missing and this is the answer.
