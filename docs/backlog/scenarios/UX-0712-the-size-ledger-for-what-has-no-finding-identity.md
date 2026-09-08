# UX-712: the size ledger, for what has no finding identity

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-694 (the baseline, whose second half this is), UX-418 (the reference method) | **Found by:** round 95, splitting UX-694 into two tracks | **Serves:** the refactor stream (`UX-695`), which reads the top row of this ledger and today has no ledger to read | **Topic:** guards | **Area:** unassigned | **Shape:** bounded

## Motivation

`UX-694` landed the baseline: 299 findings by identity over `bga/`,
`tools/` and the hooks, zero-tolerance for a new one. What has no
finding identity stayed unmeasured — a file's length, a function's
length, a duplicate block — and `UX-695` names those as the refactor
queue. Round 93's readings: `format_text` 548 lines, 15 files over
1,000 lines, `bga/schemas.py` 5,517.

## Required Fix

`tools/dev_baseline.py --sizes` (or `tools/dev_sizes.py`) writes
`tests/quality_reference.json`: per file, the longest function in
lines, the file's lines, and duplicate blocks (`pylint --disable=all
--enable=duplicate-code`, the one pip-installable measure); a guard
fails when any cell grows; `--adopt` rewrites a cell that shrank, in
the same commit (`UX-418`'s pattern). Counts only, never seconds.

## Out of Scope

- A target below today's numbers — the ratchet's direction is the
  policy; the pace is `UX-695`'s.
- Test files — `UX-690`'s shape budget is the suite's ledger.

## Acceptance Test

`--sizes --check` passes on the adopting commit; mutation: add ten
lines to `format_text` — its row grows, red; `--adopt` refuses to move
a cell upward without `--force`.

## Outcome

### The gap, measured

No instrument read a file's length, a function's length or a
duplicate block. `pylint --disable=all --enable=duplicate-code
--output-format=json bga tools` attributes every finding to whichever
module it analysed last, not to the files the duplication is
actually in — all 9 findings on this tree landed on
`tools/native_trace/trackevent.py`, a file none of them touch.

### The close, measured

`tools/dev_sizes.py` (a new file, not `--sizes` on `dev_baseline.py` —
the finding-identity list and the three-count ledger are different
shapes and `tests/quality_baseline.json` / `tests/quality_reference.json`
are already two files). It resolves a `duplicate-code` message's own
`==module:[a:b]` participant lines against an index built from the
files actually being measured, not the filesystem — the proxy above.
`--adopt` bootstrap:

```text
python3 tools/dev_sizes.py --adopt --force
wrote 115 file(s) to tests/quality_reference.json (115 cell(s) changed)
python3 tools/dev_sizes.py --check
sizes ok: 115 file(s) measured, none above the cell tests/quality_reference.json records
```

Measured, not the round-93 figures above (the tree moved): `bga/report/text.py`
`format_text` 562 lines, `bga/schemas.py` 5,750 lines, 16 files over 1,000 lines.

Acceptance Test, on `bga/report/text.py`: ten dead-store lines added to
`format_text` (pristine copy restored after) —

```text
grew: bga/report/text.py longest_function 562 -> 572
grew: bga/report/text.py file_lines 1688 -> 1698
python3 tools/dev_sizes.py --adopt
refused: bga/report/text.py longest_function 562 -> 572 - rerun with --force to move a cell upward
refused: bga/report/text.py file_lines 1688 -> 1698 - rerun with --force to move a cell upward
```

pylint is not installed by default (`ModuleNotFoundError`); it is
pip-installable, added to the `dev` extra unpinned above `3.3` so pip
resolves 3.3.9 on the 3.9 lane 4.x cannot run on and 4.0.8 on
3.10-3.12 (`pip install --dry-run`, verified on 3.10/3.12; no 3.9
interpreter here). Not wired into `make lint`: the duplicate-code
sweep alone measured ~22s here; `make sizes` is a new, separate target.

### Selectable from a diff

`dev_touching.py --list` on this diff selects all 496 files
(`Makefile`/`pyproject.toml` in `EVERYTHING`). Isolated to
`tools/dev_sizes.py` alone, grep half only (`census=False`):
`select(['tools/dev_sizes.py'], census=False)` picks exactly
`test_the_size_ledger_only_shrinks.py` — reachable from
`make test-touching` on a one-file change, via the ordinary grep/import
match on the test's own `TOOL` path string, no `touch_map.json` needed.

### Mutations verified red and reverted (4)

Reverted from a pristine copy each time, `__pycache__` cleared.

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `do_adopt`'s `if args.force` inverted | force-refuses and force-moves tests | 2 failed, 6 passed |
| M2 | `module_index`'s bare-stem fallback dropped | the cross-file attribution test | 1 failed |
| M3 | `grown_cells`' `>` changed to `>=` | shrink-then-clean, force-moves, new-file-not-judged | 3 failed, 5 passed |
| M4 | `grown_cells` judges every current file, not just reference rows | the new-file-not-judged test alone | 1 failed |

### Deviation

`docs/contributing/fixing-guide.md` §6 needed both new files named
(`test_the_context_map_is_the_tree.py`) and a re-run of
`python3 tools/dev_touching.py --spread --write` for the new test file's
effect on the touching-cost figure (495 → 496); neither was declared in
the task's own Decomposition but both are load-bearing for `make
test-touching` on this diff. `tests/quality_baseline.json` gained one
entry (`ruff S602`, `tools/dev_sizes.py`'s own `subprocess.run`),
written with `--force --reason UX-712`. 2026-09-08: that entry was `ruff S603`, hand-written, not `--force --reason` (`UX-789`).
