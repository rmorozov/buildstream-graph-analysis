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

## Outcome

Gap measured, today (`git clone` then `du -sh`, remote clone — the
proxy allowed it, no local-`.git` fallback needed):

```text
$ git clone --quiet https://github.com/rmorozov/buildstream-graph-analysis default
$ du -sh default default/.git
104M  default
74M   default/.git
$ git clone --quiet --single-branch --branch main https://github.com/rmorozov/buildstream-graph-analysis single
$ du -sh single single/.git
47M   single
17M   single/.git
```

104 MiB / 47 MiB against the sentence's stated 50 MiB / 5.3 MiB — both
roughly 2x the earlier figures, consistent with the growth the
Motivation predicted. `README.md:14`'s figure restated in the
branch-count clause's own shape: `(104 MiB against 47 MiB as of
2026-09-14: \`git clone\` vs \`git clone --single-branch\` of this
repository, each then \`du -sh\`)`.

Close measured: `test_every_readme_clone_size_sits_in_a_dated_commanded_parenthetical`
added to `tests/unit/test_docs_links_and_commands.py`, sibling to the
wall-clock guard. `python3 -m pytest tests/unit/test_docs_links_and_commands.py
tests/unit/test_a_clone_without_the_archive.py -q` → `69 passed`.
`make test-touching`: `63 file(s) selected (21 census + 42 naming the
change) · 1799 passed, 3 skipped in 279.68s`.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `(104 MiB against 47 MiB as of 2026-09-14: ...)` → bare `(50 MiB against 5.3 MiB)` | `test_every_readme_clone_size_sits_in_a_dated_commanded_parenthetical` (offenders `['50 MiB', '5.3 MiB']`) | 1 failed / 58 deselected, then reverted → 59 passed |

One collision found and fixed in the same pass: the first draft's
parenthetical restated the full `git clone
https://.../buildstream-graph-analysis` command, which put a second
"git clone" + "buildstream-graph-analysis" line into README.md and made
`test_a_clone_without_the_archive.py`'s flag-scanner (any line with
both substrings) pick up `--heads` from the neighbouring
`git ls-remote --heads` clause as a bogus documented clone flag (5 red).
Rewritten to `git clone` / `git clone --single-branch` "of this
repository" without repeating the URL; both files pass together.
