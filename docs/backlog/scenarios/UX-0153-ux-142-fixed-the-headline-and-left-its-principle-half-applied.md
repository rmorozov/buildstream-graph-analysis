# UX-153: UX-142 fixed the headline and left its principle half-applied

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-142 (the fix this completes), UX-125 (doctor's probe principle)

## Motivation

UX-142's headline fix is real: doctor's project probe reads
`element-path:` from `project.conf` and passes on the first loadable
element — a project without `all.bst` works. But the round-15 review
found the same assumption surviving around it:

1. **`check_staged_sources` still hardcodes `elements/`**
   (`tools/bga_doctor.py:299`) and SKIPs when it is absent — on a
   project with `element-path: files`, the check silently stops
   running while `element_path()` sits two functions away.
2. **The tracer's census does the same in seven places**
   (`tools/bst_native_build_tracer.py:1611, 1644, 1762, 1800, 3056,
   3960, 4069`). This one has a cost: `bga snapshot` defaults to
   `--trace-spine=auto`, and with no `elements/` the census comes back
   empty, every element reads "unassessed", and the fail-safe traces
   *everything* — correct, but silently at full spine price on exactly
   the nonstandard-layout projects UX-142 was filed for.
3. **An acceptance clause was dropped unrecorded**: "wire it as a
   workflow step so the check meets a real project every capture" —
   `real-project-capture.yml` is untouched; the only doctor step in CI
   runs against `examples/06`, the same fixture convention the item
   was filed against.
4. **`check_compiler` tests presence, not capability**, against
   UX-125's own probe-don't-check principle — and the spine link is
   `cc -static`, a separate capability (static libc) that plain
   `build-essential` does not guarantee.

## Required Fix

Route `check_staged_sources` and the tracer census through
`element_path()`; add a doctor step to `real-project-capture.yml` (or
record the deviation with a reason in UX-142's log); make
`check_compiler` compile a trivial `-shared -fPIC` object and, when
spine is in play, a trivial `-static` link, reporting which capability
is missing.

## Out of Scope

- Doctor's other checks (verified behaving as filed).
- The whole-chain probe (UX-149 — this item is about the parts being
  honest; that one is about the chain).

## Acceptance Test

A copy of `examples/06` with `element-path: files` (elements moved):
doctor runs *all* its checks including staged-sources, and a snapshot's
census assesses elements rather than tracing everything as
"unassessed" (assert on the capture summary's census line). On a
machine without static libc (simulated by a PATH shim hiding the
static archive), doctor names the `-static` gap instead of passing on
`cc`'s existence. The CI workflow shows the doctor step or UX-142's
log records why not.


---

## What was built

1. **One `element_path`, in the tracer**, where the census needs the
   answer in seven places; doctor imports it. Two copies of a rule about
   project layout is how this became a finding twice.
2. **`check_staged_sources` reads it** and says which directory it
   looked for when there is none, instead of SKIPping on a hardcoded
   `elements/`.
3. **The capture workflow runs doctor against freedesktop-sdk**, before
   an hour of build — the acceptance clause `UX-142` dropped. Not a
   gate: doctor exits non-zero only on a real failure, and a warning on
   a real project (no top-level `elements/`, no Plane 3 logs on a fresh
   runner) is information. The exit code is captured off `PIPESTATUS[0]`
   into a variable on the next line, because every later command
   rewrites it — including the `echo` that reports it, which the first
   version of that step got wrong.
4. **`check_compiler` probes instead of checking**: a trivial
   `-shared -fPIC` link for the hook and a trivial `-static` link for
   the spine, compiled from stdin to `/dev/null` so nothing is written.
   A compiler that cannot link `-static` — a separate package on some
   distributions — now **warns and says which capability is missing**,
   rather than reporting a spine that will not build as a healthy
   environment.
