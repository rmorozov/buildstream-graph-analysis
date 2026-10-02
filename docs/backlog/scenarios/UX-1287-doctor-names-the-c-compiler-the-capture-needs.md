# UX-1287: `bga doctor` names the C compiler the capture compiles its hook with

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** none | **Found by:** the 2026-10-02 state audit: `compile_hook` and `compile_spine` (`tools/bst_native_build_tracer.py:168-191`) need `cc` or `gcc` at capture time, and `bga doctor` checks bst, bwrap and the shim only | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_doctor.py` (`TestTheHookIsCompiledOnce`)

## Motivation

The hook and the spine are compiled when a capture starts, not when
bga is installed. A CI agent image built for BuildStream need not
carry a host compiler, so the first capture on it fails with a
`TraceError` after the agent was declared ready. `bga doctor` is the
preflight an infrastructure team runs on a new image, and it is
silent on this prerequisite.

## Decomposition

Input classes: `cc` on PATH; only `gcc`; neither; a `cc` that cannot
compile (no libc headers). Journey: `bga doctor` on a fresh agent.

## Required Fix

`bga doctor` reports the compiler the capture would use and compiles
the hook once into a scratch directory, so a present but broken
compiler is caught as well as a missing one. Missing or broken is a
failing check naming the package to install; the message matches the
one `compile_hook` raises.

## Out of Scope

Shipping a precompiled hook in the wheel.

## Acceptance Test

PATH with no compiler: `bga doctor` exits non-zero naming `cc`.
A `cc` stub that exits 1: the same, naming the compile failure.

## Outcome

**The gap, measured.** The audit's premise was half-right: `check_compiler` existed (`UX-125`/`UX-153`) but restated the compiler choice and its own message, and probed a trivial program, so a broken `cc` was a `warn`. `ac.py` (scratchpad: `bga doctor` under `PATH=<empty dir>`, then `PATH=<dir with a cc that prints to stderr and exits 1>`), at `1448af2c7`:

```text
== PATH=nocc  exit=1
  [FAIL] c-compiler: no C compiler (cc/gcc) on PATH - Plane 2 compiles its LD_PRELOAD hook and ptrace spine at capture time
== PATH=badcc  exit=1
  [warn] c-compiler: …/badcc/cc cannot link: -shared -fPIC (the LD_PRELOAD hook), -static (the ptrace spine)
```

Exit 1 in both is `bst`/`bwrap` missing under that PATH, not the compiler: the `c-compiler` line is the reading.

**The close, measured.** `c_compiler(purpose)` in the tracer is the one choice and message; `compile_hook`/`compile_spine` and doctor call it, and doctor runs `compile_hook` into a removed scratch dir. Same script, this tree:

```text
== PATH=nocc  exit=1
  [FAIL] c-compiler: no C compiler (cc/gcc) found on PATH - required to build the LD_PRELOAD hook
           -> apt-get install -y build-essential (Plane 1 and Plane 3 work without it; only `bga capture` needs it)
== PATH=badcc  exit=1
  [FAIL] c-compiler: failed to compile …/tools/native_trace/hook.c:
           cc: fatal error: stub
           -> apt-get install -y build-essential (Plane 1 and Plane 3 work without it; only `bga capture` needs it)
```

This host: `[ok  ] c-compiler: C compiler at /usr/bin/cc builds the hook and links static`. `tests/unit/test_doctor.py`: `39 passed, 8 skipped in 3.53s`. The `-shared -fPIC` trivial probe is gone (the real hook supersedes it); the `-static` probe stays a `warn`.

| mutation | reddened | run |
|---|---|---|
| M1 `compile_hook(scratch)` → `pass` | broken cc fails naming the failure | 1 failed, 2 passed |
| M2 doctor rewords the missing-cc summary | no compiler fails with the capture's message | 1 failed, 2 passed |
| M3 `FAIL` → `WARN` on a `TraceError` | both | 2 failed, 1 passed |
| M4 `mkdtemp` instead of `TemporaryDirectory` | scratch directory is removed | 1 failed, 2 passed |
| M5 compiler stderr dropped from `detail` | broken cc fails naming the failure | 1 failed, 2 passed |
| reverted | — | 39 passed, 8 skipped |
