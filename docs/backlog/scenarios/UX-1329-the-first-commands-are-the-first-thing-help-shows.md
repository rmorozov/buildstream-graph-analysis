# UX-1329: The README's real-project install line installs the user's project, and `bga --help` buries doctor, snapshot and view

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** docs | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_first_commands_are_the_first_thing_help_shows.py`

## Motivation

README "Use it on your real project" opens with `pip install -e ".[bst]"` under "run from inside
the project", which in the user's project tries to install their project. `bga --help` lists 35
commands; `doctor`, `snapshot` and `view` sit in the bottom "thin aliases" block
(`bga/tools_dispatch.py:146`) beside `release-notes`, a maintainer tool:

```text
capture, analysis and conversion (thin aliases for the programs in
tools/, which remain runnable directly as `python3 -m <module>`):
  ...
  release-notes     Generate a release body from the closed backlog rows  (tools.bga_release_notes)
  gen-synthetic     ...
  snapshot          Capture, analyze and compare - the whole local loop  (tools.bga_snapshot)
  doctor            Check this machine can capture at all  (tools.bga_doctor)
```

Measured on a fresh venv at `19f1fd73`.

## Decomposition

Surfaces: README's real-project block; `bga --help` and bare `bga`. Readers: a newcomer with a
clone of bga beside their project.

## Required Fix

The README install line installs bga's checkout with the `bst` extra from beside the user's
project. `bga --help` opens with a three-line "Start here" naming `doctor`, `snapshot` and `view`
in order; `release-notes` is not listed among user commands.

## Out of Scope

A PyPI wheel; reordering the remaining commands.

## Acceptance Test

`bga --help | head` shows the three first commands; the README install line resolves from a
directory beside the clone; guards hold both. Reading taken in this container.

## Outcome

**The gap measured.** `bga --help` at `19f1fd73`: 35 commands, `doctor`/`snapshot`/`view` in the bottom alias
block beside `release-notes`; README line 101 `pip install -e ".[bst]"` (also line 22).

**The close measured.** `python3 -m bga.cli --help | head -7` opens with `Start here:` then `bga doctor .`,
`bga snapshot -- bst build TARGET`, `bga view`. `release-notes` is under a separate `maintainer tools` heading
(still runnable, still in `TOOL_ALIASES`, so the cli.md alias-table walk stays green). README lines 22 and 101 read
`pip install "./buildstream-graph-analysis[bst]"`. `tests/unit/test_help_is_short.py` `TOP_LEVEL_CAP` 51 -> 57
(5-line block + 1 heading). 203 passed over docs-links, contracts, alias-table, help-length and the new file;
`test_every_command_has_a_section_in_cli_md.py` + register: 1591 passed.

**Mutation table.**

| Mutation | Reddened | Count |
|---|---|---|
| drop the `bga view` line | order test | 1 failed |
| swap `doctor` and `snapshot` | order test | 1 failed |
| `MAINTAINER_ALIASES = ()` | release-notes test | 1 failed |
| description without the block | order + opens-first | 2 failed |
| README back to `pip install -e ".[bst]"` | install-line + no-`-e` | 2 failed |
| README without the `[bst]` extra | install-line test | 1 failed |

### Deviation from the Required Fix

`release-notes` sits under a "maintainer tools" heading; the help cap 51 -> 57. The commit also carries lint fixes for UX-1330 and UX-1331's files. (`61cd78ce`)
