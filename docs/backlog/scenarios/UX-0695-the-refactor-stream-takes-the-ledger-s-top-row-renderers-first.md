# UX-695: the refactor stream takes the ledger's top row — renderers first

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the ledger) | **Serves:** the session that opens a round and has no refactor to pick because none is filed | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

§6a says what a refactor is and §6 how a round picks work; neither
says how a refactor gets *chosen*, so the stream has run zero times
against a tree with 84 functions over the threshold. The largest
bodies are renderers — `format_text` 548 lines (CC 135),
`format_compare_text` (CC 63), `build_document` 339 lines (CC 86) —
and renderers are the cheapest refactor in the tree: the golden
snapshot and the schema guards already judge that no behaviour moved.

## Required Fix

One sentence in §6a's refactor row: the candidate is the size ledger's
top row by longest function, and a round with two or more tracks
gives one to it. The first three tracks, filed here as the
acceptance: `format_text` split by section (one function per report
section, the section order a list), `build_document` the same,
`create_parser` split per subcommand. Each track's Outcome pastes the
ledger row before and after, and the golden diff (empty).

## Out of Scope

- `bga/schemas.py` (5,517 lines) — a contract surface; a split moves
  the `--schema` output's provenance and is a `UX-190` question, not
  a refactor.
- `tools/bst_native_build_tracer.py` (6,960 lines) — the tracer is
  hardware-adjacent and its suite runs on `bst`; a split is a capture
  track (`UX-536`'s neighbourhood), priced separately.

## Acceptance Test

After the first track: `tests/quality_reference.json`'s row for
`bga/report/text.py` shows the longest function under 80 lines; the
golden snapshot guard and `bga analyze --json` on every fixture
byte-identical to before; mutation: reorder two sections — the golden
reddens.

## Outcome

**2026-09-08, `create_parser` split (track 3 of 3).** `create_parser`
in `bga/cli.py` reduced to the top-level parser plus a walk over
`_SUBCOMMAND_BUILDERS`, one `_add_<name>_subcommand(subparsers)`
function per subcommand (13: analyze, graph, floors, replay, sweep,
utilisation, diagnostics, correlate, blast, whatif, cache-trend,
compare, bundle).

Ledger row (`tests/quality_reference.json`, `bga/cli.py`), before ->
after: `{"duplicate_blocks": 0, "file_lines": 2401,
"longest_function": 417}` -> `{"duplicate_blocks": 0, "file_lines":
2449, "longest_function": 214}`. `longest_function` shrank
417 -> 214 (`create_parser` itself is now ~15 lines; 214 is a
pre-existing function, `_compare_exit_code`, unrelated to this split).
`file_lines` grew 2401 -> 2449 (48 new `def`/blank lines from splitting
one function into fourteen); `dev_sizes.py --check` reds on that
growth, so `--adopt --force` moved the row (2 cells changed, only
`bga/cli.py`'s).

Help diff: every subcommand's `--help` plus the top-level `--help`
captured to files before and after the split with
`PYTHONPATH=<worktree> python3 -m bga.cli <cmd> --help`; `diff -rq
before/ after/` printed nothing (empty).

`make lint` reds on a stale forced-violation: ruff PLR0915 on
`create_parser`, no longer true once the function shrank.
`dev_baseline.py --shrink` removed the one stale entry
(`tests/quality_baseline.json`); `make lint` then clean (exit 0).

Mutation: dropped `_add_compare_subcommand` from
`_SUBCOMMAND_BUILDERS`. Reddened 9 tests naming `compare`:
`argument COMMAND: invalid choice: 'compare'` in
`tests/unit/test_compare.py` (8 tests) and `test_the_command_table_is_
the_cli.py::test_no_row_names_a_command_that_does_not_exist` (`the
table names ['compare'], which bga does not have`). Reverted from a
pre-mutation copy of the file; `test_compare.py` +
`test_cli_subcommands.py` + `test_the_command_table_is_the_cli.py`
green again (41 passed).

`make test-touching`: 147 files selected, 3322 passed, 72 skipped.
