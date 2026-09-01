# UX-487: a spine-only process has no fault counts and no I/O, from a /proc read the spine already does

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-470` measured it | **Found by:** round 73, `tools/dev_plane_capability.py` | **Serves:** the reader whose slow element is a static binary, for whom Plane 2's I/O and fault columns are empty and nothing says why | **Topic:** capture

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

## Outcome (round 73, 2026-09-01) — 🟢 Done

### After

```text
python3 tools/dev_plane_capability.py

Plane 3 - the ptrace spine

    records      END, START

    declined      /proc/<pid>/io:rchar         syscall-level bytes, an axis
                                               neither plane has ... (UX-487)
    recorded      /proc/<pid>/io:read_bytes    inblock
    declined      /proc/<pid>/io:wchar         the same, in the other direction
    recorded      /proc/<pid>/io:write_bytes   oublock
    recorded      /proc/<pid>/stat:majflt      majflt
    recorded      /proc/<pid>/stat:minflt      minflt
    recorded      /proc/<pid>/stat:stime       stime
    recorded      /proc/<pid>/stat:utime       utime
    recorded      /proc/<pid>/status:VmHWM     maxrss_kb

0 gap(s): none
```

Both planes now report no gaps: Plane 2 had none (`UX-470` measured
that the six `rusage` fields the hook does not record are ones this
kernel does not fill), and Plane 3's six are four recorded and two
declared.

And the records themselves, from one workload traced by **both planes
at once**:

```text
pid   1294 spine  inblock=0  oublock=    0  minflt= 91   sh -c dd ...; sync
pid   1295 hook   inblock=0  oublock=16392  minflt=339   dd if=/dev/urandom ...
pid   1295 spine  inblock=0  oublock=16392  minflt=339   dd if=/dev/urandom ...
pid   1296 hook   inblock=0  oublock=    0  minflt= 82   sync
pid   1296 spine  inblock=0  oublock=   16  minflt= 82   sync
```

### The fault counts were free

`read_cpu_times` reads `/proc/<pid>/stat` into a buffer and its
`sscanf` **skipped** fields 10 and 12 with `%*u` on the way to `utime`
and `stime`. Two more conversions in a read the spine already did, at
a stop it already made.

### The block counts, and the trap under them

`getrusage`'s `ru_inblock` is the kernel's `read_bytes >> 9` and
`ru_oublock` is `write_bytes >> 9`, which is what `/proc` publishes for
another process — so the spine can write **the hook's own keys in the
hook's own units** and `bst_native_build_tracer` needs no second
vocabulary. Measured in one process at one instant:

```text
read_bytes   8388608  >>9 = 16384   ru_inblock  16384
write_bytes 16797696  >>9 = 32808   ru_oublock  32808
identical: True
```

**But not from `/proc/<pid>/io`.** That file folds in *reaped
children*, the way `RUSAGE_CHILDREN` does. The first implementation
read it, and the both-planes comparison caught it before it shipped:

```text
pid 1261 spine  oublock=16408   sh -c dd ...; sync      <- wrong
pid 1262 hook   oublock=16392   dd ...
pid 1262 spine  oublock=16392   dd ...                  <- agrees
```

16408 = 16392 + 16, a shell that wrote nothing charged with both its
children's blocks. Proved directly — fork a child that writes 8 MiB,
reap it, read both files for the parent:

```text
/proc/<pid>/io           write_bytes 8409088   (the child's)
/proc/<pid>/task/<t>/io  write_bytes       0   = RUSAGE_SELF
```

`/proc/<pid>/task/<pid>/io` is the task's own, and that is what ships.
For a multi-threaded process it is the *named task's* bytes where the
hook's `RUSAGE_SELF` is the thread group's — the right grain here
rather than a shortfall, because the spine seizes with
`PTRACE_O_TRACECLONE` and every thread is a tracee with its own record.

### What the third `/proc` read costs

Measured over 800 processes doing nothing but exec and exit — the
pessimal case for a fixed per-process cost, since a real build's
processes do work. Nine runs of each, medians:

```text
as shipped        median 1220.5 ms  (1160 1185 1198 1219 1220 1222 1222 1245 1254)
with the io read  median 1248.3 ms  (1189 1206 1213 1234 1248 1263 1283 1315 1372)
```

+27.8 ms over 800 processes: **~35 µs each, +2.3%**, for the only I/O
measurement Plane 3 can have. Taken.

`rchar`/`wchar` are in the same file and are **declined**: syscall-level
bytes are an axis neither plane has, and giving it to the spine alone
would put a column in the record that is populated for the processes
the hook could not see and empty for the rest. The reason lives in
`dev_plane_capability.DECLINED`, the same shape as
`dev_trace_coverage.DECLINED`.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| Q1 | read `/proc/<pid>/io` again, so reaped children fold back in | 1 of 17 — `test_the_shell_that_spawned_it_is_not_charged_for_it` |
| Q2 | the fault counts are not written | 4 failed + 5 errors of 17 — the record clause, both agreement clauses, the parser clause, and the capability census refusing at `_check_map` |
| Q3 | the block counts are raw bytes rather than 512-byte blocks | 1 of 17 — `test_the_block_counts_are_identical` |

Each was proved to have landed with a `grep -c` before the run, and
reverted from a copy after it.

### The clause `UX-470` left, re-pointed

`test_the_census_finds_a_gap_and_an_unmaintained_field` asserted a gap
existed, and said in its own message that closing them was the point of
filing them. There are none left, so the easy version of that clause is
gone. What replaces it asks the harder question — **can the census
still produce a gap?** — by stripping one field from the name map over
the same real run and asserting it comes back reported. Without that,
"0 gaps" would be indistinguishable from an instrument that stopped
looking.

### Deviation from the Required Fix

- **None on the fields.** The two the item called the cheap half are
  recorded, the `/proc/<pid>/io` decision was measured and taken, and
  the two not taken carry a declared reason.
- The item said "under the same key names the hook writes so
  `bst_native_build_tracer` needs no second vocabulary". That is
  literally true and was verified rather than assumed: the parser
  converts the spine's `oublock` through `_IO_BLOCK_BYTES` into
  `written_bytes` with no change to it at all.

### The runs

```text
python3 -m pytest tests/unit/test_a_spine_record_carries_what_the_hook_would_have.py -q
                     7 passed in 0.64s
make test-touching   334 passed in 30.52s
make test            5,669 passed, 27 skipped in 316.55s (0:05:16)
make lint            ruff + PyMarkdown, both clean
```
