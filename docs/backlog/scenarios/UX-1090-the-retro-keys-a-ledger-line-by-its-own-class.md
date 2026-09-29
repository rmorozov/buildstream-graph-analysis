# UX-1090: the retro keys a ledger line by its own class, and "none reported" is no finding

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-999 | **Blocks:** — | **Found by:** round 149 — the first weekly retro, `docs/audits/retro-2026-09-28.md`, proposal 1 | **Serves:** every weekly retro, whose top class is its whole output | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`python3 tools/dev_retro.py` read 158 findings for 2026-09-21..28 and left
143 (90.5%) unclassed, so the table named no top class. 7 of the 15
bookkeeping-ledger lines read unclassed though each carries a `class`
field; the tool keys by a command token instead. 117 of 117
`agent-runs.md` friction cells read unclassed, and 19 of them are
"none reported", counted as findings.

## Required Fix

A bookkeeping line is keyed by its own `class` field. A friction cell
that reports nothing is not a finding. A friction cell is keyed by the
agent and the command it names, or left out of the classed count with
its own line saying so.

## Out of Scope

The retro skill's proposal step; the ledger's format.

## Acceptance Test

`dev_retro.py` on the 2026-09-21..28 window reads 0 of 15 ledger lines
unclassed and no "none reported" cell as a finding. Mutation: key the
ledger line by command again, and the guard reds.

## Decision

The `architect`, round 149, at `c324f250`.

```text
Route:     tools/dev_retro.py keys a bookkeeping line by its `class` field (a named group in
           BOOKKEEPING_LINE); a friction cell reporting nothing (`none reported`, `none`, `-`,
           `—`, empty: 70 cells today) is no finding; a cell naming a token keys as
           `<agent> · <token>`; a cell with none goes on its own `friction without a command: N`
           line, outside the classed/unclassed count
Rejected:  token first, class as fallback - the class is the stated key (7 of 15 unclassed)
           a class inferred from friction prose - a proxy (fixing guide §5)
           a ledger format change - Out of Scope
Files:     tools/dev_retro.py; tests/unit/test_a_retro_keys_a_ledger_line_by_its_own_class.py (new);
           tests/unit/test_a_retro_groups_bookkeeping_by_the_command_that_shows_it.py
           (retire TestOneClassAcrossTwoSources, TestNoTokenIsUnclassed: they assert the token key)
Guard:     the new file on a scratch repo: a coverage line with no token reports under
           `coverage`, `unclassed: 0 of 1`; `none reported` and `—` rows add 0 findings;
           `implementer | ... | tools/dev_probe.py drifted` reports under `implementer · tools/dev_probe.py`
Mutation:  key by class_key(line) again -> (a) reds; drop the nothing-reported filter -> (b) reds
Class:     bookkeeping (cap lifted for r149)
Split:     one track, parallel with UX-1091
Question:  none
```

## Outcome

Gap measured: before the fix, `bookkeeping_findings` keyed every line by
`class_key(line)` (the first `tools/dev_*.py`/`tests/unit/test_*.py`/
`` `make <target>` `` token), so 7 of 15 in-window ledger lines read
unclassed though each carries a `class` field, and every ledger friction
cell - including "none reported" - counted as a finding.

Close measured: `BOOKKEEPING_LINE` now names a `class` group and
`bookkeeping_findings` keys on it; `ledger_findings` drops a cell in
`NO_FINDING` ("none reported", "none", "-", "—", "") before counting,
keys a tokened cell as `<agent> · <token>`, and reports a cell with
neither as `friction without a command: N`, outside the classed/
unclassed total.

```text
$ python3 tools/dev_retro.py
since 2026-09-21: 42 finding(s)

classes by count:
  coverage                                    9
  brief                                       4
  doc-drift                                   2
  fail-open                                   1
  make lint                                   1
  make test                                   1
  tests/unit/test_a_bookkeeping_finding_is_one_line.py    1
  tests/unit/test_a_derived_figure_is_printed_not_committed.py    1
  tests/unit/test_docs_links_and_commands.py    1
  tests/unit/test_the_context_map_is_the_tree.py    1
  tests/unit/test_the_documents_keep_up_with_the_contracts.py    1

unclassed: 19 of 42 (45.2%)
friction without a command: 86

bookkeeping lines per ISO week:
  2026-W39   15
  2026-W40   1
```

The bookkeeping source alone (`bookkeeping_findings`, direct call): 16
findings in-window, 0 unclassed - the extra line past the Acceptance
Test's 15 is round 149's own retro filing (`c324f250`, dated
2026-09-28, inside the window), landed after the Decision's count was
taken; it carries a `class` too, so the reading is still 0 unclassed.

Mutation table:

| mutation | reddens | run |
|---|---|---|
| (a) key bookkeeping by `class_key(line)` again | `TestABookkeepingLineWithNoTokenKeysByItsClass` | 1 failed, 3 passed |
| (b) drop the `NO_FINDING` filter before counting | `TestNoFindingFrictionCellsAddNothing` | 1 failed, 3 passed |

**Deviation (integration, r149).** `dev_sizes.py --check` read red after
the merge: `tools/dev_retro.py` grew past its reference cell (24 -> 27
functions, 186 -> 207 lines) from this change's own new helpers.
`--adopt` refused upward; the integrator re-ran `--adopt --force`,
writing the 2 grown cells (both `dev_retro.py`) - nothing else moved.
