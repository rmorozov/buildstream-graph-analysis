# UX-1306: no guide says the run store grows, or how to prune it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_disk_paragraph_names_the_prune_flags_and_a_measured_size.py`

## Motivation

`bga snapshot --prune`, `--older-than`, `--keep` and `--max-store` are
in cli.md only (`cli.md:316-351`); README, real-project.md and pilot.md
(which keeps 30 bundles a class) never mention `.bga/runs` growth.

```text
$ grep -rln -- '--prune\|--max-store' docs/guides README.md
docs/guides/cli.md
```

## Required Fix

A "disk" paragraph in real-project.md with the store's measured size
per run and the prune commands, and a README pointer.

## Out of Scope

Changing prune defaults.

## Acceptance Test

The paragraph names a measured bytes-per-run figure and the commands;
the link guard holds the pointer. Reading taken in this container.

## Decision

`### Disk` under real-project.md's "What you get, and what it costs", and
one sentence in README.md appended to an existing paragraph (the README is
at its annotated 339-line budget, so no line is added). No `bst` here, so
the sizes are the two the repository holds: the committed
`tests/fixtures/macro_micro` (Plane 1 run + `plane2.json`, 11 elements) and
`bga gen-synthetic --seed 1` (1,202 elements, Plane 1 only). The
`plane2.log.gz` half is cited from the measure skill's 311 KB, labelled not
re-measured. `--prune` and the `prune` subcommand both parse; the flag form
is what `bga snapshot --help` lists.

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held.

### The gap, measured

```text
$ grep -rln -- '--prune\|--max-store' docs/guides README.md
docs/guides/cli.md
```

### After

```text
$ grep -rln -- '--prune\|--max-store' docs/guides README.md
docs/guides/cli.md
docs/guides/real-project.md
README.md
$ du -sb tests/fixtures/macro_micro
60838 tests/fixtures/macro_micro
$ bga gen-synthetic /tmp/scale --seed 1 && du -sb /tmp/scale
760213 /tmp/scale
$ PYTEST_XDIST= python3 -m pytest -q -p no:randomly tests/unit/test_the_disk_paragraph_names_the_prune_flags_and_a_measured_size.py
4 passed
```

The one real snapshot figure is 311 KB (9 elements), from the measure skill, not re-measured; 60838 is a committed fixture and 760213 a Plane 1 synthetic run, labelled so in the guide, with no per-element division.

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| A1 | the figure 60838 becomes 60000 | `..._and_a_figure_that_is_the_tree`, 1 |
| A2 | `--older-than` becomes `--older` | same, 1 |
| A3 | `--max-store` becomes `--max-size` | same, 1 |
| A4 | README pointer loses `#disk` | `test_the_readme_points_at_the_disk_paragraph`, 1 |
| A5 | `doomed = list(husks)` becomes `doomed = []` in `tools/bga_snapshot.py` | `test_the_husk_rule_is_the_one_the_prune_code_has`, 1 |
| A6 | guide says "both are snapshots" | `test_the_snapshot_figure_is_the_skills_and_the_fixture_is_labelled_not_a_snapshot`, 1 |
| A7 | guide's 311 KB becomes 411 KB | same, 1 |

### Deviation from the Required Fix

Review fixes: the guide leads with the skill's 311 KB, labels the fixture, and states the husk rule (a capture still running has no `run/` until extraction, read from the code, not reproduced).
