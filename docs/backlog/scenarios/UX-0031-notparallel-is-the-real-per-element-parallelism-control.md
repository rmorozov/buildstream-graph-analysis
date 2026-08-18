# UX-31: `UX-22` captures `public: bst: max-jobs`, but BuildStream's real per-element parallelism control is `notparallel` - so serialization-point detection sees nothing

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-22 (done - this corrects the field it captures)

## Motivation

`UX-22` shipped per-element `max-jobs` capture (`tools/bst_show_to_graph.py::_parse_max_jobs`, via `bst show`'s `%{public}`) plus a `serialization_point_risks` diagnostic. Its own docstring records the empirical work behind picking that field: `variables: max-jobs:` in an element body is rejected as a protected-variable redefinition, `%{vars}`'s `max-jobs` always reports the project default, so `public: bst: max-jobs:` was chosen as "the real mechanism".

Re-checked against a real BuildStream 2.7.0 install and a real build, that conclusion does not hold. `public:` is arbitrary user metadata; nothing in `buildstream/` reads a `max-jobs` key out of it. The variable that produces `-jN` is `JOBS: -j%{max-jobs}` (declared in `buildstream_plugins/elements/cmake.yaml`, and identically in `make.yaml`/`meson.yaml`/`autotools.yaml`), and `max-jobs` is a project-wide base variable set once from `Context.effective_build_max_jobs` (`buildstream/_project.py`). The per-element control those same plugin YAMLs actually document, in a commented-out line right next to the `make:` definition, is:

```yaml
  # Set this if the sources cannot handle parallelization.
  #
  # notparallel: True
```

Real evidence, `examples/06-macro-micro-optimization` (filed with this task). `core.bst` carries `variables: notparallel: True`; every other element is identical but for its sources. Extracted from a real Plane 2 trace of a real `bst --builders 4 --max-jobs 4 build all.bst`:

```text
core.bst    -> /usr/bin/make -f Makefile -j1
codegen.bst -> /usr/bin/make -f Makefile -j4
lib-a.bst   -> /usr/bin/make -f Makefile -j4
lib-b.bst   -> /usr/bin/make -f Makefile -j4
lib-c.bst   -> /usr/bin/make -f Makefile -j4
lib-d.bst   -> /usr/bin/make -f Makefile -j4
lib-e.bst   -> /usr/bin/make -f Makefile -j4
lib-f.bst   -> /usr/bin/make -f Makefile -j4
app.bst     -> /usr/bin/make -f Makefile -j4
```

and the measured consequence, from the same trace: `core.bst` reached a peak of **1** concurrent `cc1plus` over a 13.05s span, against a peak of 3-4 for every sibling. Removing that one line (the `optimized/` variant) took `core.bst` to peak 4 over 6.03s.

`bga`'s own verdict on that run:

```text
$ bga analyze -f json -d /tmp/run-06-baseline | jq .structural.serialization_point_risks
[]
$ jq '.elements[] | {uid, max_jobs}' /tmp/run-06-baseline/graph.json
{"uid":"core.bst","max_jobs":null}     # ... and null for every other element
```

So the one element in the project that really is a serialization point is invisible to the detector built to find serialization points.

There is a second, narrower correction in the same place. `UX-22`'s motivating scenario was *raising* one element's parallelism ("giving one large synchronization-point element like an LLVM build the full core count"). BuildStream 2.7.0 offers no such control: `max-jobs` is protected against element-level redefinition, and `notparallel` only clamps to 1. The feature's stated use case is not expressible; the opposite one - an element accidentally pinned to `-j1` - is, is common (it is the standard workaround for a race-prone Makefile, and it outlives the reason it was added), and is what the detector should be looking for.

## Required Fix

1. Capture `notparallel` per element. `bst show`'s `%{public}` will not carry it; the value lives in the element's own `variables:`. Determine the real capture route when picked up - candidate options are a `%{vars}`-based read (which `UX-22` found reports project defaults for `max-jobs`, but `notparallel` is not a protected variable, so it may behave differently and must be tested rather than assumed), or reading the element YAML directly the way `tools/bst_extract_run.py --strict` already reads `project.conf`.
2. Keep the existing `max_jobs` field - it is harmless and round-trips as `None` - but stop treating it as the parallelism signal, and correct `_parse_max_jobs`'s docstring, which currently asserts a mechanism that BuildStream does not implement.
3. Re-point `serialization_point_risks` at the real signal: an element with `notparallel` set, long duration, and high blast radius is precisely the "large synchronization point" the diagnostic was written for.
4. Correct `UX-22`'s own doc and the `docs/design/architecture.md` extension table rather than leaving two contradictory accounts in the repo.

## Out of Scope

- Measuring achieved parallelism from Plane 2 (`UX-32`). That is the stronger signal and does not need any declaration to be captured at all; this task is about the cheap, static, Plane-1-side check being pointed at a real field.
- Whether `notparallel` is *justified* for a given element. The tool's job is to surface that an element is pinned to one job and that it is expensive; deciding whether its Makefile is actually race-prone is the user's.

## Acceptance Test

1. Extracting `examples/06-macro-micro-optimization` records `core.bst` as parallelism-pinned and no other element.
2. `bga analyze` reports a real serialization-point risk for `core.bst` on that run, and none on the `optimized/` variant.
3. `_parse_max_jobs`'s docstring and `UX-22`'s doc no longer claim `public: bst: max-jobs` changes `-jN`. Full suite green.

## Fix Implemented

**The capture route turned out to be simpler than this doc predicted, and it corrects a second half of `UX-22`'s finding.** Item 1 said `%{public}` would not carry `notparallel` and that a `%{vars}` read "may behave differently and must be tested rather than assumed". Tested against a real BuildStream 2.7.0 build of `examples/06-macro-micro-optimization`:

```text
$ bst show --format '%{name}::%{vars}' core.bst lib-a.bst | grep -E 'notparallel|max-jobs'
max-jobs: 1
notparallel: True      <- core.bst
max-jobs: 4            <- lib-a.bst
```

`%{vars}` carries **both**, and its `max-jobs` is the *resolved* per-element value - the number that really reaches `-j%{max-jobs}` in the plugins' own `environment: JOBS`. `UX-22`'s conclusion that `%{vars}` "always reports the project-wide default, never a per-element override" holds only for what it actually tested (writing `variables: max-jobs:` directly, which BuildStream rejects as a protected-variable redefinition); the `notparallel` path is a different one and it does reach `%{vars}`.

So `tools/bst_show_to_graph.py` gained `%{vars}` as a seventh capture field, `_parse_effective_max_jobs` (resolved value from `%{vars}`, falling back to `UX-22`'s `%{public}` read only so an older captured `graph.json` keeps meaning what it meant), and `_parse_notparallel` (True/False/None - "didn't say" and "said no" stay distinguishable). `_parse_max_jobs`'s docstring is corrected in place rather than deleted. `Element.notparallel` and its loader wiring follow.

**`serialization_point_risks` re-pointed** (item 3). This needed more than a threshold change: with `%{vars}` reporting the resolved value, *every* element now reports the project default, so the old "near-full-core" candidate test would have fired on everything. The module now detects the expressible condition - an element pinned **below** the run's own typical resolved `max_jobs` (by `notparallel` or by value), long relative to this run's own tasks, with real elements waiting behind it. The concurrent-dispatch pairing is gone: for a serialized element the question is not who runs beside it but how much is stuck behind it, so `downstream_count` replaces it. A uniformly single-job project is deliberately not flagged - that is the project's own choice, not an outlier.

`SerializationPointRisk` keeps its list-shaped `elements` field for schema compatibility, now holding exactly one element, and gained `notparallel`/`typical_max_jobs`/`downstream_count`. The report section is renamed `Parallelism-Pinned Elements` and its hint names the element, both numbers, the cause, and both real next steps.

`docs/design/architecture.md`'s extension table and `UX-22`'s own doc are corrected (item 4).

Tests: 7 new/rewritten across `tests/unit/test_bst_show_to_graph.py` (resolved value and `notparallel` from `%{vars}`, the `%{public}` fallback, unset-vs-false), `tests/unit/test_serialization_points.py` (the real pinned case, plus the three deliberate non-flag cases: uniformly-single-job, pinned-but-cheap, pinned leaf with nothing waiting), and `tests/unit/test_serialization_point_integration.py` (the same end to end through the real analyzer call site). The two tests asserting `UX-22`'s unreachable premise were rewritten rather than deleted, with the reason recorded in their own docstrings.

## Verification Log

Filed 2026-08-16. Implemented the same day. The `-jN` table is extracted from a real Plane 2 trace (`tools/bst_native_build_tracer.py run`) of a real `bst --builders 4 --max-jobs 4 build all.bst` against `examples/06-macro-micro-optimization`, BuildStream 2.7.0 in a real `bwrap` sandbox on a 4-core host - the command lines are the tracer's own recorded `cmd` strings, not reconstructed. `serialization_point_risks: []` and `max_jobs: null` are from that same run's real `bga analyze -f json` output and real `graph.json`. The BuildStream-side claims (`JOBS: -j%{max-jobs}`, `max-jobs` as a protected project-wide base variable, `notparallel` documented in the plugin YAMLs) were read from the installed BuildStream 2.7.0 and `buildstream-plugins` sources directly.

Real end-to-end re-verification. Re-extracting the exact real capture from this doc's Motivation now yields the per-element values (`python3 -m tools.bst_show_to_graph examples/06-macro-micro-optimization all.bst`):

```text
toolchain.bst    kind=import   max_jobs=4 notparallel=None
core.bst         kind=cmake    max_jobs=1 notparallel=True
codegen.bst      kind=cmake    max_jobs=4 notparallel=None
lib-a.bst .. lib-f.bst, app.bst, all.bst   max_jobs=4 notparallel=None
```

matching the traced sandbox exactly (`core.bst -> make -j1`, everything else `-j4`). And `bga analyze -d` on the re-extracted run now names it:

```text
  Parallelism-Pinned Elements (UX-31 - running fewer native build jobs than the rest of
  this build, and expensive enough for it to matter):
    - core.bst runs its own build system at 1 job(s) - `variables: notparallel: True` -
      while the rest of this build runs at 4, and it is the longest kind of task here
      (14.0s) with 8 element(s) waiting behind it. If its sources can handle parallelism,
      removing the pin is a single-line change; if they genuinely cannot, it is a real
      synchronization point worth splitting up
```

Acceptance Test items 1-3 all confirmed with real data - and note what this changes for the walkthrough: the micro-level finding that previously required an ad-hoc script over Plane 2's JSON is now in Plane 1's own text report, from a plain `bst show`. Full suite green (717 passed, up from 712), `make lint` clean.
