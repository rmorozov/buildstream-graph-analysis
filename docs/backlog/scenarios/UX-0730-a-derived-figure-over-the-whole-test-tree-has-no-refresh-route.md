# UX-730: a derived figure over the whole test tree has no refresh route

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-716 (the same class, in the timing mechanism), UX-662 (which retires the map's readers), UX-336 (the selector) | **Serves:** every round that adds a test file, and the branch that pays for it | **Topic:** guards | **Shape:** bounded | **Area:** tools

## Motivation

Round 98 went red on CI across four Pythons and three shas, with the
suite otherwise green (7441 tests recorded, 2 failures):

```text
FAILURE test_the_cost_row_is_derived_from_the_selector
        TestTheDocumentsCarryTheComputedFigure::test_each_cost_line_carries_the_figure
        docs/contributing/fixing-guide.md: 0 line(s) price the loop at
        '13-127 of 490 test files, median 19', expected 2
```

The cause is two new guard files:

```console
$ python3 tools/dev_touching.py --spread --write
13-127 of 491 test files, median 19          # the guide said 489
```

**The selector cannot reach it.** `select()` greps every test file for
each *changed path*, so this guard is chosen when
`tools/dev_touching.py` or `docs/contributing/fixing-guide.md` changes.
Its verdict, though, depends on the size of `tests/`, and adding
`tests/unit/test_an_aliased_import_is_refused.py` is not a change to
anything the guard names. The `selector-before-commit` hook therefore
passed on all four commits that invalidated it, and CI paid.

**The class has at least four members, measured.** Round 98 hit it
twice more, hours apart, through a *task file* rather than a test file:
`UX-727`'s text was edited to derive `bounded` while its header still
said `judgement`, and four guards that read the whole backlog went red
on CI while the hook stayed green. What one task-file change selects:

```console
$ python3 -c "from tools.dev_touching import select; \
    print(len(select(['docs/backlog/scenarios/UX-0727-….md'])[0]))"
13                                         # the census floor, and nothing else
  test_a_task_declares_its_shape.py                    not selected
  test_the_loop_stays_fast.py                          not selected
  test_the_fast_check_holds_what_the_suite_holds.py    not selected
  test_the_cost_row_is_derived_from_the_selector.py    not selected
$ pytest <those four> -q
84 passed in 13.05s
```

Four guards, 13.05 s together. `UX-716` says to decide between its two
routes on how many guards are in the class — "if it is two, the first
route is cheaper; if it is twenty, the second is". Four is the count so
far, and all four are reachable by one declaration
(`docs/backlog/scenarios/` and `tests/`), which argues for the
declare-the-population route over normalising each reading.

This is `UX-716`'s class in a second mechanism. There it is *recorded
seconds* decaying as a population grows; here it is a *derived figure*.
Same shape, different currency, and neither `UX-662`'s retirement of
the map's readers nor the census floor covers it.

**Half the mechanism already exists, and this row was filed without
knowing it.** `test_the_selector_carries_the_census`'s
`TestTheDeclarationIsTheDerivation` derives exactly this class and
requires its members in `CENSUS` — it caught `UX-713`'s new guard on
CI in this same round:

```text
AssertionError: 1 guard(s) walk the repository tree and no grep selects
them, so they run only if listed in tests/tiers.py's CENSUS:
['tests/unit/test_every_skill_directory_is_named_in_claude_md.py']
```

It detects a *directory walk*, by AST:

```python
WALKS = {"glob", "rglob", "iterdir", "walk", "listdir", "scandir"}
```

The four guards measured above walk nothing. They read **named index
files** (`README.md`, `closed.md`, the fixing guide) or shell out
(`git ls-files`, `dev_touching.py --spread`), so their population is
just as wide and the derivation cannot see it. That is the gap, and it
is narrower than "build a mechanism": the mechanism is built and its
*detector* is too literal.

## Required Fix

The census floor (`tests/tiers.py`'s `CENSUS`, the 13 files that run
under every mapped module) is the obvious home, and the judgement is
whether it is the *right* one: `select(census=False)`'s docstring says
the census is "which guards a grep can never reach", and this guard is
reachable by grep — for its readers, not for its population. Either
the census's definition widens to "a grep cannot reach it *for every
input it has*", stated where `CENSUS` is declared, or a guard declares
the population it derives from and a run that changes that population's
size selects it — which is `UX-716`'s first candidate route and would
serve both rows with one mechanism.

Decide with the measurement `UX-716` asks for: how many guards are in
the class. If the two rows have the same members, build the mechanism
once and close both.

## Out of Scope

- The figure re-derived in this round to unblock CI (489 → 491).
  Declined as the fix for the same reason `UX-716` declined its own
  hand-refresh: it buys one round, not the property.
- Making `make test-touching` run everything. `UX-336` sized the
  selector against exactly that, and `UX-605` bounded it.

## Acceptance Test

A commit that adds a test file and nothing else selects the guards
whose figures are derived from the test-file population. Mutation: add
an empty test file, run the selector — the cost-row guard is in the
selection and reds before the commit lands.

## Outcome

**The gap, measured.** `test_the_selector_carries_the_census.py`'s
`_walks_the_repo` is an AST check for `WALKS` in the guard's own file;
none of the four guards this row's Motivation names call `.rglob`/
`.glob` themselves — they call a tool function (`dev_touching.spread`,
`dev_close_task.shape_disagreements`) that does. `derived` never saw
them, so `test_every_derived_census_guard_is_declared` stayed green
while they stayed unselectable.

**The close, measured.** Added `_delegates_a_population()`: a curated
`POPULATION_DELEGATES` of six tool functions (`spread`, `test_files`,
`touch_map`, `table_statuses`, `backlog_files`, `shape_disagreements`),
each verified by its own source in
`TestPopulationDelegatesActuallyDelegate`, matched against a guard's
imports regardless of `reachable` — the event that invalidates these
(a file added elsewhere) is not one `_sources()` (bga/tools diffs) ever
asks about. Running it against the real tree:

```console
$ python3 -m pytest tests/unit/test_the_selector_carries_the_census.py -q
22 passed
```

5 guards newly declared: the 4 named plus `test_docs_links_and_commands.py`
(same rule, same tool functions, named in this row's own sibling
guard's docstring). `CENSUS` 14 → 19; `HANDFUL` 28 → 33 and
`CENSUS_FLOOR` 14 → 19 (`test_the_loop_stays_fast.py`, same "+14 of
your own" arithmetic prior rounds used); the cost row itself moved
(`19-131 of 495 test files, median 25`, refreshed via `--spread
--write`). `make test-touching`: `7372 passed, 126 skipped in 473.04s`.
`make lint`: clean.

**Deviation, loud.** The gap description named a second mechanism -
shelling out (`git ls-files`, `pytest --collect-only`) - and building
that detector too surfaced **13 further pre-existing guards** this
row's own "at least four" undercounted (`test_a_counted_figure_is_derived.py`,
`test_a_guard_ledger_names_its_link.py`,
`test_a_guard_that_reads_history_declares_its_depth.py`,
`test_every_invariant_has_a_guard.py`, `test_every_part_has_a_guard.py`,
`test_the_environment_surface_is_an_inventory.py`,
`test_the_process_documents_derive_their_figures.py`,
`test_the_python_floor_is_a_guard.py`,
`test_the_roles_table_names_who_serves_it.py`,
`test_the_round_history_names_every_audit.py`,
`test_the_styleguide_names_its_guards.py`,
`test_the_tiers_are_a_partition.py`, `test_docs_links_and_commands.py`'s
own `--collect-only` clause). Migrating all of them would move `CENSUS`
14 → 31 and `HANDFUL` 28 → 45 - a >2x jump past what this row's own
Motivation measured, and a real ongoing cost to every `test-touching`
run. That is a population-migration decision, not a mechanical one, so
this close ships only the named-index-file/delegate half and leaves
the subprocess half undetected — narrower than the gap description,
named here rather than silently absorbed. Recommend a follow-up row.
`test_the_touching_map_is_measured.py`'s `touch_map()` call is a
detector false positive (exercises the empty-map fallback under
`monkeypatch.setattr(dev_touching, "TESTS", tmp_path)`); excluded via
`DELEGATED_UNDER_A_FIXTURE`, the same shape as `NOT_A_TREE_WALK`.

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| new guard file calling `dev_touching.spread()`, absent from `CENSUS` | `test_every_derived_census_guard_is_declared` | 1 failed |
| `POPULATION_DELEGATES = set()` (vacuity) | `test_the_set_is_not_empty`, `test_nothing_is_declared_that_does_not_read_the_tree` | 2 failed, 14 passed, 1 skipped |

Both reverted by hand-editing back (not `git checkout --`, which would
discard the uncommitted fix in the same file); both green after -
`test_the_selector_carries_the_census.py`: 22 passed.
