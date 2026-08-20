# UX-149: doctor checks the parts, and nothing checks the chain

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-125/UX-142 (doctor), UX-146/UX-147/UX-148 (the diagnostics it composes)

## Motivation

The field failure's diagnostic dead-end, restated as the gap between
two tools: `bga doctor` proves the *parts* work (bst runs, bwrap builds
a sandbox **with bga's own arguments**, a compiler exists), and
`--diagnose` instruments the *user's real build* — which costs a real
build and yields its evidence only after the failure. Nothing in
between runs the actual chain — `bst` → `buildbox-run` → the PATH shim
→ the rewritten argv → the hook loading inside the sandbox — on a
**canned, ten-second workload** with every recorder on. That probe is
the first thing a helper wants a remote user to run, and today the
instruction would be "add --diagnose to your real failing build and
send three files".

## Required Fix

`bga doctor --capture [PROJECT_DIR]` (name per doctor's existing
grammar): stage a one-element, one-command probe project into a temp
dir (a `manual` element echoing a marker — reusing the staged-shell
detection doctor already does, and skipping with the `stage_*.sh`
remedy when no shell can be staged), then run one traced `bst build`
of it with UX-146 diagnostics, the UX-147 self-probe, and UX-148's
stderr tee all on. Report per link, in chain order, each `ok`/`FAIL`
with its evidence file:

```text
  [ok  ] shim exec self-probe (interpreter /usr/bin/python3.12)
  [ok  ] bst launched a sandbox (1 build task)
  [FAIL] shim reached through buildbox-run: 0 invocations
         -> a buildbox-casd started 2h before this capture is still
            running; its PATH predates the shim. <remedy>
  [skip] hook records (unreachable: the shim never ran)
```

Exit 0 only when the chain is whole; `--format json` with check ids,
like doctor. The failure modes it must classify are exactly UX-147's
three causes plus "shim ran, hook produced no records" (static-only
shell, or LD_PRELOAD stripped) — each already individually detectable
by the pieces this composes.

## Out of Scope

- Diagnosing the user's real project's build failures (that stays
  `--diagnose` on the real build; this proves the machinery before
  blaming the project).

## Acceptance Test

On this container: `bga doctor --capture` exits 0 with every link ok,
end to end, in under ~30s. Each classified failure is reproduced live
once and shows its named verdict: the round-15 fake bwrap (sandbox
launched, shim ran, real bwrap failed → stderr quoted), a shim dir
made non-executable (self-probe FAIL, chain short-circuits with
`skip`s), and a PATH-bypass simulation (shim never reached →
cause-2 text). The probe leaves nothing behind (temp project and
cache keys cleaned, asserted the way doctor's read-only test works).
