# UX-869: the jobserver FIFO mounts under the bind destination

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-841, UX-846 | **Found by:** round 121, the user (a real project under a junction, GNU Make 4.4 on the host) | **Serves:** R2 (a cmake element builds under the mode on a project that is not under /tmp) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

`open_jobserver` makes the FIFO under the trace's bind dir, which lives
at `<project>/.bga/tmp/trace-*/bind` by design (`UX-155`), and the shim
binds it onto its own host path: `--bind <fifo> <fifo>`
(`_jobserver_injection`, the line `UX-841` describes as "a bind of the
FIFO onto itself"). The sandbox root is read-only and the project's
path does not exist inside it, so bwrap fails to make the parents:
`can't mkdir parents for .../my_project/.bga/tmp/trace-*/bind/
jobserver: read-only file system`, and the build dies on its first
cmake element. `UX-846` moved the wrappers under the fixed `bind_dst`
(`/tmp/.bst-native-trace`) for the same reason and never reached the
FIFO. The bind is only injected under fifo-style auth, which
`jobserver_auth_style("auto")` picks for GNU Make 4.4 and newer on the
host; this box and CI run 4.3, fd style, so the defect never fired
here and the user's host hit it at once.

## Required Fix

`tools/native_trace/bwrap_shim.py`: the FIFO is not mounted on its own,
since it already sits inside the bind dir the shim mounts at
`bind_dst`, so the in-sandbox path is `bind_dst/jobserver`; `MAKEFLAGS`'s
`--jobserver-auth=fifo:<path>` and the wrappers' `BST_TRACE_JOBSERVER`
carry that path, and the host path stays with the tracer's own
reader. `tools/bst_native_build_tracer.py`: the `--diagnose` record
names both paths.

## Decomposition

Input classes: fd style (no bind), fifo style with the bind dir under
the project, fifo style with it under `/tmp`; the journey it extends is
the user's first build under the mode on a project outside `/tmp`.

## Out of Scope

The auth style choice (`UX-841`); a bind dir outside the project.

## Acceptance Test

`tests/unit/test_bwrap_shim.py`: a fake `bwrap` on `PATH` that refuses
any `--bind`/`--ro-bind` destination outside `bind_dst` and `/tmp`
(exit 1 with bwrap's own message) runs the fifo-style injection clean,
and the composed `MAKEFLAGS` names `bind_dst/jobserver`; mutation:
restore `--bind <fifo> <fifo>` - red. A live pair on `examples/11` with
`--jobserver-auth fifo` from this box pasted in the Outcome.

## Outcome

**Gap measured.** `_jobserver_injection` bound the FIFO (global and
UX-849's per-element proxy alike) onto its own host path -
`--bind <fifo> <fifo>` - and named that same host path in
`MAKEFLAGS=--jobserver-auth=fifo:<path>`, even though `bind_src` (the
FIFO's own parent) is already bound whole at `bind_dst`. The proxy FIFO
(`bind_dir/proxies/<element>.fifo`) carried the identical defect -
checked and fixed in this row, per the brief.

**Close measured**, pair: the session's, at merge (`--diagnose` on
`examples/11` with `--jobserver-auth fifo` not run here - the box runs
a gate and five other tracks).

`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/unit/test_bwrap_shim.py tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py tests/unit/test_the_broker_grants_by_slack.py tests/unit/test_capture_diagnostics.py tests/unit/test_a_held_tool_returns_its_tokens.py tests/unit/test_bwrap_argv_capture.py`:

```text
tests/unit/test_bwrap_shim.py .......................................... [ 27%]
............                                                             [ 35%]
tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py ........           [ 40%]
tests/unit/test_the_broker_grants_by_slack.py .............              [ 49%]
tests/unit/test_capture_diagnostics.py ................................. [ 70%]
..........................                                               [ 87%]
tests/unit/test_a_held_tool_returns_its_tokens.py ...........            [ 94%]
tests/unit/test_bwrap_argv_capture.py ........                           [100%]
============================= 153 passed in 5.68s ==============================
```

Full `touching` file list (69 files) direct-run:
`2063 passed, 8 skipped in 382.27s`. `ruff check`, `dev_baseline.py
--check`, `dev_sizes.py --check` (after one `--adopt --force` for the
new helper/wider tuple param) all clean.

**Mutation table**, `falsify` skill, reverted from a scratchpad copy:

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `test_fifo_style_runs_clean_through_a_bwrap_that_refuses_binds_outside_bind_dst_or_tmp` | restore `--bind <fifo> <fifo>` in `_jobserver_injection` | itself | 1/1 |
| `test_a_proxy_under_fifo_style_names_the_bind_dst_path_with_no_bind_of_its_own` | same | itself | 1/1 |
| `TestTheShimsArgvCarriesTheChosenStyle::test_a_4_4_version_string_carries_fifo_under_bind_dst_and_no_bind_of_its_own` | same | itself | 1/1 |

One run: `test_bwrap_shim.py`/`test_the_jobserver_fifo_has_a_lifecycle.py`/
`test_the_broker_grants_by_slack.py` together, `75` collected -
`3 failed, 72 passed`; reverted from the pristine pre-mutation copy,
`75 passed`. `test_a_fifo_bound_onto_its_own_host_path_reds_under_the_same_bwrap`
(a hand-built mutated argv, not the live source) stayed green under the
source mutation too - it proves the fake bwrap itself refuses the
defect shape, not that the shim still produces it; the three rows
above are what discriminates the real change.
