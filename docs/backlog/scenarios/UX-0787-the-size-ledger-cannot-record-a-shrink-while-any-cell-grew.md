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

_Not started._
