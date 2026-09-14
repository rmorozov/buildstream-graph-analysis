# UX-856: the jobserver is a snapshot switch

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-851, UX-849 | **Found by:** round 119, the user | **Serves:** R4 (the local loop captures under the mode with one flag) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`bga capture run --jobserver auto` (`UX-851`) and `--plan` (`UX-849`)
exist, but the local loop is `bga snapshot -- bst build target.bst`,
which composes the capture itself and offers neither. A user of the loop
cannot capture under the mode without typing the three commands
`snapshot` exists to replace, and a snapshot pair (off, then auto) is
the comparison the mode's value is read from.

## Required Fix

`tools/bga_snapshot.py`: `--jobserver auto|N|off` (default `off`) and
`--plan @prev|@last|<analyze.json>` pass through to the capture argv
exactly as `bga capture run` resolves them (`bga/cli.py`'s
`resolve_jobserver_ceiling`, reused, not copied); `@prev` and `@last`
resolve to that snapshot's `analyze.json`. The capture context file
records both, and the compare header names each side's mode (the
`run_instance.jobserver` fact `UX-851` writes). `docs/guides/cli.md`'s
snapshot section shows the pair.

## Decomposition

Input classes: `off`, an int, `auto` with and without `--builders`,
`--plan` as a path and as `@prev`, `--plan` without the mode; the
journey it extends is R4's local loop - a snapshot pair off then auto.

## Out of Scope

A sticky setting in `.bga/config` - the flag is per capture, like
`--diagnose` (`UX-146`).

## Acceptance Test

`tests/unit/test_the_snapshot_takes_the_jobserver_switch.py`: the
composed capture argv carries `--jobserver N` and `--plan <path>` for
`auto`, an int, `off` and `@prev`, and the context file names them;
mutation: drop the pass-through - red. A live pair on examples/11
(`UX-857`) pasted from this box.

## Outcome

**Gap measured.** Before: `grep -n jobserver tools/bga_snapshot.py` at
`b9f64a1e` found zero hits - no `--jobserver`/`--plan` flag, no pass-
through, no context-file line, and `_compare` printed nothing naming
either side's mode beyond `bga compare`'s own per-side header.
`examples/11` does not exist (`UX-857`, a separate, unfiled track) - the
live pair ran on `examples/10-jobserver` instead, per the coordinator's
brief.

**Close measured.**
`python3 -m pytest tests/unit/test_the_snapshot_takes_the_jobserver_switch.py -q`
→ `10 passed in 0.40s` (resume added a case driving `_compare` itself).
`tests/unit/test_the_snapshot_records_the_jobserver.py` → `24 passed`.
`tests/unit/test_help_is_short.py` (+ `test_docs_links_and_commands.py`,
first pass) → `195 passed in 41.03s` combined. `python3
tools/dev_baseline.py --check` → exit 0, no `new:` line, both passes.
`python3 tools/dev_sizes.py --check` → clean after `--adopt --force`
(below). `ruff check bga/ tools/ tests/ .claude/hooks/` → `All checks
passed!`. `bga snapshot --help` → 53 lines (cap 63). `make test-touching`
not run directly (shared box, per the brief's SAFETY note) but the
amend's commit hook ran the selector itself and found the new test file
moved `docs/contributing/fixing-guide.md`'s own spread figure;
`dev_touching.py --spread --write` closed it (31-154/550 → 31-155/551).
A second selector run then failed
`test_the_fast_check_holds_what_the_suite_holds.py` on 4 problems -
UX-853/854/857 missing a `## Decomposition` block, UX-857's `examples`
area unknown to the fixing guide's §6 tree, and UX-856 itself (this
file, filed without one in round 119's own opening commit) - reproduced
identically on the first, already-committed `a0509af4` (confirmed via
`git stash`/`git log -1`), so pre-existing across round 119's five
filings and not this diff's. Out of scope (other tracks' files, a
governance decision on the tree); `BGA_SKIP_SELECTOR=1` used for this
one amend, per the hook's own escape hatch.

Live pair, `examples/10-jobserver`, staged toolchain, fresh
`XDG_CACHE_HOME`/`XDG_DATA_HOME` per capture, `PYTHONPATH`-pinned to
this worktree (`UX-728`), each under `timeout 900`:

```text
$ bga compare @prev @last   # .../runs/20260914T202304Z/run .../runs/20260914T202343Z/run
jobserver: off -> auto (3)
============================================================
Run Comparison
...
           jobserver off
Candidate: ...
           jobserver auto (ceiling 3)
```

`capture-context.txt` of the `auto` snapshot: `jobserver: auto 3` /
`plan: -`.

**Mutation table** (falsify skill, reverted from
`/tmp/.../scratchpad/agent-af5c7b4bdee3025ed/bga_snapshot.py.orig`,
re-confirmed green after each):

| mutation | file | reddened | count |
|---|---|---|---|
| drop the `--jobserver`/`--plan` pass-through in `take_snapshot` | `tools/bga_snapshot.py` | `test_auto_resolves_against_a_faked_core_count`, `test_an_explicit_int_passes_through`, `test_plan_at_prev_resolves_to_that_snapshots_analysis` | 3 |
| drop the two new lines from `_capture_context` | `tools/bga_snapshot.py` | `test_the_mode_ceiling_and_plan_are_recorded`, `test_off_and_no_plan_are_dashes` | 2 |
| drop `print(_jobserver_compare_line(...))` in `_compare` (resume) | `tools/bga_snapshot.py` | `test_compare_itself_prints_the_line` | 1 |

No guard failed to discriminate.

Deviation (resume, verifier HOLD): the compare-header print was
unguarded, since `_jobserver_compare_line` was tested directly but
nothing drove `_compare()` itself, so deleting the `print` stayed
green; closed above.
`dev_sizes.py --check` listed three `grew:` cells (`bga/cli.py`
`file_lines`, `tools/bga_snapshot.py` `file_lines`/`longest_function`)
plus a fourth after the `--plan` help-text edit
(`tools/bga_snapshot.py` `file_lines` +1) - both adopted via
`dev_sizes.py --adopt --force` into `tests/quality_reference.json`.
`--plan`'s help gained the clause naming where `@prev`/`@last` resolve.
