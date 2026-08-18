# UX-56: Plane 2's element tag is a path convention a real project overrides, so 99.4% of a real build's processes land in one bucket that is not an element

**Priority:** High | **Status:** 🟢 Done (guard + correlation) | **Depends on:** `UX-23` (which introduced the tag), `UX-51` (which made it a join key)


## Investigation, 2026-08-17: what the argv and the process tree rule out

`UX-58` shipped the argv capture this task said it needed, and the answer
is not the one this task assumed. Both candidate sources were checked
against a **local reproduction** rather than another 50-minute capture.

### Reproducing the real failure in seconds

`freedesktop-sdk`'s collapse is caused by one project-wide variable.
Adding it to `examples/07-declared-vs-used-dependencies/project.conf`:

```yaml
variables:
  build-root: /buildstream-build
```

reproduces the real capture's shape exactly:

| | real `freedesktop-sdk` | local repro |
|---|---|---|
| processes in one bucket | 126,890 / 127,630 (99.4%) | **234 / 234 (100%)** |
| bucket name | `buildstream-build` | `buildstream-build` |
| `element_attribution.reliable` | false | false |
| `declared_vs_used` | entirely empty | entirely empty |

Restoring `project.conf` restores correct attribution (`base.bst`,
`user.bst`, `unrelated.bst`) and `declared_vs_used`'s 1 unused / 4 used
verdict. **This is the harness for the fix**, and it costs about forty
seconds.

### The argv does not carry the element

In a real 349-token argv the element appears three times — `--dir`,
`--chdir`, and `--setenv PWD` — and all three are the *same*
build-root-relative path. They are one source printed three times, not
three independent sources, so a project overriding `build-root` loses all
three together. Nothing else in the argv identifies the element: the CAS
staging bind is randomly named (`cas-tmpdir2wnYto`).

### Neither does the process tree

Walking the shim's full ancestry on a real build:

```
bwrap-shim
  └─ buildbox-run --remote=unix:… --action=/tmp/tmp5bfa04hs --action-result=…
      └─ …/venv/bin/python3 …/bst  (the main BuildStream process)
          └─ the tracer
```

There is no per-element job process to read a title or command line from,
and `buildbox-run`'s only per-invocation argument is an opaque temporary
action file. The element name is nowhere in the chain.

### What this means for the fix

The three ranked candidates in "The information is available" are all
variants of *find a better field*, and the measurement says no such field
exists at shim time. The fix has to be a **correlation**, not a lookup:

- Each bwrap invocation is exactly one element's build, and every traced
  process descends from one such invocation.
- Plane 1 already knows each element's BUILD span in wall-clock time, and
  `UX-51`'s `bga correlate` already joins the planes.
- So an invocation whose window is contained in exactly **one** element's
  BUILD span can be attributed with certainty.

The honest part is the rest: under `--builders N` several BUILD spans
overlap, so some invocations will be contained in more than one. Those
must be reported as ambiguous and left unattributed rather than assigned
to the most likely candidate — `UX-46` already refuses to judge a
truncated read set, and a mis-attributed one is worse than a missing one.

This also needs the shim to record a per-invocation timestamp (the
`--argv-log` sidecar `UX-58` added is the natural place) and the hook's
`CLOCK_MONOTONIC` stamps anchored to wall-clock once at capture start.

## Fix Implemented

A **correlation**, since the investigation above ruled out every lookup.

1. **A layout-independent sandbox id.** The shim injects
   `BST_TRACE_INVOCATION` (its own pid — unique among concurrently-live
   host processes, which is the only scope that matters) alongside the
   collapsible element tag, and the hook emits it on every `START`/`END`
   and `OPENS` line. Traced processes now group exactly per element
   *build* even when their name is wrong, which is what makes a whole
   sandbox relabellable at once.
2. **A per-sandbox record** (`invocations.jsonl`, one line per bwrap
   invocation) carrying `CLOCK_REALTIME` at exec — deliberately not the
   hook's `CLOCK_MONOTONIC`, since the thing it must be matched against
   is Plane 1's wall clock.
3. **Constraint propagation, not matching.** An invocation whose start
   falls inside exactly one BUILD span is that element's, with certainty.
   An element hosts at most one sandbox, so resolving one removes it from
   every other candidate set, which may force the next; iterating to a
   fixed point makes deductions only. What is left over is returned as
   `ambiguous` (several consistent assignments), `conflicting` (two
   sandboxes forced onto one element — which invalidates the premise, not
   just the reach, so it is reported separately), or `unmatched`.

Nothing is guessed. `UX-46` already refuses to judge a truncated read
set; a *mis*-attributed one is worse than a missing one.

### Verified against the reproduction

`examples/06` with `build-root: /buildstream-build`, a real traced build:

| | before | after |
|---|---|---|
| processes with a real element name | **0 / 822** | **616 / 822** |
| distinct elements in `opens_captured` | 1 (`buildstream-build`) | **8** |
| invocations resolved | — | 7 certain, 0 ambiguous, 0 conflicting |

### The resolution limit, stated rather than hidden

On `examples/07` — the *same* override, but a 1.4-second build — the
correlation resolves almost nothing, and the reason is worth recording:
Plane 1's timestamps are stamped when the **wrapper reads** a line from
`bst`'s stdout, while an invocation is stamped when the **shim execs**.
The skew between those is small in absolute terms and irrelevant when
elements run for seconds or minutes, but on a build whose whole critical
path is 1.4s it moves invocations outside their element's span entirely —
they come back `unmatched`, which is the honest outcome rather than a
wrong one.

So this method's precondition is that element BUILD spans are long
compared to log-read latency. A real project satisfies that by a wide
margin (`freedesktop-sdk`'s heaviest element runs 1,226 seconds); a toy
project may not. The two unmatched invocations in the `examples/06` run
above are the same effect at its margin.

Tests: 12 new (`tests/unit/test_invocation_correlation.py`), covering
each outcome including the three ways the correlation must *decline* to
answer. Suite: 997 → 1009.

## Original filing

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
