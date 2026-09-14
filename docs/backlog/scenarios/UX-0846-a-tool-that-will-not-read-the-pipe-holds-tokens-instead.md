# UX-846: a tool that will not read the pipe holds tokens instead

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843 | **Found by:** round 117, Direction 20 | **Serves:** R4 (links stop oversubscribing under the mode) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`ld.lld` 18 sizes `--threads` to every core, gold and mold likewise,
ninja 1.11 has no client, rustc's codegen units and ThinLTO's jobs run
their own pools - none reads `MAKEFLAGS`. Under the mode each is a
sandbox that took one implicit token and used sixteen cores. LLVM 22
speaks the jobserver across clang, lld and LTO (the user's brief;
verified at capture, not assumed), `gcc -flto=jobserver` joins since
GCC 10, cargo is a client.

## Required Fix

`tools/native_trace/wrappers/`: one wrapper script per tool, on a
`PATH` directory the shim bind-mounts first (key-invisible, like the
hook). A wrapper acquires `K = min(cap, tokens readable now)` from the
FIFO without blocking longer than 50 ms, runs the tool with
`--threads=K` (`-jK` for ninja, `-Cjobs=K`-equivalents where they
exist), and returns the tokens on exit through a trap; if none is
readable it runs with the implicit token alone. A tool whose `--help`
names a jobserver flag is passed the auth and wrapped by nothing; the
capture probes each tool once and records the policy table
(`tool, version, policy`) in the report. The safe default is `1`.

## Decomposition

Input classes: lld 18 (held), gcc `-flto=jobserver` (pass-through),
ninja 1.11 (held) and a ninja with a client (pass-through), a tool that
is killed mid-link (tokens returned by the trap). The journey it
extends is R4's capture of a project with a large final link.

## Out of Scope

Rewriting argv from the hook at `exec` - declined: a `PATH` wrapper
is observable in the run and a hook rewrite is not.

## Acceptance Test

`tests/unit/test_a_held_tool_returns_its_tokens.py` runs the `lld`
wrapper against a pool of 4 with a fake `ld.lld` that prints its
`--threads`, asserts 3 held and 4 readable after exit, and the same
for a killed fake; mutation: drop the trap - red.
