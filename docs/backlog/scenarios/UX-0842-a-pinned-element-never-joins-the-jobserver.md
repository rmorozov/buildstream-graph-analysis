# UX-842: a pinned element never joins the jobserver

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-679, UX-841 | **Found by:** round 117, Direction 20 | **Serves:** R2 (an element pinned for a build-system defect keeps its pin) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`examples/06`'s `core.bst` is `notparallel: True`, and `UX-679`'s
capture b joined it anyway: peak native concurrency 4 where the project
declared 1. A pin can be the workaround for a defect in the native build
system - a Makefile that races itself - and a jobserver that overrides
it turns a green build red. BuildStream composes the pin into the
sandbox environment as `-j1` (`MAKEFLAGS: -j%{max-jobs}` for make and
autotools, `JOBS: -j%{max-jobs}` for cmake and meson), and the shim
sees that `--setenv` in the `bwrap` argv it wraps.

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

`tests/unit/test_bwrap_shim.py` gains three cases from the composed
argv of the three fixture elements: the `-j1` argv is unchanged, the
default joins, the 16 is recorded; mutation: join the `-j1` element -
red. On examples/06 under `--jobserver 4`, `core.bst`'s per-element
peak concurrency reads 1 (pasted from the capture's `per_element_parallelism`).
