# UX-1305: a capture that recorded zero processes has no troubleshooting guide

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_capture_troubleshooting_names_what_the_code_prints.py`

## Motivation

The pilot's most likely failure, a shim that never ran, is answered
by `--diagnose`/`--no-inject` and `BST_TRACE_REAL_BWRAP`, and those live
only in cli.md's catch-all list or nowhere: `bwrap_shim.py:2065` tells
the user to set `BST_TRACE_REAL_BWRAP`, which no doc names.

```text
$ grep -rlw BST_TRACE_REAL_BWRAP docs/guides README.md | wc -l
0
$ grep -rl -- '--diagnose' docs/guides README.md
docs/guides/cli.md
```

## Required Fix

A troubleshooting section in real-project.md (linked from pilot.md):
zero processes, the shim's exec failing, `bga doctor`, `--diagnose`,
`--no-inject`, `BST_TRACE_REAL_BWRAP`; the env var joins cli.md's
inventory with `BST_TRACE_ARGV_MAX`.

## Out of Scope

`bga doctor`'s own checks.

## Acceptance Test

`grep` reads the section's names in real-project.md; the env inventory
guard covers both variables. Reading taken in this container.

## Decision

The section is `## Troubleshooting: Plane 2 recorded zero processes` in
real-project.md, linked from pilot.md. The two variables go in
`docs/design/areas/tools-native_trace.md`, where `UX-1290` moved the
`BST_TRACE_*` rows: `test_no_capture_wiring_row_in_the_switches_table`
refuses them in cli.md's table. Both rows already existed there; the
`BST_TRACE_ARGV_MAX` row was wrong (it counts recorded invocations, not
truncation) and is corrected.

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held. The variable the shim tells the user to set was in no guide.

### The gap, measured

```text
$ grep -rlw BST_TRACE_REAL_BWRAP docs/guides README.md | wc -l
0
$ grep -rl -- '--diagnose' docs/guides README.md
docs/guides/cli.md
```

### After

```text
$ grep -rlw BST_TRACE_REAL_BWRAP docs/guides README.md
docs/guides/real-project.md
$ grep -rl -- '--diagnose' docs/guides README.md
docs/guides/cli.md
docs/guides/real-project.md
$ PYTEST_XDIST= python3 -m pytest -q -p no:randomly tests/unit/test_the_capture_troubleshooting_names_what_the_code_prints.py
8 passed
```

Found while quoting: under `bga snapshot` / `bga capture run` the tracer
overwrites `BST_TRACE_REAL_BWRAP` with `shutil.which("bwrap")`
(`bst_native_build_tracer.py`, `env["BST_TRACE_REAL_BWRAP"] = real_bwrap`),
so exporting it does not take effect there. The section says so and names
`PATH` as the lever; the shim's own message ("set BST_TRACE_REAL_BWRAP")
only helps when the shim is driven by hand.

### Mutations verified red and reverted (10)

| # | mutation | reddened |
|---|---|---|
| A1 | guide renames `BST_TRACE_ARGV_MAX` | `test_the_env_var_the_shim_tells_the_user_to_set_is_named`, 1 |
| A2 | shim's message names `BST_TRACE_REAL_BIN` | same, 1 |
| A3 | guide renames `PLANE 2 CAPTURED NOTHING` | `test_the_untraced_warning_and_no_inject_line_are_quoted`, 1 |
| A4 | guide drops "process" from the `--no-inject` line | same, 1 |
| A5 | guide misquotes `could not be run` | `test_the_self_test_failures_are_the_ones_the_probe_raises`, 1 |
| A6 | guide misnames `--diagnose` | `test_the_flags_named_are_flags_the_commands_have`, 1 |
| A7 | guide misquotes `The bwrap shim ran 0 times.` | `test_the_diagnose_readings_are_the_sentences_it_prints`, 2 |
| A8 | pilot link anchor shortened | `test_the_pilot_links_the_section`, 1 |
| A9 | tracer's `env["BST_TRACE_REAL_BWRAP"] = real_bwrap` becomes `pass` | `test_the_tracer_overwrites_the_real_bwrap_variable_as_the_section_says`, 1 |
| A10 | `shutil.which("bwrap")` becomes a constant path | same, 1 |

### Deviation from the Required Fix

cli.md's table is not edited: its guard refuses `BST_TRACE_*` rows there (`UX-1290`); the rows are corrected in the area page.
