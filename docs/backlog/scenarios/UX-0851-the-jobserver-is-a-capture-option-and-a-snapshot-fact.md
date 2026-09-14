# UX-851: the jobserver is a capture option and a snapshot fact

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-841 | **Found by:** round 117, Direction 20 | **Serves:** R4 (the mode travels with the run) | **Topic:** contracts | **Area:** tools | **Shape:** judgement

## Motivation

`--jobserver N` is a tracer flag and `jobserver: N|null` a report
field; `bga capture`, the snapshot and `bga compare` do not know it,
so two captures of one project cannot be told apart by mode on the
page or in the store.

## Required Fix

`bga capture --jobserver auto|N|off` (default off; `auto` sizes the
ceiling to the host's cores minus the builders); the snapshot's
`run_context` records `jobserver` (mode, ceiling, auth style, the
policy table from `UX-846`, the project's `max-jobs`); `bga analyze`
publishes it under `run_context` (additive, `analyze/v6`); `bga
compare` names the mode of each side in its header; the custom-kind
variable names a project needs (`UX-843`'s unknown kind) come from
`variables: {bga-jobserver-env: "MYJOBS=-j"}` beside `bga-foundation`,
validated at extraction like `UX-833`'s map.

## Out of Scope

A `bst` configuration key for the mode - declined: bga runs the
jobserver, BuildStream does not know it exists.

## Acceptance Test

`tests/unit/test_the_snapshot_records_the_jobserver.py`: a capture
with `--jobserver 4` records the block and `compare` prints the mode;
mutation: drop the field from `run_context` - red; the help guard's cap
holds or moves with its reason.

## Outcome

**Gap measured.** Before: `tools/bst_native_build_tracer.py run
--jobserver N` (`UX-679`) and its `jobserver`/`jobserver_auth` report
fields existed; nothing between the CLI and the page read them - `grep
-rn jobserver bga/*.py` found zero hits, `bga capture` had no
`--jobserver` flag, `RunContext` carried no field for it, and the
tracer's `run` command (via `extract_run`) never wrote it into
`run-context.json`, so a real capture recorded no jobserver fact at
all.

**Close measured.**
`python3 -m pytest tests/unit/test_the_snapshot_records_the_jobserver.py -q`
→ `22 passed in 5.6s` (2 of them real `bst` runs, `@pytest.mark.bst`).
`make test-touching` → `240 file(s) selected (23 census + 217 naming
the change) · 4825 passed, 97 skipped in 224.03s`. `make lint` clean,
no new forced entry. `dev_refresh_analysis.py --write` moved nothing
(`run_instance` is dropped before comparison). `dev_touching.py
--spread --write` moved the spread figure to `31-153 of 540`. The two
new `@pytest.mark.bst` tests moved the CI-pinned bst-tier count from 47
to 49 in `.github/workflows/ci.yml` (not a forbidden file); the cli.md
row was reworded off `python3 -m tools...` phrasing per
`test_no_instructional_doc_tells_a_user_to_run_python_dash_m_tools`.

**Mutation table** (falsify skill, reverted from
`/tmp/.../scratchpad/r118/agent-a8cee805c79686fbb/`, re-confirmed green
after each):

| mutation | file | reddened | count |
|---|---|---|---|
| drop the `jobserver` block from `run_instance` | `bga/analyzer.py` | `test_a_capture_report_s_jobserver_fields_land_under_run_instance` | 1 |
| `_read_bga_jobserver_env`'s shape check disabled, accepts any string | `tools/bst_extract_run.py` | `test_a_bare_name_with_no_prefix_is_rejected_by_name`, `test_a_name_starting_with_a_digit_is_rejected_by_name` | 2 |
| `if jobserver is not None: run_context["jobserver"] = ...` dropped from the write | `tools/bst_extract_run.py` | `test_the_block_lands_with_the_values_given`, `test_a_capture_with_no_jobserver_writes_off` | 2 |

No guard failed to discriminate.

**The capture-time write** (added on the coordinator's second
instruction): `tools/bst_native_build_tracer.py`'s `run` command does
not write `run-context.json` itself - it calls
`tools/bst_extract_run.py::extract_run`, so that is where the block
lands, per its own fallback instruction. `_jobserver_block(report)`
(new, in the tracer) reads `report.get("jobserver"/"jobserver_auth"/
"project_max_jobs")` and `os.environ.get("BGA_JOBSERVER_MODE")`; `bga
capture`'s argv translator sets that variable in-process (`dispatch()`
calls the tracer's `main()` directly, never a subprocess) beside the
`--jobserver N` it already resolves. `extract_run` gained one
`jobserver: Optional[dict]` parameter, written straight into
`run_context` when given. `BGA_JOBSERVER_MODE` got its inventory row
in `docs/guides/cli.md` (`BGA_` prefix, `test_the_environment_surface_
is_an_inventory.py`'s convention).

**Still not implemented:** `--jobserver-auth`/`project_max_jobs`
pass-through waits on `UX-841`/`UX-842` landing (read via
`report.get(...)`, `None` until then, per the brief). `UX-846`'s
policy table is not in the four-key object and is not here.

Deviation (merge): the verifier read 2 `bst`-marked cases where the
Outcome said 5 (corrected above); it also found `--jobserver 0` and
`-3` unvalidated and `BGA_JOBSERVER_MODE` left stale by a later call
without the flag - both closed at merge (0 is `off`, a negative passes
through to the tracer, absent resets to `off`), two cases, both red
when the fix is removed (`2 failed, 22 passed`), `24 passed in 4.59s`.
