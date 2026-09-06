# UX-737: the census detector's other half — thirteen guards a subprocess hides

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-730 (which built the first half and measured this one), UX-716, UX-336 | **Serves:** the round whose CI reds on a guard its pre-commit hook could not select | **Topic:** guards | **Shape:** bounded | **Area:** tools

## Motivation

`UX-730` closed the delegated-population half of the census detector
and, in closing it, measured the half it did not build. Its Outcome is
the record; the figures are its, re-stated here so this row stands on
its own:

```text
shipped   (named index files / tool delegates)   CENSUS 14 -> 19
measured  (subprocess populations, not shipped)  CENSUS 14 -> 31
                                                 HANDFUL 28 -> 45
```

Thirteen further guards read their population by shelling out — `git
ls-files`, `pytest --collect-only` — so no path-grep selects them and
none is in `CENSUS`:

```text
test_a_counted_figure_is_derived.py
test_a_guard_ledger_names_its_link.py
test_a_guard_that_reads_history_declares_its_depth.py
test_every_invariant_has_a_guard.py
test_every_part_has_a_guard.py
test_the_environment_surface_is_an_inventory.py
test_the_process_documents_derive_their_figures.py
test_the_python_floor_is_a_guard.py
test_the_roles_table_names_who_serves_it.py
test_the_round_history_names_every_audit.py
test_the_styleguide_names_its_guards.py
test_the_tiers_are_a_partition.py
test_docs_links_and_commands.py  (its --collect-only clause)
```

`UX-730`'s track declined to absorb them, and was right to: taking
`CENSUS` past a doubling is a decision about what every
`test-touching` run costs from now on, not a mechanical consequence of
a detector. That decision is this row.

Note what the deferral means in the meantime: the detector now has a
name wider than its reach. It finds a guard that *delegates* and not
one that *shells out*, and a round adding the second kind still gets
no signal until CI. That is the `UX-730` gap, narrowed, not closed.

## Required Fix

Decide, with the cost measured on this tree rather than argued:

- **Migrate all thirteen.** `CENSUS` 31, `HANDFUL` 45. Measure what
  that does to a real `make test-touching` — the selector's own
  `--spread` gives min/median/p90/max — and say whether the daily loop
  can carry it.
- **Migrate the subset whose population actually moves often.** A
  guard reading `git ls-files` over `docs/backlog/` is invalidated by
  every close; one reading `pytest --collect-only` by every new test
  file. Rank by how often the population moved in the last hundred
  commits and take the head of that list, with the tail named and
  dated.
- **Make them selectable instead of resident.** A guard whose
  population is a subprocess could declare the paths it depends on, so
  the selector picks it up by path like everything else — no `CENSUS`
  growth at all. The most work, and the only route that does not tax
  every run.

Whichever is taken, the detector must stop being wider than its reach:
either it sees the subprocess kind, or its name and docstring say it
does not and `UX-730`'s deferral is closed with a dated note.

## Out of Scope

- `test_the_touching_map_is_measured.py`. `UX-730` established it is a
  detector false positive — it exercises the empty-map fallback under
  a `monkeypatch` — and excluded it via `DELEGATED_UNDER_A_FIXTURE`.
- The `POPULATION_DELEGATES` set itself. `UX-730` built and guarded it.

## Acceptance Test

Either the thirteen (or the chosen subset, named) are in `CENSUS` with
the loop cost re-measured and pasted, or the detector's name and
docstring are narrowed to what it reads and the gap is dated. Mutation:
add a guard that reads its population through `git ls-files` and is
absent from `CENSUS` — red under the first route, and under the second
explicitly out of the detector's stated reach.

## Outcome

**The gap, measured.** `_shells_out_for_a_population()` (AST) checks a
`subprocess.run`/`check_output`/`check_call`/`call` whose argv's first
two literal elements are `["git", "ls-files"]` with no
`--error-unmatch` (that names one file, not a population), or any argv
carrying `--collect-only`. Against the real tree this fires on 16
files; 4 already `CENSUS` (`test_a_guard_reads_only_what_a_clone_has.py`,
`test_docs_links_and_commands.py`, `test_the_agent_configuration_holds.py`,
`test_the_context_map_is_the_tree.py`), 12 new — exactly the thirteen
this row's Motivation named, minus `test_docs_links_and_commands.py`
which was already in. It does **not** flag `git grep`, `git log`,
`git ls-files --error-unmatch <path>` (a single-file check, 2 sites),
or a docstring/comment mention (5 sites) — the discriminator is the
call's own second argv element, not the word "subprocess", which about
200 guard files use for the CLI under test.

**The close, measured.** Migrated: the widened detector already forces
this, since `derived` (unfiltered by `reachable`, same argument as
`UX-730`'s delegate half) must be a subset of `CENSUS` or
`test_every_derived_census_guard_is_declared` reds. `CENSUS` 19 → 31.
`test_the_selector_carries_the_census.py`:

```console
$ python3 -m pytest tests/unit/test_the_selector_carries_the_census.py -q
25 passed
```

`HANDFUL` 33 → 45, `CENSUS_FLOOR` 19 → 31 (`test_the_loop_stays_fast.py`,
same "+14 of your own" arithmetic; `store_aggregate` measures 41 rather
than 45 because 4 of its 14 own files are now also census members —
`HANDFUL` keeps the stated formula, not the tighter measured bound).
`WIDE` lost one member, `bga/ingest/loader.py` (45 against the new 45,
no longer over); `bga/graph/edg.py` stayed (46, one over). Real
`make test-touching`:

```console
7382 passed, 126 skipped in 489.84s
```

31-file census run alone: `891 passed, 3 skipped in 24.19s` at `-n auto`
(`UX-730`: 19 files/716 tests/36.6s — seconds are the machine, `UX-551`,
not comparable). `make lint`: clean.

**Price paid, argued.** `CENSUS` grew 63% (19→31) in this row alone,
132% since `UX-730`'s own 14. The 12 are the guards round-75's own
argument already covers — a guard whose subject is the tree and no
grep reaches — so the alternative (leave them undetected) is the exact
gap `UX-522` was filed to close, reopened for a different mechanism.
Right price: yes, on the same grounds `UX-730` used for its five.

**Deviation, loud.** `test_the_cost_row_is_derived_from_the_selector.py`
reds on `docs/contributing/fixing-guide.md` — its cost-row sentence is
stale (`19-131 of 495…` vs. the new `31-143 of 495 test files, median
37`). Fixed by `python3 tools/dev_touching.py --spread --write`, but
that file is not a declared surface for this track and is not touched
here; the orchestrator's merge needs that one command before
`make test`.

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| new guard calling `subprocess.run(["git","ls-files",...])`, absent from `CENSUS` | `test_every_derived_census_guard_is_declared` | 1 failed |
| `SUBPROCESS_POPULATION_MARKERS = set()` (vacuity) | `test_the_set_is_not_empty` | 1 failed, 22 passed, 1 skipped |

Both reverted by hand-editing back (not `git checkout --`); both green
after — `test_the_selector_carries_the_census.py`: 25 passed.
