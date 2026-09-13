# UX-839: the clone-size claim is half what a clone now costs

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-551 (a machine-dependent figure is not reproducible), UX-779 (the wall-clock guard this extends) | **Found by:** review 23 | **Serves:** someone deciding whether `--single-branch` is worth typing | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`README.md:14` states a default clone (every `captures/*` branch) at
**50 MiB against 5.3 MiB** for `--single-branch`, with no date and no
command — unlike the branch count in the same sentence, which carries
both (`twelve as of 2026-09-07`). Measured today:

```text
$ git clone --single-branch https://github.com/rmorozov/buildstream-graph-analysis clone_single
$ du -sh clone_single clone_single/.git
46M  clone_single
16M  clone_single/.git
$ git clone https://github.com/rmorozov/buildstream-graph-analysis clone_full
$ du -sh clone_full clone_full/.git
103M  clone_full
73M   clone_full/.git
```

No pairing of these four numbers lands near 50/5.3: the full clone is
roughly 2x the stated 50 MiB by any measure, and the single-branch
clone is 3x–9x the stated 5.3 MiB. The repository's `captures/*`
branches only grow (the sentence's own "a capture job may add more at
any time"), so a bare figure here ages the way `UX-551` found
`make test`'s wall clock does — it is a property of the tree's history
at measurement time, not a constant.

## Required Fix

Restate both figures dated and commanded, in the sentence's own style:
`du -sh` on a fresh `--single-branch` clone and a fresh default clone,
today's date, both commands shown — matching the branch-count clause
three words earlier in the same sentence rather than leaving it the
one unmeasured half of it.

## Out of Scope

- A guard that re-clones over the network on every CI run — too slow
  and too flaky for a gate; this is a dated record, not a live check.
- The `captures/*` branch count itself — already dated and commanded,
  and not what drifted.

## Acceptance Test

A new guard, sibling to `test_no_readme_line_states_a_suite_wall_clock_beside_make_test`
(`tests/unit/test_docs_links_and_commands.py`): any `MiB`/`KiB` clone-size
figure in `README.md`'s Install section must sit inside a parenthetical
that also names a date (`YYYY-MM-DD`) and a `du`/`git clone` command,
the same shape the branch-count clause already passes. Mutation: drop
the parenthetical back to a bare `(50 MiB against 5.3 MiB)` — the new
guard reds, naming the line.
