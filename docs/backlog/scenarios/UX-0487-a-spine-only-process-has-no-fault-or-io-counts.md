# UX-487: a spine-only process has no fault counts and no I/O, from a /proc read the spine already does

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-470` measured it | **Found by:** round 73, `tools/dev_plane_capability.py` | **Serves:** the reader whose slow element is a static binary, for whom Plane 2's I/O and fault columns are empty and nothing says why | **Topic:** capture

## Motivation

`UX-379` gave the hook six `rusage` fields it was already reading —
`inblock`, `oublock`, `majflt`, `minflt`, `nvcsw`, `nivcsw` — on the
argument that they are "the only measurement bga has of the two axes
it otherwise only models: what a process actually read and wrote, and
whether it was waiting or being preempted".

The spine got none of them, and the spine is the plane that exists for
the processes the hook **cannot see** — static binaries, and anything
that never loads the preloaded object. So exactly the population Plane
2 is blindest about is the one with no I/O and no fault counts.

Measured on a real mixed capture
(`examples/06-macro-micro-optimization/.bga/runs/20260829T174845Z`):

```text
spine END: 87   with minflt: 0
hook  END: 71   with minflt: 71
```

and on a two-queue capture generated this round
(`/tmp/ux469/.bga/runs/20260901T161438Z`, spine-only):

```text
spine END records:      30
  of them with minflt:  0
  of them with inblock: 0
```

`tools/dev_plane_capability.py` reports six, all on Plane 3:

```text
gap   /proc/<pid>/stat:minflt      exposed here (read as 7101) and no record key carries it
gap   /proc/<pid>/stat:majflt      exposed here (read as 0) and no record key carries it
gap   /proc/<pid>/io:read_bytes    exposed here (read as 1048576) and no record key carries it
gap   /proc/<pid>/io:write_bytes   exposed here (read as 9601024) and no record key carries it
gap   /proc/<pid>/io:rchar         exposed here (read as 33849637) and no record key carries it
gap   /proc/<pid>/io:wchar         exposed here (read as 9416730) and no record key carries it
```

The fault counts are the cheap half: `read_cpu_times` already reads
`/proc/<pid>/stat` into a buffer and its `sscanf` **skips** fields 10
and 12 with `%*u` on the way to `utime` and `stime`. Two conversions
in a read the spine already does, at the exit-stop where it already
stops.

`/proc/<pid>/io` is a second file and a second open per process, so it
is a real cost and a real decision — `rchar`/`wchar` are also
different quantities from `read_bytes`/`write_bytes` (syscall bytes
against block-layer bytes), and the hook's `inblock`/`oublock` are the
block-layer pair. Publishing all four would give Plane 3 two axes
Plane 2 does not have, which is its own inconsistency.

## Required Fix

- **`minflt` and `majflt` in the spine's `END` record**, from the
  `sscanf` that already has them, under the same key names the hook
  writes so `bst_native_build_tracer` needs no second vocabulary.
- **A decision on `/proc/<pid>/io`**, measured: what a second open per
  process costs on a real build, against what a spine-only element's
  missing I/O costs a reader. Either the `read_bytes`/`write_bytes`
  pair — the hook's `inblock`/`oublock` in bytes rather than 512-byte
  blocks, so the reader converts one of them — or a declared reason,
  which `UX-470`'s census reads from a declared list the way
  `dev_trace_coverage.DECLINED` does.
- **The census green on what is fixed**: the gaps this closes stop
  being reported, and `test_the_capability_census_discriminates.py`'s
  both-verdicts clause is the one that has to be re-pointed when the
  last gap goes.

## Out of Scope

- Anything the hook records — `UX-379` did that half and the census
  reports Plane 2 with **no** gaps.
- The `rusage` fields Linux does not maintain (`ru_ixrss`, `ru_idrss`,
  `ru_isrss`, `ru_msgsnd`, `ru_msgrcv`, `ru_nsignals`): `UX-470`'s
  probe exercised each and measured zero, so they are not gaps.
- Reading `/proc` on a *schedule* — a sampler is a different design
  with a different cost, and this is one read at a stop the spine
  already makes.

## Acceptance Test

```bash
python3 tools/dev_plane_capability.py
```

with the fault-count gaps gone and the `/proc/<pid>/io` four either
gone or declared, plus a real spine capture showing the new keys on
its `END` records — the `87 with minflt: 0` figure above, re-measured.

## Outcome

_Not started._
