# UX-718: the census omits the guard its own docstring names

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-522 (the census set), UX-645 (the census floor) | **Serves:** anyone whose inner loop is `make test-touching` | **Topic:** guards | **Shape:** mechanical | **Area:** tools

## Motivation

`census_set()`'s docstring names three archetypes of the class, and
the list is missing the middle one:

```text
tools/dev_touching.py:86-88
    A census guard's subject is the **tree** - the register cap over
    every task file, the skip census over every guard, the context map
    over every module - so it names none of them and no diff can point
    at it.

tests/tiers.py:117-129   CENSUS, 11 entries
    test_the_register_is_terse.py          ✓ the register cap
    test_every_skip_reason_is_declared.py  ✓ the skip census
    test_the_context_map_is_the_tree.py    ✗ absent
```

Measured, not argued: adding `bga/utilisation/envelope.py` in `44d211f`
passed `make test-touching` at 104 files and **failed CI on all four
`test` jobs** —

```text
FAILURE tests.unit.test_the_context_map_is_the_tree.TestTheMapNamesTheTree
        ::test_every_module_is_on_the_map
        module(s) the context map does not mention:
        ['bga/utilisation/envelope.py']
```

A new module is exactly the diff that cannot name this guard: the guard
mentions no module, and the module is not yet in the map it checks. So
the one change that reddens it is the one change the selector cannot
select — `UX-522`'s own argument, on a file `UX-522` left out.

A second guard missed the same way, in the same round, before this item
closed. `test_a_committed_analysis_matches_the_analyzer.py`'s subject is
the **committed fixture population** - `tests/fixtures/golden/mixed_task_kinds`,
`tests/fixtures/with_timeline` - so it too names no module:

```text
FAILURE tests.unit.test_a_committed_analysis_matches_the_analyzer
        ::test_the_committed_document_is_the_one_the_analyzer_emits
        tests/fixtures/golden/mixed_task_kinds disagrees with a fresh analysis
```

`89b1ddf` added `utilization_envelope` to the analyzer's output and
reddened all four CI jobs after `make test-touching` passed locally at
251 files. Unlike the first miss, this guard does not glob or `rglob`
the tree at all — its population is a fixed pair of fixture paths, not
a directory walk — so it is not even the same AST shape as the first.

## Required Fix

`test_the_context_map_is_the_tree.py` joins `tests/tiers.py`'s `CENSUS`.
`test_the_selector_carries_the_census.py` derives the set rather than
auditing a typed list, so a fourth tree-walking guard added later is
not a fourth round of this.

## Out of Scope

- The other 480 guards. This item adds the one its own docstring
  names and closes the derivation gap that let it be missed; a sweep
  for further census candidates is a separate measurement.

## Acceptance Test

`python3 tools/dev_touching.py --why tests/unit/test_the_context_map_is_the_tree.py`
reports `census` on a diff naming no module; `git rm` a `bga/` module
and `make test-touching` reds without the module being named anywhere
in the diff. Mutation: drop the entry again — the derivation guard reds
rather than the list silently shrinking.

## Outcome

**Gap measured.** Both guards report `census` on a diff naming no
module (`--why --staged` on a docs-only change): `test_a_committed_
analysis_matches_the_analyzer.py <- ['census']`,
`test_the_context_map_is_the_tree.py <- ['census']`. `bga/units.py`
(named on the context map) moved aside and, with no module named in
any diff, `test_the_map_names_nothing_that_does_not_exist` reddened:
`the context map names path(s) that do not exist: ['bga/units.py']`.

**Close measured.** Both joined `tests/tiers.py::CENSUS` (11 -> 13),
each with the reddening commit sha as its `why`. Neither is `derived`'s
shape: the context-map guard's tree walk is `root.iterdir()` inside a
`def f(root=REPO):` default, invisible to the module-level-only scan —
fixed in `_walks_the_repo`. The committed-analysis guard globs nothing
at all (`refresh.FIXTURES` is a fixed pair); `NOT_A_TREE_WALK` says so
and a typed clause, not the derivation, is its argument.

**Mutation table.**

| mutation | reddens | count |
|---|---|---|
| drop context-map entry from `CENSUS` | `test_the_module_this_derivation_cannot_see_is_in_it` | 1/15 |
| drop committed-analysis entry from `CENSUS` | `test_the_second_miss_the_same_round_measured_is_in_it` | 1/15 |
| revert `_walks_the_repo`'s default-arg tracking | `test_nothing_is_declared_that_does_not_read_the_tree` (context-map) | 1/15 |
| empty `NOT_A_TREE_WALK` | `test_nothing_is_declared_that_does_not_read_the_tree` (committed-analysis) | 1/15 |

**Deviation.** Full auto-derivation (`derived`, condition: walks the
tree *and* no existing module's grep reaches it) does not extend to
either guard, and a second, differently-shaped miss in the same round
is evidence against one: the context-map guard is grep-reachable for
18 modules it already names as examples, so a *new* module's absence
is invisible to a boolean reachable/unreachable test; the committed-
analysis guard is not a tree walk at all - fixing `_walks_the_repo` to
recognise it would require a heuristic ("imports no bga/tools module")
that, checked against the whole suite, also flags 4 unrelated files as
missing census candidates - out of this item's scope to add. Both are
typed, with the reddening commit as evidence, matching the round-75
precedent already in this file. What a round should do instead of a
third instance: treat "reddened CI, passed `test-touching`" as a
standing check on close, not a derivation to keep re-deriving.

Left untouched, per the orchestrator's direction to confine this diff:
`tests/unit/test_the_loop_stays_fast.py` (`CENSUS_FLOOR`, `HANDFUL`,
`WIDE` all shift with `CENSUS`'s size), `docs/contributing/fixing-
guide.md`'s cost row (`test_the_cost_row_is_derived_from_the_selector.py`),
and the two now-unconditionally-run, already-stale golden fixtures
(`test_a_committed_analysis_matches_the_analyzer.py`, red before this
item touched anything) — all mechanical, all reconciled at merge.
