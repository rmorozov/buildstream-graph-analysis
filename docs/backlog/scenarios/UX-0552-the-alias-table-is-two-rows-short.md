# UX-552: the CLI guide's alias table is two rows short

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Serves:** a reader looking up what `bga` can run | **Topic:** docs

## Motivation

Architecture review 12, checklist 4:

```text
docs/guides/cli.md:47-65   17 rows
bga --help                 19 aliases
absent from the table      timeline, view
```

Both have their own sections later in the same file, so the reader who
scrolls finds them and the reader who reads the table does not. Neither
is round 80's; the gap predates this review.

`docs/design/architecture.md`'s CLI table is guarded against `bga
--help` and is complete at 21 rows — this one is guarded by nothing,
which is the whole difference.

## Required Fix

Two rows, and the same derivation the architecture table has if it is
cheap: the table is `bga --help`'s alias block, so a guard can compare
them rather than a reader noticing.

## Out of Scope

- The per-command sections below the table: checked against `bga
  <name> --help` for both missing entries and both are current, so the
  gap is the table alone.

## Acceptance Test

The table's rows equal the alias block of `bga --help`, checked rather
than counted by hand.

## Outcome (round 81, 2026-09-03) — 🟢 Done

### The gap, measured

```text
$ python3 -c "from bga import tools_dispatch; print(len(tools_dispatch.TOOL_ALIASES))"
19
$ grep -c '^| `bga ' docs/guides/cli.md   # the alias table, before
17
absent: timeline, view
```

Both are `PROMOTED` in `test_the_command_table_is_the_cli.py` — the
architecture table carries them because a guard holds it against the
parser, and this one carried nothing because nothing read it.

### After

```text
$ python3 - <<'EOF'   # the acceptance test, both sides parsed
help block 19 rows 19 equal True
EOF
$ python3 -m pytest tests/unit/test_the_alias_table_is_the_help.py -q
4 passed in 0.16s
```

The population is `format_tool_help()` — the block `bga --help` prints
— not `TOOL_ALIASES`, so a change to how the block is rendered is
caught rather than walked past. Both directions and the module column.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| B1 | the `bga view` row deleted | 2 — `..._every_alias_the_help_lists_has_a_row`, `..._both_sides_were_actually_found` (18 rows against 19) |
| B2 | a phantom `bga retired` row added | 2 — `..._no_row_names_an_alias_that_does_not_exist`, `..._both_sides…` (20 against 19) |
| B3 | the `bga timeline` row made to claim `tools.bga_view` | 1 — `..._each_row_wraps_what_the_help_says_it_wraps` |
| B4 | a `brand-new` alias added to `TOOL_ALIASES` | 2 — `..._every_alias_the_help_lists_has_a_row`, `..._both_sides…` (19 against 20) |

B4 is the one that matters: it is the defect's own shape, an alias
shipping with no row, and it reddens from the code side. Reverted: 4
passed in 0.29s, with `__pycache__` cleared (`UX-508`).

No guard of mine failed to discriminate. Row **order** is deliberately
unchecked — the table and the block agree on rows and modules, and a
reordering that costs a reader nothing should not be a red test.

### Deviation from the Required Fix

None. The derivation the fix called "cheap if it is cheap" is a new
file, `tests/unit/test_the_alias_table_is_the_help.py`; it is untiered,
so it defaults to `small`, and `tests/tiers.py`/`ci_reference.json` are
untouched (`UX-503`).

```text
pytest (alias, docs-links, front-door, command-table, retired-contract)
                                  61 passed, 1 failed
make lint                          clean (ruff + PyMarkdown)
make test                          the orchestrator's gate; not run in this track
```

The failure is `test_the_table_status_matches_the_task_files`, and the
selector adds the two clauses that shell out to `dev_close_task.py
--check` (`test_the_loop_stays_fast.py`) for the same reason: this
track may not edit `README.md`, so both rows stay 🔴 against 🟢 files
until the orchestrator's `--move`. The commit is made with
`BGA_SKIP_SELECTOR=1` for that reason alone; 520 passed beside them.
