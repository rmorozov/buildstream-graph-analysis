# UX-608: fifteen commands the context map never names

**Priority:** Medium | **Status:** 🟢 Done Open | **Depends on:** UX-590 (which measured it), UX-607 (which blocks it) | **Serves:** every session reading fixing guide §6 to find where a thing lives | **Topic:** docs

## Motivation

`UX-590` held §6's `--format` row against the writer registry both
ways. The command half it could only do in one direction — a command
*named* in §6 is checked against the registry, but the registry is not
held to appear in §6:

```text
registered commands            32
named nowhere in §6            15
--format choices                4     named in §6   2
```

The map's whole promise is "where does a thing live", and for
fifteen of thirty-two commands it does not answer.

## Required Fix

§6 names every registered command, and a guard holds the set both
ways — so adding a subcommand without a map entry is red, and a map
entry naming no command is red.

## Out of Scope

- The `--format` row — done in `UX-590`, and it is the worked example
  this one follows.

## Acceptance Test

A registered command removed from §6 — red naming it; a §6 entry for
a command that does not exist — red.

## Blocked on

`UX-607`. The vocabulary costs ~920 B against 33 B of headroom.

## Outcome (round 84, 2026-09-03) — 🟢 Done

**Premise: confirmed.** Re-measured at this track's base `d4a3d04`,
off the registry rather than off `UX-590`'s note:

```text
$ registered commands (13 subcommands + 19 tool aliases)   32
  ... named nowhere in §6's fenced map                     15
cache-logs, cache-trend, checkout-cost, chrome-to-trace, cross-check,
doctor, extract, gen-synthetic, graph-from-show, log-to-chrome,
native-to-chrome, rebuild-set, release-notes, timeline, wrap
```

The other 17 were named only *incidentally* — `compare` is in the map
because `bga/compare.py` is, not because anything holds it there.

**Close.** §6 gains one fenced block, keyed by its heading, of 32
`command  path` rows: the subcommands, then the `tools/` aliases, whose
module names differ from the command (`rebuild-set` ->
`tools/bst_rebuild_set.py`) and were the map's real gap. Four clauses in
`UX-590`'s file, its shape: registry -> block, block -> registry, each
row points at a path that exists, and a vacuity floor.

```text
block +1,479 B    guide 41,440 -> 42,919 B    still ~40 KB, 3,162 B left
$ PYTEST_XDIST= python3 -m pytest \
    tests/unit/test_the_context_map_is_the_tree.py -q
1 failed, 28 passed in 0.26s      # the one red is UX-595's, below
$ make lint      All checks passed!
```

`UX-607` is what made this one file: at `round(B/1024)` this block was
1,479 B against 33 B of headroom.

**Acceptance Test.**

```text
$ sed -i '/^rebuild-set  .../d' fixing-guide.md
E   AssertionError: command(s) `bga` registers and section 6 does not
    name: ['rebuild-set']. docs/contributing/fixing-guide.md section 6.
$ + row `unwrap  tools/bst_run_wrapped.py`
E   AssertionError: section 6's command block names row(s) `bga` does
    not register: ['unwrap']
```

**Mutations.**

| mutation | anchor confirmed | red | count |
|---|---|---|---|
| `rebuild-set` row deleted (AT) | `grep -c '^rebuild-set'` -> 0 | `…every_registered_command_is_on_the_map` | 2 failed, 27 passed |
| `unwrap` row added (AT) | `grep -c '^unwrap'` -> 1 | `…every_command_the_map_names_is_registered` | 2 failed, 27 passed |
| `"reheat"` into `TOOL_ALIASES` | `bga/tools_dispatch.py:52` | `…every_registered_command_is_on_the_map` | 2 failed, 27 passed |
| `doctor` -> `tools/bga_physician.py` | `grep -c bga_physician` -> 1 | `…each_command_row_says_where_the_command_lives` + `…names_nothing_that_does_not_exist` | 3 failed, 26 passed |
| block emptied, heading kept | rows -> 0 | `…every_registered_command…` + `…block_is_a_non_empty_population` | 3 failed, 26 passed |

Every count carries the one pre-existing red below.

**A clause narrower than it looks.** The last mutation is the reason the
vacuity floor is there: with the block empty, `…names_is_registered` and
`…says_where_the_command_lives` both go *green* on an empty set. Neither
discriminates alone; the floor is what makes the pair a guard.

**Not done, and why.** `test_every_module_is_on_the_map` is red at base
`d4a3d04` on `bga/capacity_model.py` (`UX-595`, another track). Its row
needs a description of what that module is, which `UX-595`'s Outcome is
the authority for — guessing it onto the map is the defect §6's guard
exists to catch. Filed for the orchestrator; ~60 B, and 3,162 B are
free. `BGA_SKIP_SELECTOR=1` on this commit for it.

**Deviation from the Required Fix.** None.
