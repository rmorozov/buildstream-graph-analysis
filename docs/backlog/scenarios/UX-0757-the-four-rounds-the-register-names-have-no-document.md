# UX-757: the four rounds the register names have no document

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-744 (the register and its waiver), UX-666 (the guard) | **Serves:** the reader who cannot see what rounds 99..102 launched | **Topic:** docs | **Area:** unassigned | **Shape:** bounded

## Motivation

`UX-744` built the register and extended `UX-666`'s guard to read it.
Four registered rounds carry no document, so the guard ships with a
dated waiver naming exactly them:

```python
UNDOCUMENTED_ROUND_WAIVER = {
    "99": ("2026-09-07", "UX-757"), "100": ("2026-09-07", "UX-757"),
    "101": ("2026-09-07", "UX-757"), "102": ("2026-09-07", "UX-757"),
}
```

The waiver is the point: it is green today and reds the moment a
*fifth* round goes undocumented. But four rounds of real work have no
record a later round can read, and `UX-744`'s Out of Scope said to
file the archaeology once the register could name them. It can.

The register gives the material:

```text
| 99  | 2026-09-06 | UX-719, UX-729, UX-732, UX-733 |
| 100 | 2026-09-06 | UX-735, UX-736 |
| 101 | 2026-09-06 | UX-728, UX-738 |
| 102 | 2026-09-06 | UX-667 |
```

## Required Fix

Write `docs/audits/round-99.md` through `round-102.md`, each carrying
the `## Agents` table `UX-666` requires, derived from the ledger where
the ledger has rows and stated as absent where it does not — rounds 99
and 101 have no ledger row at all, which is itself the finding for
those two.

Then remove the four waiver entries. The guard must go green because
the documents exist, not because the waiver still covers them.

## Out of Scope

- Rounds 64 and 85, whose `—` rows are `UX-759`'s subject, not this
  row's. This row writes documents for rounds that have ids.
- Rounds 96, 97 and 98. They do not exist; `UX-744` established that
  from three sources and the register correctly omits them.
- Changing the waiver mechanism. It works and it is what made this
  row filable.

## Acceptance Test

Four documents exist, `UNDOCUMENTED_ROUND_WAIVER` is empty, and
`test_it_carries_a_document_or_is_waived` is green for every
registered round on its own merits. Mutation: delete any one of the
four and the guard reds naming that round's number.

## Outcome

**The gap measured.** `docs/audits/round-*.md` jumped 95 -> 103;
`docs/README.md`'s and `docs/design/directions.md`'s round runs did
the same. `UX-744` (the register, `UNDOCUMENTED_ROUND_WAIVER`,
`test_it_carries_a_document_or_is_waived`) was built (`cbe1ccf`) and
reverted (`d34fb95`); none of it exists in this tree, so this row was
worked against the guard that predates it, `tests/unit/test_a_run_is_priced.py`.

**The close measured.** Four documents written from `closed.md` rows,
`git log` over each round-marker range, and `agent-runs.md`'s own
rows:

```console
$ ls docs/audits/round-9[9]*.md docs/audits/round-10[0-2].md
docs/audits/round-100.md  docs/audits/round-101.md
docs/audits/round-102.md  docs/audits/round-99.md
```

Round 99: three judgements, no track (`grep "^| 99 " agent-runs.md` →
nothing; no `merge the track` commit in range). Round 100: five ledger
rows, self-confirmed by `9798abe`'s own commit body. Round 102: five
ledger rows (`UX-667`, `UX-691`, `UX-702`, `UX-712`, `UX-703`), the
`af56022` "gate" a checkpoint inside the round, not its edge. Round
101: seven ids closed by a track merge each (`UX-728`, `UX-737`,
`UX-738`, `UX-717`, `UX-716`, `UX-692`, `UX-677`), zero ledger rows —
`3805321` names "round 101's four" transcripts as unrecoverable and
declines to guess a row; this document's own count is seven, and the
record does not resolve the difference (stated in `round-101.md`,
unresolved, and left that way).

**`docs/design/directions.md`'s Round history table** — not owned by
a sibling this round; four rows added beside `round-95` and
`round-103`.

**Round 101's guard, closed with a waiver, not left red.** First
pass: checked the guard's code for a second accepted value beyond the
literal `"no agents launched"` substring — none exists in either
assertion — and for the ledger's `"—"`/`"cut, re-run"` convention,
which predates `3805321` and was already declined there on purpose;
reusing it would override that decision with no new evidence. Second
pass, on direction: `UNPRICEABLE_ROUND_WAIVER = {"101": ("2026-09-07",
"3805321: transcripts unrecoverable after a context rebuild, a
guessed row worse than a missing one")}` added to
`tests/unit/test_a_run_is_priced.py`, read by both
`TestEveryRoundDocumentPricesItsAgents` clauses — the `DASH_ROUNDS`
idiom: the reason is the tuple's second element, the comment above it
one line naming the mechanism. `round-101.md`'s own text is unchanged.

**The mutation table.**

| mutation | what it reddened | count |
|---|---|---|
| delete `round-99.md` (pre-waiver guard) | nothing — the population silently shrank, reproducing the Motivation's own defect live | `28 passed`, restored |
| add `round-999.md`, an `## Agents` heading with no table, not in the waiver | both clauses, naming round 999 | `2 failed, 29 passed`; removed, back to `30 passed` |
| round 101, same run, waiver in place | passes both clauses throughout | `30 passed` |

```console
$ python3 -m pytest tests/unit/test_a_run_is_priced.py -q
30 passed in 0.19s
$ python3 -m pytest tests/unit/test_the_round_history_names_every_audit.py -q
8 passed in 0.15s
```
