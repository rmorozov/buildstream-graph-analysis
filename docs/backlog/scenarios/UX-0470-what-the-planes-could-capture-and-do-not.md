# UX-470: nothing compares a plane's capability with the records it writes

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** none; `UX-466` named the gap and declined to guess at it | **Found by:** round 72, closing `UX-466` stage 3 | **Serves:** the round that wants a signal the hook could already have produced and has no way to know it | **Topic:** capture | **Area:** tools

## Motivation

`UX-466` asked three questions and answered two. Its stage 3 was
written as *"what the planes could capture and do not"*; what the
census could honestly answer was *"what the planes do capture and the
trace drops"*. Those are different, and the difference was declared
rather than folded in:

> The other half needs a comparison between the hook's *capability* -
> the syscalls it interposes, the `rusage` fields it reads - and the
> records it writes, which is a third instrument over `tools/` rather
> than over emitted artifacts.

`UX-379` is the precedent for the gap being real: the hook was already
reading `rusage` fields it did not record, and a round had to notice by
reading the source. That is the sighting this item would make
mechanical.

## Required Fix

An instrument that reads, per plane, what the code *can* observe and
what its record schema *carries*, and reports the difference.

Unlike `UX-466`'s census this one necessarily reads source — the
capability is not in any emitted artifact — so it is a **text scan**,
which fixing guide §5 is about. That has to be handled rather than
ignored: the scan reads the interposed symbol list and the record
struct, both of which are declarations rather than prose, and every
answer it gives must be checkable against a real capture before it is
believed. A finding it reports and a capture cannot confirm is a
finding about the scan.

That difficulty is why this is filed at Low and separately, rather
than done inside `UX-466`.

## Out of Scope

- Adding any field to any plane — this measures, and what it finds
  gets filed.
- Fields the capture already holds and the trace drops: `UX-469`.
- Plane 1, whose capability is BuildStream's log format rather than
  this repository's code, and which `UX-110` already measured for
  read-lag.

## Acceptance Test

The instrument's output over both Plane 2 and Plane 3, pasted, with
every reported gap either filed as a row or confirmed against a real
capture — and, per the Required Fix, at least one confirmed the hard
way before any of it is quoted elsewhere.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The instrument

`tools/dev_plane_capability.py`, run over both planes:

```text
python3 tools/dev_plane_capability.py

Plane 2 - the LD_PRELOAD hook

    interposes   open, open64, openat, openat64
    records      END, OPENS, START

    unmaintained  ru_idrss     the probe exercised it and this kernel left it at zero
    recorded      ru_inblock   inblock
    unmaintained  ru_isrss     the probe exercised it and this kernel left it at zero
    unmaintained  ru_ixrss     the probe exercised it and this kernel left it at zero
    recorded      ru_majflt    majflt
    recorded      ru_maxrss    maxrss_kb
    recorded      ru_minflt    minflt
    unmaintained  ru_msgrcv    the probe exercised it and this kernel left it at zero
    unmaintained  ru_msgsnd    the probe exercised it and this kernel left it at zero
    recorded      ru_nivcsw    nivcsw
    unmaintained  ru_nsignals  the probe exercised it and this kernel left it at zero
    unexercised   ru_nswap     moving it means forcing the host to swap, which an
                               instrument must not do to the machine it runs on
    recorded      ru_nvcsw     nvcsw
    recorded      ru_oublock   oublock
    recorded      ru_stime     stime
    recorded      ru_utime     utime

Plane 3 - the ptrace spine

    records      END, START

    gap           /proc/<pid>/io:rchar         exposed here (read as 33849652) and no record key carries it
    gap           /proc/<pid>/io:read_bytes    exposed here (read as 1048576) and no record key carries it
    gap           /proc/<pid>/io:wchar         exposed here (read as 9416741) and no record key carries it
    gap           /proc/<pid>/io:write_bytes   exposed here (read as 9584640) and no record key carries it
    gap           /proc/<pid>/stat:majflt      exposed here (read as 0) and no record key carries it
    gap           /proc/<pid>/stat:minflt      exposed here (read as 7100) and no record key carries it
    recorded      /proc/<pid>/stat:stime       stime
    recorded      /proc/<pid>/stat:utime       utime
    recorded      /proc/<pid>/status:VmHWM     maxrss_kb

6 gap(s): /proc/<pid>/io:rchar, /proc/<pid>/io:read_bytes,
          /proc/<pid>/io:wchar, /proc/<pid>/io:write_bytes,
          /proc/<pid>/stat:majflt, /proc/<pid>/stat:minflt
```

### It is almost not a text scan, which is what the item was worried about

The Required Fix expected a scan and said the difficulty was why this
was filed at Low. Almost none of it is one, because **both sides can
be run**:

| what | where it comes from |
|---|---|
| the hook's observable universe | `struct rusage` as this kernel fills it, through CPython's `resource` — the same struct `hook.c` calls `getrusage` into |
| what the hook records | `hook.c` compiled and a real process run under it; the keys read off the record it writes |
| what it interposes | `nm -D --defined-only` over that compiled object |
| the spine's observable universe | the `/proc/<pid>` fields this kernel exposes, read here for a live process |
| what the spine records | `spine.c` compiled and a real process traced with it |

The one declaration is the **name map** — that the record's
`maxrss_kb` is `ru_maxrss`. No measurement can supply a mapping
between two vocabularies, so it is written down, and `_check_map`
holds every key it claims against a real record and exits loudly if
one is not there. Without that, a renamed record key turns a recorded
field into a reported gap and the census files a row about work
`UX-379` already did.

### The verdicts, and why `unmaintained` is a measurement

Seven `rusage` fields the hook does not record. Six of them the probe
**exercises** — it touches 64 MB, `fsync`s an 8 MB write, reads it
back with `O_DIRECT` so the read reaches the device, delivers 200
signals to itself, sends 200 socket messages and yields 200 times —
and this kernel leaves all six at zero. That is what Linux documents
for `ru_ixrss`, `ru_idrss`, `ru_isrss`, `ru_msgsnd`, `ru_msgrcv` and
`ru_nsignals`, measured rather than quoted. The seventh, `ru_nswap`,
is reported `unexercised`: moving it means forcing the host to swap,
which an instrument must not do.

So **Plane 2 has no gaps**, and the answer `UX-379` left open is
closed: the hook records every `rusage` field this kernel fills.

### The gap, confirmed the hard way

The Required Fix asks for at least one gap confirmed against a real
capture before any of it is quoted. `minflt`, on a real mixed capture
(`examples/06-macro-micro-optimization/.bga/runs/20260829T174845Z`):

```text
spine END: 87   with minflt: 0
hook  END: 71   with minflt: 71
```

Every hook record carries it; no spine record does. And on a
spine-only capture generated this round
(`/tmp/ux469/.bga/runs/20260901T161438Z`):

```text
spine END records:      30
  of them with minflt:  0
  of them with inblock: 0
```

The population Plane 3 exists for — processes the hook cannot see —
is exactly the one with no fault counts and no I/O. All six gaps are
filed as `UX-487`.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| N1 | the probe reads without `O_DIRECT`, so the read is served from page cache | 1 of 9 — `test_the_probe_reaches_the_block_layer` |
| N2 | the name map claims `ru_minflt` is written as `min_faults` | 4 passed, **5 errors** — `_check_map` refuses at census time, which is the loud refusal it is for |
| N3 | the record-kind scan takes the first token of every line | 2 of 9 — both clauses in `TestTheRecordKindsAreKindsAndNotPaths` |
| N4 | the `gap` verdict is made unreachable | 1 of 9 — `test_the_census_finds_a_gap_and_an_unmaintained_field` |

Each was proved to have landed with a `grep -c` before the run, and
reverted from a copy after it.

### What its own first run got wrong

The record-kind scan read the first token of every line, and the
`OPENS` record is followed by the paths it recorded, one per line. It
reported **35 `.pyc` files as Plane 2 record kinds**. Found by reading
the output rather than by a clause, which is why `_KIND` exists and
why a clause holds it now.

### Deviation from the Required Fix

- **The scan is smaller than the item expected**, and that is the
  deviation worth naming: the item budgeted for a text scan over
  `tools/` and warned about §5. Compiling and running both planes
  turned out to be cheap — 1.2s for the whole guard — so the scan
  shrank to one declared name map with a check on it. The item's
  worry was right and the answer was to remove most of the scan
  rather than to defend it.
- **`ru_nswap` is judged by neither side.** Declared `unexercised`
  rather than guessed at in either direction.

### The runs

```text
python3 -m pytest tests/unit/test_the_capability_census_discriminates.py -q
9 passed in 1.03s

make test-touching   499 passed in 19.36s
make test            5,651 passed, 27 skipped in 328.49s (0:05:28)
make lint            ruff + PyMarkdown, both clean
```
