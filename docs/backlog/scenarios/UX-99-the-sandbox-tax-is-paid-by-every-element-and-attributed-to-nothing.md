# UX-99: the sandbox tax is paid by every element and attributed to nothing

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-91 (Plane 3 exists)

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

```
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
