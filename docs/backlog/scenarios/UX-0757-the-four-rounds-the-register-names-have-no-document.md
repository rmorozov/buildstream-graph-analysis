# UX-757: the four rounds the register names have no document

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-744 (the register and its waiver), UX-666 (the guard) | **Serves:** the reader who cannot see what rounds 99..102 launched | **Topic:** docs | **Area:** unassigned | **Shape:** bounded

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

_Not started._
