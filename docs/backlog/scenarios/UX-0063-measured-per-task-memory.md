# UX-63: the memory oversubscription guard runs entirely on operator-declared estimates, on a blocker that has since been removed

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-21`, `UX-45` (both done) | **Topic:** capture | **Area:** tools/native_trace

## Motivation

`UX-21` added a memory dimension to the oversubscription guard, because
swap thrashing is a worse real failure mode than CPU contention. It works
on two *declared* numbers — `--memory-budget-mb` and
`--estimated-job-memory-mb` — and its Out of Scope explained why:

> Real, measured per-task memory accounting (would need the same kind of
> intra-sandbox visibility `UX-11`'s own native-build-system profiler
> brainstorm already identifies as a separate, large, future tool)

That tool is no longer future. It shipped as `UX-11`, and `UX-45` then
put `getrusage` in its destructor to capture real per-process CPU time.
The same `struct rusage` already being read carries `ru_maxrss` — peak
resident set size — one field away from the numbers `UX-21` currently
asks the operator to guess.

## What this would make possible

`UX-21`'s guard can presently only answer "is your declared budget
consistent with your declared per-job estimate", which is arithmetic on
two inputs the user supplied. With a measurement it could answer the
question they actually have: *does this build fit in this machine?*

It also has a sharper form on real data. The `freedesktop-sdk` capture's
heaviest element (`cmake-stage1`, 1,226 seconds) is exactly the kind of
element whose peak RSS decides whether `--builders 4` is safe, and
nothing in the pipeline records it.

## Required Fix

1. Record `ru_maxrss` for `RUSAGE_SELF` and `RUSAGE_CHILDREN` alongside
   the CPU fields already emitted on END lines. Note the unit trap:
   `ru_maxrss` is kilobytes on Linux and bytes on macOS, and it is a
   *peak*, not a sample, so summing it across processes overstates a
   concurrent total.
2. Aggregate per element, with the same coverage honesty `UX-45`
   established — a measured maximum over 93% of processes is reported as
   such, never as a total.
3. Feed it to `UX-21`'s guard as a measured alternative to the declared
   estimate, keeping the declared path for runs with no Plane 2 capture.

## Out of Scope

- Changing `UX-21`'s guard *semantics*. This supplies a better input to
  the same check.
- Cgroup-level accounting, which measures the same thing more accurately
  but requires privileges the sandbox does not have.

## Acceptance Test

1. A real traced build reports a per-element peak RSS, with coverage.
2. Summing peaks is explicitly refused as a concurrent-total estimate,
   with the reason stated.
3. `UX-21`'s guard consumes the measurement when present and the declared
   estimate when not, and says which it used.

## Fix Implemented

`ru_maxrss` is emitted on every END line from the `struct rusage` the
hook was already reading, as `maxrss_kb=` / `cmaxrss_kb=`, and aggregated
per element by `compute_peak_memory`.

Reported as a **maximum, never a sum**, and that distinction is the whole
point rather than a caveat on top of it. Two processes that each peaked
at 500 MB at different moments never held 1 GB between them; summing
peaks would manufacture a concurrent total nothing measured — the same
class of error as reading occupancy as CPU (`UX-36`) or summing
per-element redundancy savings (`UX-37`). What the figure *can* support
is "no single process in this element exceeded X", which is exactly the
per-job input `UX-21`'s guard currently asks the operator to estimate.
The report says so on its own line.

The unit trap is handled at the boundary: `ru_maxrss` is kilobytes on
Linux and bytes on macOS, so it is carried through verbatim in KiB and
converted only for display.

One implementation note worth keeping, because it cost a debugging round:
`pair_events` builds a **fresh** record from a START/END pair and copies
only named keys, so a field added to the hook is silently dropped unless
copied there too. The first attempt emitted the field correctly, parsed
it correctly, and still reported "unavailable". That is now pinned by
`test_the_field_survives_start_end_pairing`.

### Verified on a real build

```text
Peak Memory (largest single process per element):
  base.bst                 20.6 MB  (63 of 78 processes measured)
  unrelated.bst            20.6 MB  (63 of 78 processes measured)
  user.bst                 20.6 MB  (63 of 78 processes measured)
  NOTE: a per-process peak, not a concurrent total - these are maxima
        and must not be summed.
```

Coverage is reported rather than assumed, matching `UX-45`: the 15
unmeasured processes per element are the `sh -c` wrappers that `_exit()`
past the destructor, already documented in `open_records_note`.

Tests: 6 new (`tests/unit/test_peak_memory.py`). Suite: 991 → 997.

## Verification Log

Filed and implemented 2026-08-17. `UX-21`'s deferral is quoted verbatim from its Out of
Scope. The absence of any RSS capture was confirmed by grepping
`tools/native_trace/hook.c`, which reads `ru_utime`/`ru_stime` from the
same `struct rusage` and no other field.
