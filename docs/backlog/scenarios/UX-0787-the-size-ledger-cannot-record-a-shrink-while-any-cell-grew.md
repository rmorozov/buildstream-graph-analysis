# UX-787: the size ledger cannot record a shrink while any cell grew

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-712 (the ledger), UX-418 (`--shrink`'s shape) | **Found by:** round 109, retro-verifying round 102 | **Serves:** the refactor that shrinks a function and cannot bank it | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`tools/dev_sizes.py` `do_adopt` computes the merged reference, then
`if blocked and not args.force: return 1` before `write_reference`.
Shrinking `.claude/hooks/no_bulk_add.py` by four lines on today's
`main`:

```console
$ python3 tools/dev_sizes.py --adopt
refused: .claude/hooks/no_bulk_add.py duplicate_blocks 0 -> 1 - rerun with --force ...
... (35 refusals)
$ git diff --stat tests/quality_reference.json
(empty)
```

The Required Fix said "`--adopt` rewrites a cell that shrank, in the
same commit", citing `dev_baseline.py --shrink`, which writes the
removals unconditionally and reports the growth separately. This
tool fused the two. And `--check` is red on a clean `main` — 34 grown
cells over 20 files — because nothing runs it: not `make lint`, not
CI. A ratchet nobody pulls is a number.

## Required Fix

Two decisions, both in the Outcome. First, `--adopt` writes every
shrink and exits 1 on the grows, `--shrink`'s shape. Second, whether
`--check` joins `make lint` after one `--adopt --force --reason
UX-787` that names today's 34 cells as the floor — or stays a weekly
job beside `UX-703`'s mutation run. Pick one and say why; a third
state (neither, red on main) is what this task closes.

## Out of Scope

- Lowering any cell below today's number — `UX-712`'s own Out of Scope,
  and `UX-695`'s refactor stream is where a cell moves down.

## Acceptance Test

Fixture with one file shrunk and another grown: the shrink is
written, exit 1, the grow named. Mutation: restore the early return —
red.

## Outcome

Two decisions taken: (1) `do_adopt` now writes `write_reference` for
every shrink and new-file row unconditionally, then names each grown
cell and exits 1 unless `--force` - `dev_baseline.py --shrink`'s
write-then-report order. (2) `--check` joins the GitHub-side shelf, a
new `sizes` job in `.github/workflows/quality.yml` beside `pip-audit`
(`pip install -e '.[dev]' pylint`), on the same `pull_request` and
weekly triggers as `codeql` - not `make lint`, so the inner loop stays
at ruff's wall time.

**Gap measured** (`main`, before this task, on today's tree):

```console
$ python3 tools/dev_sizes.py --check
grew: ... (39 cells, 27 files)
$ python3 tools/dev_sizes.py --adopt
refused: ... (39 refusals)
$ git diff --stat tests/quality_reference.json
(empty)
```

**Close measured**:

```console
$ python3 -m pytest tests/unit/test_the_size_ledger_only_shrinks.py \
    tests/unit/test_the_gate_only_shelf_is_on_github.py -q
16 passed
$ python3 tools/dev_sizes.py --adopt --force
wrote 121 file(s) to tests/quality_reference.json (46 cell(s) changed)
$ python3 tools/dev_sizes.py --check
sizes ok: 121 file(s) measured, none above the cell ... records
```

`tests/quality_reference.json` now names today's 121 files' cells as
the floor - a `UX-787` bank, not a shrink of the underlying code.

**Mutation table**

| mutation | reddened | count |
|---|---|---|
| `do_adopt`'s early `return 1` restored before `write_reference` (the pre-fix shape) | the new shrink-plus-grow fixture only | `1 failed, 9 passed` |
| the `sizes` job dropped from `quality.yml` | the four-jobs-on-both-triggers guard only | `1 failed, 5 passed` |
| `sizes`'s `run:` swapped for `echo skip` (verifier's gap: a job named `sizes` that runs nothing) | `test_each_shelf_job_names_its_tool`, naming `('sizes', ...)`, only | `1 failed, 6 passed` |

All mutations reverted from a saved pre-mutation copy (not
`git checkout`, since the fix is itself uncommitted); all suites
green again after. The third guard parses `quality.yml` with
`yaml.safe_load` (`import yaml` confirmed importable) and asserts each
shelf job's steps mention its tool - `sizes` → `dev_sizes.py --check`,
`pip-audit` → `pip-audit`, `codeql` → `github/codeql-action/analyze`,
`eslint` → `eslint` - so a job kept by name but emptied of its `run:`
reds.
