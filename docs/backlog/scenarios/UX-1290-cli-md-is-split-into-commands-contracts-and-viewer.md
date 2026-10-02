# UX-1290: `cli.md` is split into a command reference, a contracts page and a viewer page, and user switches are separated from internal variables

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1285, UX-1286, UX-1287, UX-1288 (they edit `cli.md`) | **Found by:** the docs audit (2026-10-02, finding 6) and the owner: pilots "will suffer" if the jobserver switches are buried | **Serves:** R1, R4, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome
