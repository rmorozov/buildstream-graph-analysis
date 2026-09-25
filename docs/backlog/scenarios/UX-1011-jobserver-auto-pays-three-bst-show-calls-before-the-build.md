# UX-1011: `--jobserver auto` pays three `bst show` calls before the build

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-842, UX-843, UX-882 | **Found by:** Graviton run 36123209379 (`bst-perf-tools/bga-bench` job 108033307761), `10-jobserver`, cold cache, 3 repeats | **Serves:** R4 | **Topic:** capture | **Area:** tools | **Shape:** bounded

## Motivation

```text
off   wall 22.97/21.20/21.05s  head (to bst's first START) 4.1/3.7/3.7s  "Compiling the trace hook..." at 2.8s
auto  wall 28.52/27.55/27.74s  head 10.0/10.0/10.0s                      "Compiling the trace hook..." at 8.9s
```

The traced element spans are the same or shorter under `auto` (8.8s
against 8.9s). The whole penalty is before the build: `--jobserver
auto` runs three separate `bst show` subprocesses
(`tools/bst_native_build_tracer.py`) that `off` never pays -
`read_project_max_jobs` (`%{vars}` of the target), `read_element_kinds_
for_jobserver` (`%{name} %{kind}`) and `read_element_auth_map_for_
jobserver` (`%{name}<US>%{public}<RS>`) - each paying BuildStream's
startup plus a project load, about 2s on a Cortex-A72.

## Required Fix

`tools/bst_native_build_tracer.py` gains one `bst show` call in place
of the three: `%{name}<US>%{kind}<US>%{vars}<US>%{public}<RS>`, the
RS/US-delimited scheme UX-882's own `read_element_auth_map_for_
jobserver` already used, because `%{vars}` and `%{public}` are
multi-line YAML. Every consumer receives exactly what it received
before: `kinds_read_diagnostic`'s argv and reason (`no-target`/
`timeout`/`oserror`/`exit`/`no-lines`), `{}` on a failed auth read,
`None` for max-jobs on any failure or when `cmd` names no target. The
three public readers (`read_project_max_jobs`,
`read_element_kinds_for_jobserver`, `read_element_auth_map_for_
jobserver`) keep their own names, own signatures and own individual
`bst show` calls unchanged - every existing test of them still calls
them directly and still passes. `main`'s own `--jobserver` site
(`read_jobserver_metadata_for_build`) is what stops calling them and
calls the new combined `read_jobserver_bst_show` instead.

## Out of Scope

The Graviton re-run confirming the wall-clock win - the session's job,
this row stays open for it. Any change to what the build itself does;
the scheduler's own recipe-width behaviour under `auto` is unchanged.

## Decomposition

surfaces: `tools/bst_native_build_tracer.py` (two new functions -
`read_jobserver_bst_show`, `read_jobserver_metadata_for_build`, plus a
`_parse_jobserver_show_records` helper kept under the mccabe baseline -
and `main`'s own call site), `tests/unit/
test_jobserver_reads_pay_one_bst_show_call.py` (new guard),
`tests/quality_baseline.json` (one new `S603` entry, `--force --reason
UX-1011` - a net-new `bst show` call site, even though it replaces
three at runtime). guards: the new subprocess-count test; every
existing reader test, unchanged, still green.

## Acceptance Test

`tests/unit/test_jobserver_reads_pay_one_bst_show_call.py`: a fake
`bst` script that logs its own argv shows exactly one `bst show` call
under `read_jobserver_metadata_for_build(..., jobserver=4)`, and none
at all when `jobserver` is falsy. Every existing reader test
(`test_the_kinds_read_carries_the_options.py`,
`test_a_public_annotation_sets_the_auth_style.py`, the `_parse_*` tests
in `test_native_build_tracer.py`) stays green.

## Outcome

### The gap, measured

Graviton run 36123209379 (`bst-perf-tools/bga-bench` job
108033307761), `10-jobserver`, cold cache, 3 repeats:

```text
off   wall 22.97/21.20/21.05s  head (to bst's first START) 4.1/3.7/3.7s  "Compiling the trace hook..." at 2.8s
auto  wall 28.52/27.55/27.74s  head 10.0/10.0/10.0s                      "Compiling the trace hook..." at 8.9s
```

The traced element spans are the same or shorter under `auto` (8.8s
against 8.9s) - the whole ~6-7s penalty is three extra `bst show`
subprocesses paid before the build starts.

### The close, measured

```text
$ python3 -m pytest tests/unit/test_jobserver_reads_pay_one_bst_show_call.py \
    tests/unit/test_the_kinds_read_carries_the_options.py \
    tests/unit/test_a_public_annotation_sets_the_auth_style.py \
    tests/unit/test_native_build_tracer.py -q
73 passed, 3 skipped in 0.83s
$ make test-touching
116 file(s) selected (32 census + 84 naming the change) · 2995 passed, 45 skipped in 73.64s (0:01:13)
$ make lint
All checks passed!
```

Graviton run 36129369038 (head `edd36330`), same fixture and arms:

```text
off   wall 25.88/22.59/21.07s  head 4.1/3.7/3.7s  cpu 150/159/149s
auto  wall 23.95/23.65/23.55s  head 6.0/6.0/6.0s  cpu 156/156/155s
```

auto's head 10.0s -> 6.0s and its wall 27.7s -> 23.6s median; the
2.3s left over off is the one remaining `bst show`.

### Mutations verified red and reverted (1)

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `read_jobserver_metadata_for_build` restored to call the three separate old readers instead of `read_jobserver_bst_show` | `test_the_jobserver_path_pays_one_bst_show_call` | `assert 4 == 1` (4 `bst show` calls logged: the combined format, `%{vars}`, `%{name} %{kind}`, `%{name}<US>%{public}`) |

### Deviation from the Required Fix

None.
