# UX-56: Plane 2's element tag is a path convention a real project overrides, so 99.4% of a real build's processes land in one bucket that is not an element

**Priority:** High | **Status:** 🟢 Guard implemented, real fix open | **Depends on:** `UX-23` (which introduced the tag), `UX-51` (which made it a join key)

## Motivation

Found in round 6, on the first **successful** real dual-plane capture:
`freedesktop-sdk`, 25 elements rebuilt from source on top of a cached
base, 46 minutes, and **127,630 traced processes** — 155× the largest
capture Plane 2 had ever seen.

Plane 2 survived that scale. What it did not survive was the project's
layout:

```
by_element:
  buildstream-build   126871      <- 99.4%
  expat                  411
  unknown                336
  flit_core               12
```

`buildstream-build` is not an element. It is `freedesktop-sdk`'s build
root.

`tools/native_trace/bwrap_shim.py::extract_element_name` takes the
element from bwrap's `--dir` option:

> BuildStream's own generated bwrap argv always includes a real `--dir
> buildstream/<project-name>/<element>.bst` option (the sandbox's own
> working directory, confirmed present in every real captured invocation
> this whole `UX-11`/`UX-23` arc has examined)

That was true of every invocation examined — all of them from projects in
this repository's `examples/`, which use BuildStream's **default** build
root. A project is free to set its own, and `freedesktop-sdk` does:
`/buildstream-build` (and `/buildstream-install`). Its elements' sandbox
working directory therefore carries no element identity at all, and every
process lands in one bucket.

## What that made the report say

Every per-element figure became a whole-build figure wearing an element's
name, and none of them reads as obviously wrong in isolation:

| reported | actual |
|---|---|
| `peak_work_concurrency: 1019` for one "element" | 4 builders × 4 jobs on a 4-core runner |
| `achieved_vs_requested: 254.75` against `requested_jobs: 4` | the build achieved 255× the parallelism it asked for |
| one redundant operation worth `total_duration_s: 44145` | inside a **2,796-second** build — 12 hours of recoverable time in a 46-minute build |
| `cpu_time.per_element["buildstream-build"]: 8704s` | the whole build's CPU time, attributed to a directory |

And `bga correlate` — whose entire design (`UX-51`) rests on element UID
being *the* contract between the planes — reported:

```
Joined 4 element(s) on element UID (126 in Plane 1, 4 traced in Plane 2)
  Not traced, but Plane 1 says they matter: components/_private/cmake-stage1.bst,
    components/bison.bst, components/doxygen.bst, components/openssl.bst,
    components/python3.bst
No element has a finding in both planes worth acting on.
```

The five elements naming 90% of the critical path were "not traced" —
they *were* traced, all 127,630 processes of them, into a bucket the join
could not see. The one plausible-looking key, `expat`, is not
`components/expat.bst` either, so it could not have matched.

## Why no previous round could find it

This is the fourth consecutive round whose finding is about **fixture
shape**, and the first where the shape in question is not the data but
the *project layout*:

| capture | processes | tags | reliable |
|---|---|---|---|
| `examples/06` (real, this repo) | 822 | 9, all `*.bst` | yes |
| `examples/05`, `examples/07` | — | all `*.bst` | yes |
| `freedesktop-sdk` (real, third-party) | 127,630 | 0 `*.bst` | **no** |

Every project this repository wrote uses BuildStream's default build
root, because nothing in writing an example project prompts you to change
it. The convention held perfectly across three real captures and four
audit rounds, and then failed completely on the first project written by
someone else.

## Required Fix

1. **Detect and refuse, rather than publish per-element figures that are
   not per-element.** (Done.) A BuildStream element name ends in `.bst`;
   a tag that does not is not an element. `assess_element_attribution`
   reports `reliable: false` with the measured share and the largest
   bucket, the text report says so directly under the split it
   invalidates, and `bga correlate` refuses the join entirely rather than
   render rows that cannot mean anything. This is the posture `UX-46`
   established: refuse rather than guess.
2. **Find an authoritative element identifier.** *(Open.)* `--dir` is a
   convention, not an identity. Candidates worth measuring on a real
   capture, in the order I would try them:
   - BuildStream's own log names the element per task and the sandbox is
     created inside that task, so a timestamp-ordered join between the
     Plane 1 log and the bwrap invocation order may be exact — but it is
     an inference, and would need to be shown so rather than assumed.
   - The bwrap argv's `--bind <cas-tmpdir> /` path may contain a
     per-element temporary directory. This needs a real captured argv to
     settle, which round 6 does not have: the raw trace exceeded the
     tarball budget and was dropped.
   - Failing both, BuildStream would have to be asked to pass the element
     name explicitly, which is an upstream change and should be treated
     as one.
   Whatever wins, the `.bst` check stays: it is what turns a silent
   mis-attribution into a refusal.

## Out of Scope

- `max_concurrency: 5268` across the whole capture, which is a separate
  question about processes with no observed exit (already documented in
  `open_records_note`) and is not caused by this.
- `opens_captured` reporting **149,053 dropped paths against 65,101
  recorded** — a 70% drop rate that finally answers round 5's open
  question about the hook's fixed 8192-slot / 256 KiB per-process budget
  ("generous or naive"). Naive, at this scale. Filed separately rather
  than mixed in here.

## Acceptance Test

1. The real `freedesktop-sdk` tag distribution yields `reliable: false`
   naming `buildstream-build` and its 126,871 processes.
2. The real `examples/06` tag distribution (822 processes, 9 elements)
   yields `reliable: true` — the guard must not fire on the captures
   Plane 2 was built against.
3. `bga correlate` against an unreliable report renders the refusal and
   **nothing else** — a reader must not be able to scroll past a warning
   into a table of meaningless rows.
4. A native report predating this field correlates exactly as before.

## Fix Implemented

`assess_element_attribution` in `tools/bst_native_build_tracer.py`,
emitted as `element_attribution` in every report; `format_report` prints
`ELEMENT ATTRIBUTION UNRELIABLE: ...` immediately after the by-element
split; `bga/correlate.py` sets `attribution_unreliable`, empties
`actionable`, and `format_correlation` returns the refusal as its entire
output.

Verified against both real captures taken the same day:

| capture | verdict |
|---|---|
| `freedesktop-sdk`, 127,630 processes | `reliable: false`, 0 of 127,630 recognized, largest bucket `buildstream-build` |
| `examples/06`, 822 processes | `reliable: true`, 822 of 822 recognized, 9 elements |

Tests: 10 new (`tests/unit/test_element_attribution_reliability.py`),
including both real tag distributions, a partial collapse (one bad bucket
is enough — there is no way to tell which of the rest are affected), that
the tracer's own `unknown` placeholder never counts as an element, and
that the refusal replaces the join rather than prefixing it.

Suite: 938 → 948.

## Verification Log

Filed 2026-08-17 (round 6). Every figure is from GitHub Actions run
`32026123204`'s successor — the first capture in this project's history
of a real third-party BuildStream project building successfully
(`traced_build_exit=0`, 2,801.9s wall clock, 25 elements built on top of
a 101-element cached base, `bst` 2.7.0, 4-core runner). The report is the
70MB `native-report.json` published to the `captures/fdsdk-latest` branch
by `.github/workflows/real-project-capture.yml`.

The contrast case is not hypothetical either: the `examples/06`
dual-plane capture quoted above was run in the development container on
the same day, with the same `--trace-opens` tracer, and produced a fully
reliable 9-element split. Same code, same command; different project
layout.
