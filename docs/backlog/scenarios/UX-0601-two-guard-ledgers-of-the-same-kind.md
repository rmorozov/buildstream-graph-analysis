# UX-601: two guard ledgers of the same kind, two mechanisms

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-582 (§7's ledger), UX-585 (the card's markers) | **Serves:** the next session asked to add a rule and its guard | **Topic:** docs

## Motivation

Round 83 built the same thing twice, three days apart in the same
round, and the two do not agree on how:

```text
docs/design/styleguide.md §7      guard ledger, read by a §N citation in the guard's text (UX-582)
docs/contributing/rules.md        guard column, read by a `holds:` marker line (UX-585)
```

Both hold "this document's row names a guard, and that guard is about
this row" both ways. One infers the link from prose the guard happens
to contain; the other from a declared marker. The marker is the
stronger of the two — it cannot be satisfied by a passing mention —
and the citation is the cheaper.

## Required Fix

Decide, and write the decision down: either §7 adopts markers, or the
difference is argued in one paragraph naming why a citation is right
for a page's visual contract and a marker for a process rule. A
guard reads whichever is chosen, so a third ledger cannot invent a
third mechanism.

## Out of Scope

- Rewriting either ledger's content — both were measured this round and hold.

## Acceptance Test

Mutation: a new ledger row linked by neither mechanism — red naming
the convention it skipped.
