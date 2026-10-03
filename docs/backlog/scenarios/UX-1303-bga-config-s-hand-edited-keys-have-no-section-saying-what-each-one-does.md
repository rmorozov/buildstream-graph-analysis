# UX-1303: `.bga/config`'s hand-edited keys have no section saying what each one does

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R8 | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_the_config_section_names_every_key_the_code_reads.py`

## Motivation

`builds_per_day` (`bga/build_rate.py:7`) prices the decision panel's
agent-hours a day, and appears in the guides only as a contract row
(`json-contracts.md:367`); `public_junctions` (`bga/run_store.py:508`)
is in no guide; the sticky `trace_opens`/`trace_spine` are mentioned in
passing (`cli.md:277`, `real-project.md:123`).

```text
$ grep -rln public_junctions docs/guides README.md | wc -l
0
$ grep -rn builds_per_day docs/guides | cut -d: -f1,2
docs/guides/json-contracts.md:367
```

## Required Fix

One `.bga/config` section in cli.md: every key a reader in `bga/`
reads, its default, who writes it and what it changes; real-project.md
links it. Also check `docs/design/roles.md`'s R8 row against `UX-1276`
and fix the cell if stale.

## Out of Scope

Nothing further.

## Acceptance Test

A guard collects the keys `bga/` reads from `.bga/config` and reddens
when the section misses one. Reading taken in this container.

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held — the four keys had no section; `public_junctions` was in no guide.

### The gap, measured

```text
$ grep -rln public_junctions docs/guides README.md | wc -l
0
$ grep -rn builds_per_day docs/guides | cut -d: -f1,2
docs/guides/json-contracts.md:367
```

### After

```text
$ grep -n '^| `\(builds_per_day\|public_junctions\|trace_opens\|trace_spine\)`' docs/guides/cli.md | cut -c1-40
(four rows, in "## `.bga/config`")
$ PYTEST_XDIST= python3 -m pytest -q -p no:randomly tests/unit/test_the_config_section_names_every_key_the_code_reads.py
3 passed
```

Keys come from an AST walk: `.get(<const or module constant>)` on
`read_config(...)`/`config`/`stored` in files using `run_store.read_config`,
plus the `defaults` dict in `bga_snapshot.py`. real-project.md links the section;
roles.md R8 was stale against `UX-1276` and its cell now names agent-hours a day.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | delete the `builds_per_day` row from cli.md | `test_every_key_the_code_reads_has_a_row`, 1 failed |
| A2 | add a `phantom_key` row | `test_no_row_names_a_key_nothing_reads`, 1 failed |
| A3 | `CONFIG_KEY = "builds_per_week"` in build_rate.py | all 3 failed |
| V1 | `cfg = run_store.read_config(".")`, `cfg.get("ghost_key")`, `cfg["ghost2"]` appended to build_rate.py (other name, subscript) | `test_every_key_the_code_reads_has_a_row`, 1 failed, misses ghost2, ghost_key |
| V2 | build_rate.py on `from .run_store import read_config` (3 passed), then `read_config(".").get("ghost3")` appended | `test_every_key_the_code_reads_has_a_row`, 1 failed, misses ghost3 |

### Deviation from the Required Fix

None. The R8 question moved from Out of Scope to the Required Fix at the session's request; the cell was stale and is fixed.
