# UX-1290: `cli.md` is split into a command reference, a contracts page and a viewer page, and user switches are separated from internal variables

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1285, UX-1286, UX-1287, UX-1288 (they edit `cli.md`) | **Found by:** the docs audit (2026-10-02, finding 6) and the owner: pilots "will suffer" if the jobserver switches are buried | **Serves:** R1, R4, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** test_every_command_has_a_section_in_cli_md.py, test_the_environment_surface_is_an_inventory.py

## Motivation

`docs/guides/cli.md` is 3,015 lines under 98 headings. Installation
sits at line 402, after the snapshot chapter; "JSON outputs and their
schemas" is 780 lines (1063-1841); `bga view` is 540 (1862-2402);
`doctor`, `bundle`, `junction-cost` and `cache-trend` have no `##`
entry. The environment table (around 830-915) lists the few switches
an operator sets (`BGA_ADMISSION`, `BGA_JOBSERVER_MODE`, `BGA_RATE`)
among ~30 internal `BST_TRACE_*` and shim variables the capture sets
on itself.

## Required Fix

Three pages: `guides/cli.md` (install first, then one `##` per
command, flags and exit codes), `guides/json-contracts.md` (the
schemas chapter) and `guides/viewer.md` (the view chapter). The
environment table splits into "switches you set" (default, how to
turn it off, cost) and "set by bga itself, listed for debugging".
The ~35 internal wiring and fault-injection `BST_TRACE_*` rows move
to `design/areas/tools-native_trace.md`. `--trace-opens` and
`--trace-spine` state, where they are introduced (cli.md:172-180),
that they are on by default, how to turn them off (`--no-trace-opens`,
`--trace-spine=off`) and their measured cost (UX-895). Every inbound link and anchor is moved with its section.

`tests/unit/test_the_environment_surface_is_an_inventory.py` keeps
holding every variable, wherever its row now lives.

## Out of Scope

Rewording sections beyond what the move needs.

## Acceptance Test

Every `bga` subcommand in `bga --help` has a `##` in `cli.md`; no
`BST_TRACE_*` row in the "switches you set" table; the link and
anchor guards green; total lines of the three pages within ±3% of
today's 3,015 (nothing dropped).

## Outcome (2026-10-03)

**Premise:** held; `cli.md` had grown to 3,062 lines since filing.

### The gap, measured

`acc1290.py` (`bga --help`'s subcommands and aliases via `create_parser`
and `format_tool_help`, a `## \`bga NAME\`` heading per command), base
tree `671e2396b`:

```text
before: cli.md 3062 lines, 82 headings, first ## 'One entry point (`UX-67`)'; 33 commands in `bga --help`,
  27 with no `## `bga NAME``: [analyze, baseline, bundle, cache-logs, cache-trend, capture, checkout-cost,
  chrome-to-trace, cross-check, diagnostics, doctor, extract, floors, gen-synthetic, graph, graph-from-show,
  junction-cost, log-to-chrome, native-to-chrome, rebuild-set, release-notes, replay, run-context, sweep,
  utilisation, whatif, wrap]; BST_TRACE_ rows in the user table: 39
```

### The close, measured

```text
after: cli.md 1809 lines, 80 headings, first ## 'Installation'; 33 commands in `bga --help`, 0 with no
  `## `bga NAME``: []; BST_TRACE_ rows in the user table: 0
cli.md 1809 + json-contracts.md 858 (of which 779 appended) + viewer.md 545; the three pages less
  json-contracts.md's prior 79: 3133 against 3062, +2.3%
tools-native_trace.md 55 -> 124 (+69, the BST_TRACE_* section)
$ pytest tests/unit/test_docs_links_and_commands.py <the two guards>   70 passed
```

The schemas chapter is appended to `json-contracts.md` whole, with
`whatif`'s and `junction-cost`'s worked examples, which lived in it;
the view chapter is `viewer.md`. All 39 `BST_TRACE_*` rows moved — the
twelve "set by hand" ones too, since a user's capture switches are
flags. The switches table gains default, off and cost; two `BGA_*`
rows set by `bga` itself joined the four non-switches. The one
cross-page anchor (`#the-two-plane-join-published-ux-215`) and the
ceilings-table references in `what-the-viewer-answers.md` and
`styleguide.md` follow their sections; eleven guards that read a moved
section read its new page. The 21 command stubs are a heading and one
line. `test_the_loop_stays_fast.py`'s selector `max` 196 → 197: the new
guard reads `bga.cli`'s parser.

### Mutations verified red and reverted (9)

`test_every_command_has_a_section_in_cli_md.py` (4) and
`test_the_environment_surface_is_an_inventory.py` (7):

| # | mutation | reddened |
|---|---|---|
| N1 | `## \`bga junction-cost\`` demoted | every command has a section: 1 |
| N2 | a `## \`bga frob\`` added | every section names a command: 1 |
| N3 | `## Installation` renamed | installation first: 1 |
| N4 | the JSON chapter heading back in `cli.md` | left the reference: 1 |
| N5 | a `BST_TRACE_OPENS` row in the switches table | 5 (two homes, no wiring row, area page) |
| N6 | `BGA_RATE`'s cost cell blank | default, off and cost: 1 |
| N7 | the area page dropped from `HOMES` | every name has a row, area page: 2 |
| N8 | `BST_TRACE_SPINE`'s row deleted from the area page | every name has a row: 1 |
| N9 | the switches header loses `cost` | default, off and cost: 1 |

Restored: 11 passed.
