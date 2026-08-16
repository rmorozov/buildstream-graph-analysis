# UX-31: `UX-22` captures `public: bst: max-jobs`, but BuildStream's real per-element parallelism control is `notparallel` - so serialization-point detection sees nothing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-22 (done - this corrects the field it captures)

## Motivation

`UX-22` shipped per-element `max-jobs` capture (`tools/bst_show_to_graph.py::_parse_max_jobs`, via `bst show`'s `%{public}`) plus a `serialization_point_risks` diagnostic. Its own docstring records the empirical work behind picking that field: `variables: max-jobs:` in an element body is rejected as a protected-variable redefinition, `%{vars}`'s `max-jobs` always reports the project default, so `public: bst: max-jobs:` was chosen as "the real mechanism".

Re-checked against a real BuildStream 2.7.0 install and a real build, that conclusion does not hold. `public:` is arbitrary user metadata; nothing in `buildstream/` reads a `max-jobs` key out of it. The variable that produces `-jN` is `JOBS: -j%{max-jobs}` (declared in `buildstream_plugins/elements/cmake.yaml`, and identically in `make.yaml`/`meson.yaml`/`autotools.yaml`), and `max-jobs` is a project-wide base variable set once from `Context.effective_build_max_jobs` (`buildstream/_project.py`). The per-element control those same plugin YAMLs actually document, in a commented-out line right next to the `make:` definition, is:

```yaml
  # Set this if the sources cannot handle parallelization.
  #
  # notparallel: True
```

Real evidence, `examples/06-macro-micro-optimization` (filed with this task). `core.bst` carries `variables: notparallel: True`; every other element is identical but for its sources. Extracted from a real Plane 2 trace of a real `bst --builders 4 --max-jobs 4 build all.bst`:

```
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

```
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
4. Correct `UX-22`'s own doc and the `docs/architecture.md` extension table rather than leaving two contradictory accounts in the repo.

## Out of Scope

- Measuring achieved parallelism from Plane 2 (`UX-32`). That is the stronger signal and does not need any declaration to be captured at all; this task is about the cheap, static, Plane-1-side check being pointed at a real field.
- Whether `notparallel` is *justified* for a given element. The tool's job is to surface that an element is pinned to one job and that it is expensive; deciding whether its Makefile is actually race-prone is the user's.

## Acceptance Test

1. Extracting `examples/06-macro-micro-optimization` records `core.bst` as parallelism-pinned and no other element.
2. `bga analyze` reports a real serialization-point risk for `core.bst` on that run, and none on the `optimized/` variant.
3. `_parse_max_jobs`'s docstring and `UX-22`'s doc no longer claim `public: bst: max-jobs` changes `-jN`. Full suite green.

## Verification Log

Filed 2026-08-16. The `-jN` table is extracted from a real Plane 2 trace (`tools/bst_native_build_tracer.py run`) of a real `bst --builders 4 --max-jobs 4 build all.bst` against `examples/06-macro-micro-optimization`, BuildStream 2.7.0 in a real `bwrap` sandbox on a 4-core host - the command lines are the tracer's own recorded `cmd` strings, not reconstructed. `serialization_point_risks: []` and `max_jobs: null` are from that same run's real `bga analyze -f json` output and real `graph.json`. The BuildStream-side claims (`JOBS: -j%{max-jobs}`, `max-jobs` as a protected project-wide base variable, `notparallel` documented in the plugin YAMLs) were read from the installed BuildStream 2.7.0 and `buildstream-plugins` sources directly.
