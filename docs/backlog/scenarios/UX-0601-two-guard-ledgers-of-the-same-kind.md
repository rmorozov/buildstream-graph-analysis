# UX-601: two guard ledgers of the same kind, two mechanisms

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-582 (§7's ledger), UX-585 (the card's markers) | **Serves:** the next session asked to add a rule and its guard | **Topic:** docs

## Motivation

Round 83 built the same thing twice, three days apart in the same
round, and the two do not agree on how:

```text
docs/design/styleguide.md §7      guard ledger, read by a §N citation in the guard's text (UX-582)
                                  33 rows · 22 name a guard · 34 distinct guard files
docs/contributing/rules.md        guard column, read by a `holds:` marker line (UX-585)
                                  30 rule rows · 11 name a tests/unit guard · 10 files · 9 marked
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

## Outcome (round 84, 2026-09-03) — 🔴 handed back for the close

### The gap, re-measured on `0bc5aff`

Both premises this round was handed were wrong, in the same direction:

```text
                                            handed    measured
styleguide.md §7 ledger rows                  34         33   (34 is the
                                                               distinct guard
                                                               *files*, not rows)
rules.md marker carriers, tests/unit/*.py     14          9   (10 marker lines;
                                                               1 deferred, UX-600)
```

The mechanisms hold as filed. What the numbers change is the *argument*:
the citation is not merely cheaper, it is the only link §7's rows can
carry cheaply, and the marker is the only link the card's rows can carry
at all.

```text
$ git grep -c "§" -- tests/unit/test_a_drawing_is_graded.py   # sample
tests/unit/test_a_drawing_is_graded.py:20
    :142  "a drawing was made without a grade; §2a says the call site "
$ git grep -c "rules.md" -- tests/unit/test_output_schemas.py
tests/unit/test_output_schemas.py:1        # the marker line, and nothing else
```

A §7 guard quotes its section id inside the assertion message — the
citation is prose that had to be there. A card guard names its rule
*nowhere* but the marker: the card's rows are sentences the document
numbers nowhere, so there is no id to cite and a mention would be an
accident. **Decision: keep both, and write the test for choosing.**

**Rejected: markers for all of §7.** 34 test files edited, against a
rule that already discriminates both ways, for a Low-priority item —
and it would delete the §7 citation from prose that reads better with
it. Declined.

### The close, measured

```bash
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_guard_ledger_names_its_link.py -q
7 passed in 0.15s          # 0.11s, 0.10s on two more runs
$ make test-touching
18 file(s) selected · 504 passed, 3 skipped in 8.98s
$ make lint
All checks passed!
```

### Mutations verified red and reverted

| mutation | reddened | run |
|---|---|---|
| **`rules.md` grows a row naming `test_blame_chain.py`, no marker** | `..._marker_ledger_is_linked_by_markers` — "is linked by a `holds: rules.md#<slug>` line … these name no such line" | 1 failed, 6 passed |
| **§7's `§3e` row also names `test_blame_chain.py`, no citation** | `..._citation_ledger_is_linked_by_citations` — "row §3e names test_blame_chain.py, which does not cite it" | 1 failed, 6 passed |
| **a third ledger: a `claim \| guard` table in `roles.md`** | `..._tree_has_only_the_declared_ledgers` — "`['docs/design/roles.md']`" | 1 failed, 6 passed |
| the rule declares the citation for both ledgers | 4 clauses, incl. "0 ledgers declare marker" | 4 failed, 3 passed |
| the choosing question deleted from the rule | `test_the_rule_asks_a_question` | 1 failed, 6 passed |
| the two declared links swapped | `..._stated_test_separates_the_two_ledgers` — "rules.md … rows carry no id to cite" | 3 failed, 4 passed |
| *vacuity:* the guard-column detector blinded | `test_the_scan_reads_a_population`, +4 | 5 failed, 2 passed |

Every clause discriminated; none had to be widened.

### Deviation from the Required Fix

- **None.** The Required Fix offered "§7 adopts markers **or** the
  difference is argued in one paragraph"; the second branch is taken,
  in `docs/contributing/style-guide.md` §15, with the guard.
- Not in the brief and edited anyway: `style-guide.md`'s header
  sentence, whose "Four … **Enforced by test**" is derived by
  `test_the_process_documents_derive_their_figures.py` and had to move
  to "Five". Its next sentence still said "The four are counted off" —
  a restatement the derivation does not read — now "That count".
- The task file is `UX-0601-two-guard-ledgers-of-the-same-kind.md`,
  not the `…-two-mechanisms.md` the brief named.
