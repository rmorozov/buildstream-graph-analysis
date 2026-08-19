# UX-123: spine record hygiene — ENDs without STARTs, exec chains, and the nearest join

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-106, UX-107 (done — these are their S4/S5/S6)

## Motivation

Three record-level defects from round 12's `spine.c`/parser review,
none build-breaking, each quietly distorting the data:

1. **ENDs for processes that never exec'd.** `PTRACE_EVENT_EXIT` fires
   for every tracee including fork-without-exec children, whose
   "cmdline" is the parent's; the parser discards these ENDs, but the
   discard is **uncounted** — a whole record class neither reported nor
   summarized.
2. **Exec chains bill the first image.** `sh -c "gcc …"` execs in
   place, producing N STARTs and one END; FIFO pairing lands CPU, peak
   RSS and exit status on the *pre-exec* image and counts the surplus
   START as "no observed exit". The shell/compiler chain is the common
   case, and it plausibly accounts for part of fdsdk's 8,135
   unobserved exits.
3. **The stream join takes the first hook record within its 1.0s
   tolerance, not the nearest** — and the repo's own tests assert that
   `--unshare-pid` namespaces reuse small pids quickly, so a stale
   unmatched hook record can capture a later spine record for a reused
   pid.

## Required Fix

1. Do not emit an exit record for a pid with no exec START (or emit a
   distinct record type), and publish the drop/fork-only count in the
   report's coverage block.
2. Decide the exec-chain billing (last image is what a profiler means
   by "the process") and implement it in pairing for both streams; the
   unobserved-exits count should then drop measurably on the fdsdk
   capture, which is the check.
3. Nearest-within-tolerance for the stream join.

## Out of Scope

- The hang paths (UX-117/118) and signal model (UX-119).
- hook.c's own pre-existing exec-chain shape beyond what shared
  pairing code fixes.

## Acceptance Test

A fixture build with a fork-no-exec child and an exec chain: no
phantom END rows, the chain's CPU/RSS/exit billed to the final image,
the fork-only count published. On the retained fdsdk spine capture,
re-parsed: unobserved-exit count reported lower with the delta
explained, and no join pairs a reused pid across a gap larger than the
nearest candidate's.

---

## Fix Implemented

### 2 first, because it was the big one

`sh -c "gcc …"` execs in place: N STARTs, one END. Pairing the END with
the **first** START billed the pid's whole CPU, peak RSS and exit status
to the pre-exec image. On freedesktop-sdk, **7,384 records** — one for
essentially every unobserved exit in the capture:

```text
billed to:  'sh -c -e python -P -mbuild --no-isolation --wh…'
really ran: 'python -P -mbuild --no-isolation --wheel --out…'   cpu=195219
```

The visible consequence, on the same capture's retained head — the
question Plane 2 exists to answer, *where did the CPU go*:

| | 1st | 2nd | 3rd | 4th |
|---|---|---|---|---|
| before | cc1plus 8.3s | cc1 3.4s | **sh 2.6s** | install-info 1.3s |
| after | cc1plus 8.3s | cc1 3.4s | **python 2.3s** | install-info 1.3s |

The third-largest consumer in the build was a shell that had exec'd away
four seconds earlier.

**The chain is collapsed into one record**, not re-paired. That is the
physically correct model rather than a choice between images:
`/proc/<pid>/stat` and `getrusage` are both per-**pid** and cumulative
across execs, so the figures describe the process, and the span runs from
the first exec to the exit. The name is the last image, which is what a
profiler means by "the process". `exec_chain` is published per record so
a collapse is visible as a collapse.

The check the task names, on real data:

| | records | unobserved exits |
|---|---|---|
| freedesktop-sdk (retained 4 MB head) | 1833 → **1812** | 37 → **16** |
| `examples/06` | 822 → **813** | 9 → **0** |

### 1: exits for pids that never exec'd

`PTRACE_EVENT_EXIT` fires for every tracee, including fork-without-exec
children — which are the same program as their parent and wear its
cmdline. Those ENDs were already dropped; they are now **counted**, by
`count_fork_only_exits` over the same events, and published in the
coverage block. **552** of them in the fdsdk head. A record class that is
neither shown nor mentioned is indistinguishable from one that never
occurred.

Counted in the parser rather than suppressed in `spine.c`: the tracer
would have to carry a second per-pid table to know, and the parser
already has the whole event stream in front of it.

### 3: nearest-within-tolerance

The join took the first hook record inside the tolerance rather than the
nearest. A `--unshare-pid` sandbox recycles small pids quickly — this
repository's own tests assert it — so a stale unmatched record could
capture a later spine record by being first in a list. Now the minimum
by |Δstart|, with a test that puts the stale one first.

Tests: 7 in `tests/unit/test_spine_record_hygiene.py`. Suite unchanged at
1445 before them, so nothing existing depended on the old billing.

## Verification Log

Done 2026-08-19. Before/after figures from re-parsing two retained real
captures with the code stashed and unstashed, not from a fixture.
