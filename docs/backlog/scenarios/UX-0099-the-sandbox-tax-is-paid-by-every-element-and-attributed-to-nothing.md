# UX-99: the sandbox tax is paid by every element and attributed to nothing

**Priority:** Medium | **Status:** 🟡 In Progress — shipped and verified locally; the fdsdk half of the acceptance is waiting on a capture | **Depends on:** UX-91 (Plane 3 exists)

Direction 3, item 1 (first half) — see
[`design/directions.md`](../../design/directions.md).

## Motivation

Every element pays a fixed toll before and after its real work:
BuildStream stages its dependencies into the sandbox, integrates it,
stages sources, and caches the artifact afterwards. On a project that
stages a multi-hundred-MB sysroot into each of 90 sandboxes, that toll
is real wall-clock — and today it is invisible: Plane 1 books it inside
the element's span (or untracked head), attributed to the element's
"work"; Plane 2 never sees it (no process of the native build runs
during staging); no report names it.

The data already exists. Round 11 verified the persisted per-element
logs time each phase separately:

```text
[--:--:--] START   [e50dfdfd] core.bst: Staging dependencies at: /
[00:00:00] SUCCESS [e50dfdfd] core.bst: Staging dependencies at: /
[--:--:--] START   [e50dfdfd] core.bst: Integrating sandbox
...
[--:--:--] START   [e50dfdfd] core.bst: Caching artifact
[00:00:00] SUCCESS [e50dfdfd] core.bst: Caching artifact
```

`bga cache-logs` (UX-91) already parses this file format and already
extracts `Running commands`; it simply does not read the overhead
activities around it.

## Required Fix

Extend Plane 3's per-element phase model with the overhead activities:
`staging_dependencies`, `integrating_sandbox`, `staging_sources`,
`caching_artifact` — everything in the log that is not `Running
commands` is toll, and the split between toll and work is the point.
Report, per element and project-wide:

- toll seconds and toll share of the element's total, ranked;
- the project-wide line the direction argues for: *"sandbox overhead is
  X% of this project's element time"*;
- in JSON, the raw per-phase values (they feed UX-100).

State the known limit in the payload, as UX-91 does: one-second
resolution, so on sub-second phases the split is a floor, not a
measurement — the number is meaningful on real projects and noise on
toy ones.

## Out of Scope

- Artifact/staged-tree *sizes* (would need CAS queries; a second
  evidence axis for UX-100, not needed for the time split).
- Any recommendation (UX-100 consumes this; this task only measures).
- Plane 1 attribution changes (the toll stays inside the element span
  there; Plane 3 is where the split lives).

## Acceptance Test

On this machine's real log tree (the round-11 builds):
`bga cache-logs --project macro-micro-optimization-example-optimized`
shows the four overhead phases per element and the project-wide toll
line, with values consistent with the raw log lines above. On the fdsdk
element-logs tarball (published by the capture workflow since UX-91):
the toll share renders for the 25-element rebuild set, and the top
payer is named. Determinism: two runs over the same tree are identical.

---

## Fix Implemented

`sandbox_tax(records)` in `tools/bst_cache_logs.py`, rendered by
`bga cache-logs` and carried in its JSON.

**Three buckets, not two,** and the third is why this is trustworthy.
`work` is `Running commands`; `toll` is every other timed activity in
the build log; `unaccounted` is whatever the enclosing `Build`
activity's own total hands to neither. Folding the remainder into the
toll would inflate exactly the number the feature exists to report, so
it is published beside it.

Per element, `phase_breakdown` gains `work_us`, `toll_us` and
`toll_share` — computed over *all* phases, not the ones above
`PHASE_SHARE_FLOOR`. The floor decides which phases earn a printed row;
a toll that is small is still part of the split.

Two details that only show up on real logs:

- **The staging path is inside the activity name.** BuildStream writes
  `Staging dependencies at: /`, so a project staging at several prefixes
  would get one aggregate row per prefix and none of them would be the
  phase. `_phase_family` groups on the part before `at:`; each element
  keeps the exact string its own log carried.
- **Ranked by toll seconds, not by toll share.** A 90% toll on a 0.4s
  element is arithmetic; a 40s toll on a 90s element is a finding.
  Pinned by a test with exactly those two elements.

### Measured

On this machine's `examples/06` log tree — 27 build logs, 70.0s of
element time:

```text
Sandbox tax: 0.0s of 70.0s element time (0.0%) across 27 build log(s) went to
staging, integrating and caching rather than to the build itself
  Every overhead phase rounded to zero at BuildStream's one-second resolution -
  which is a real answer on a small project, and the reason this is a floor
  rather than a measurement
  (1.0s of the enclosing Build activity is in neither bucket - reported rather
  than folded into the toll)
```

That zero is the honest answer and it is the task's own prediction
(*"meaningful on real projects and noise on toy ones"*) confirmed rather
than assumed: BuildStream stages from CAS by hardlink, so even
`examples/06`'s 270 MB toolchain stages in under the one-second
resolution. A tool that printed a confident percentage here would be
printing rounding.

On a real log with a real toll — the bst 2.7.0 log the parser was built
against, 2s staging dependencies, 14s running commands, 1s caching the
artifact, 17s total:

```text
Sandbox tax: 3.0s of 17.0s element time (17.6%) across 1 build log(s) ...
    Staging dependencies                 2.0s
    Caching artifact                     1.0s
  Who paid it (by toll seconds, not by share):
    core.bst                             3.0s toll of 17.0s (18%)
```

Those three seconds were previously booked as `core.bst`'s work.

Tests: 7 new in `tests/unit/test_cache_logs.py`. Suite: 1255 → 1262.

### Not yet discharged

The acceptance's second half — *"on the fdsdk element-logs tarball, the
toll share renders for the 25-element rebuild set and the top payer is
named"* — needs a capture published since `UX-91` added the tarball. One
is running; this stays 🟡 until it is checked against it, because a
project whose staging is measured in minutes is the only place this
number is more than a floor.
