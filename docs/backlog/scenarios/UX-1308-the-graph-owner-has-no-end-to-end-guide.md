# UX-1308: the graph owner has no end-to-end guide

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R3 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_pasted_guide_block_is_fresh_or_dated.py` (existing; diffs every pasted block of `docs/guides/graph-owner.md`)

## Motivation

R3's tools - `junction-cost`, `cache-trend`, floors, blast, what-if -
are in cli.md; real-project.md covers blast, what-if and sweep, and no
guide walks a graph owner from a capture to a structural decision.

```text
$ grep -rl 'bga junction-cost\|bga cache-trend' docs/guides README.md
docs/guides/cli.md
```

## Required Fix

A section (or `graph-owner.md`) walking one example project through
the graph-only and duration findings, in the shape of `jobserver.md`.

## Out of Scope

New findings.

## Acceptance Test

The guide's commands run on a committed example (the pasted-block
guard holds them). Reading taken in this container.

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held - `grep -rl 'bga junction-cost\|bga cache-trend' docs/guides README.md` named `docs/guides/cli.md` alone.

### The gap, measured

```text
$ grep -rl 'bga junction-cost\|bga cache-trend' docs/guides README.md
docs/guides/cli.md
```

Two one-line stubs in cli.md; no document walked R3 from a capture to a decision.

### After

`docs/guides/graph-owner.md` walks `tests/fixtures/macro_micro/run` (no BuildStream needed) through width and chain-bound diagnosis, `bga graph`, `bga floors`, `bga blast`, `bga whatif`, `bga junction-cost` and `bga cache-trend`, 8 pasted blocks, each diffed by the existing guard; linked from the `docs/README.md` router.

```text
$ PYTEST_XDIST= python3 -m pytest -q -p no:randomly tests/unit/test_a_pasted_guide_block_is_fresh_or_dated.py tests/unit/test_the_docs_index_is_a_router.py tests/unit/test_the_documented_invocations_parse.py tests/unit/test_docs_links_and_commands.py
all green; make lint clean
```

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | whatif block `saves 19.050s` -> `18.050s` | pasted-block guard, 2 failed |
| A2 | drop the `[... elided: a blank line ...]` markers in the blast block | pasted-block guard, 1 failed |

### Deviation from the Required Fix

None. `docs/design/roles.md` lists no guides, so no link there. `junction-cost` is shown on `macro_micro` against `with_timeline` (same keys) and `cache-trend` on one run named four times: the committed fixtures hold no real variant or series pair; the guide says so.
