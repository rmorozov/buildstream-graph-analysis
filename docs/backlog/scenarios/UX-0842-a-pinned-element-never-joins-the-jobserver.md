# UX-842: a pinned element never joins the jobserver

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-679, UX-841 | **Found by:** round 117, Direction 20 | **Serves:** R2 (an element pinned for a build-system defect keeps its pin) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`examples/06`'s `core.bst` is `notparallel: True`, and `UX-679`'s
capture b joined it anyway: peak native concurrency 4 where the project
declared 1. A pin can be the workaround for a defect in the native build
system - a Makefile that races itself - and a jobserver that overrides
it turns a green build red. BuildStream composes the pin into the
sandbox environment as `-j1` (`MAKEFLAGS: -j%{max-jobs}` for make and
autotools, `JOBS: -j%{max-jobs}` for cmake) or as a bare `1` (`JOBS`
for meson - verified against installed `buildstream-plugins` 2.7.0),
and the shim sees that `--setenv` in the `bwrap` argv it wraps.

## Required Fix

`tools/native_trace/bwrap_shim.py`: `build_shim_argv` parses the
element's own `-j` from the `--setenv MAKEFLAGS`/`--setenv JOBS` entries
BuildStream composed; `-j1` means no injection at all for that sandbox -
no `MAKEFLAGS` auth, no `JOBS` change, the argv byte for byte as without
the mode; `-jK` with K equal to the project's `max-jobs` (read once by
the tracer from `bst show --format '%{vars}'` of any element, recorded
as `project_max_jobs`) joins uncapped; any other K joins through a
proxy capped at K once `UX-849` lands and, until then, is recorded as
`capped_pending` and joins uncapped. The report lists each element's
decision.

## Decomposition

Input classes: a `notparallel` element, an element at the project
default, an element with `public: bst: max-jobs: 16` (the
`bst_show_project` fixture has all three); the journey it extends is
`UX-679`'s two captures of examples/06, where `core.bst` must now show
peak concurrency 1 under the mode.

## Out of Scope

The cap itself - `UX-849`'s proxies; `max_jobs_advice`'s missing
pinned-element rule is `UX-847`'s block.

## Acceptance Test

`tests/unit/test_bwrap_shim.py` gains four cases from the composed
argv of the three fixture elements plus meson's own shape: the `-j1`
MAKEFLAGS argv is unchanged, meson's bare `JOBS: 1` is also unchanged,
the default joins, the 16 is recorded; mutation: join the `-j1`
element - red. On examples/06 under `--jobserver 4`,
`jobserver_decisions` shows `core.bst` `pinned` with `max_jobs: 1` and
no `--jobserver-auth` anywhere in its sandbox's argv - `per_element_parallelism`'s
`peak_work_concurrency` reads 2 either way, mode on or off, which is
`_concurrency_profile`'s own driver+child overlap accounting and out
of this row's scope (pasted in the Outcome).

## Outcome

**Gap measured.** The spike joined `core.bst` at peak native
concurrency 4 where the project declared 1; `UX-841`'s Outcome, fix
landed but before this row's decision logic: `"peak 2 req 1 achieved
200%"`. The verifier's HOLD found this row's own first pass still had
two gaps: meson composes `JOBS` as a bare integer, not `-jN` (verified:
`bst show --format '%{env}'` on a `notparallel` meson element prints
`JOBS: 1`), so `parse_element_max_jobs(["--setenv","JOBS","1"])`
returned `None`, the decision was `joined`, and the auth was injected -
the exact bug this row exists to close, unfixed by the first pass. And
`read_project_max_jobs`/`_cmd_target`/`_parse_max_jobs_from_vars`/
`read_jobserver_decisions` had no guard at all - forcing `_cmd_target`
to return `None` left 58/58 green.

**Close measured.** `parse_element_max_jobs` now also accepts a bare
integer for `JOBS` (`MAKEFLAGS` still requires `-jN`/`-j N`/`--jobs=N`);
`tests/unit/test_bwrap_shim.py` gained the meson case, 20/20 green.
Two new guards in `test_native_build_tracer.py` cover the previously
unguarded functions (a pasted `bst show --format '%{vars}'` excerpt for
`_parse_max_jobs_from_vars`, a temp JSONL of 0/1/3 rows for
`read_jobserver_decisions`), 42/42 green. Live, `examples/06`,
`--jobserver 4`, fresh cache, `bst build core.bst`, exit 0:

```text
jobserver_decisions: [{"decision": "pinned", "element": "core.bst", "max_jobs": 1}]
core.bst's exec_argv (387 tokens, --diagnose): 0 occurrences of "jobserver-auth"
core.bst per_element_parallelism: peak_work_concurrency 2, requested_jobs 1
```

**Deviation from the original Acceptance Test text** (which asked for
peak 1): a second capture with the jobserver mode entirely off
(`jobserver: null`, no FIFO, no shim jobserver code reached at all)
reproduced the identical `peak_work_concurrency: 2` for `core.bst` -
`_concurrency_profile`'s own interval-overlap accounting (a compiler
driver and its forked child both counted as live for one instant),
pre-existing (`f30102cd`) and orthogonal to this row's fix, not a
jobserver leak. The Acceptance Test now asks for the decision and the
argv, which the fix controls, not the peak, which it does not.

**Mutations verified red and reverted (4):** `jobserver_decision`'s
`element_max_jobs == 1` → `== 0` reddened the MAKEFLAGS pin case
(`with_mode == without_mode` failed, `--jobserver-auth` injected);
dropping the bare-int branch reddened the meson case the same way;
`_parse_max_jobs_from_vars`'s `data.get("max-jobs")` →
`data.get("max-jobs-typo")` reddened its present-line case (`None` vs
`1`); `read_jobserver_decisions` skipping every second line reddened
its many-rows case (`[]` vs 1 row). All reverted from scratchpad
copies; `test_bwrap_shim.py` 20/20 and `test_native_build_tracer.py`
42/42 green again.

Deviation (merge): the verifier held the first commit on a defect the
filing itself carried - meson composes `JOBS` as a bare integer, not
`-jN` - and the amended parser accepts both; `_cmd_target` stays
unguarded and degrades to `project_max_jobs` unknown, the safe branch;
the Acceptance Test was refiled from peak 1 to the measured 2, read
with the mode on and off alike.
