# UX-1082: the cache key set is read without the build's own options, and silently

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5, R1 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

Before `bst build` starts, the tracer runs `bst show --format
'%{name} %{full-key}' <targets>` (`tools/bst_native_build_tracer.py:8503-8520`)
to record the key set (`UX-844`). It passes only the targets
(`bst_command_targets`), not the global options the build was given:
`bst -o arch aarch64 build all.bst` records the keys of the default
options, so two variants' key sets compare as the same build. The
`extract_run` call already forwards them (`_bst_global_options`,
`UX-870`); this one does not. It is also `shutil.which("bst")`, not the
build's own `cmd[0]`, and it prints nothing for up to its 300 s
timeout while the build has not started.

It is also a whole project load the build repeats a second later.
Measured with BuildStream 2.8.1 (a PATH shim timing each `bst`; the
audit's `genproj.py` projects for size):

```text
examples/06 (11 el), cold    key-set bst show 1.16s of a 40.2s snapshot
examples/06 (11 el), warm    key-set bst show 1.18s of a 5.1s snapshot (build 1.07s)
1,201 elements               key-set bst show 5.87s
5,001 elements               key-set bst show 23.68s, silent
```

The build's own Plane 1 log already carries every key: its `Pipeline`
block lists `<state> <64-hex key> <name>` per element. Parsed from
`build.log`, the set is identical to the `bst show` output on both the
cold and the warm capture of `examples/06` (11 of 11, strict build
plan). Non-strict mode is unmeasured.

## Decomposition

Input classes: no global options, `-o` pairs, `--option`, `-c config`,
a `bst` given by path; a timeout; a project `bst show` cannot resolve.
Journey: `bga snapshot`'s pre-build window.

## Required Fix

In `tools/bst_native_build_tracer.py`: the key set is read from the
build's own Plane 1 log (the `Pipeline` block), so it is the keys of
the options the build ran with, and the separate `bst show` goes. Where
the log's block is absent or partial (a build that failed while
loading, non-strict keys not yet resolved), the report says the key
set is unread rather than guessing; if a fallback `bst show` stays, it
uses the build's own `cmd[0]` and `_bst_global_options(cmd)` under
`progress.ticker`.

## Out of Scope

Reusing the post-build graph (`UX-1083`).

## Acceptance Test

`tests/unit/test_the_key_set_reads_the_builds_options.py`, bst-marked:
two builds of one fixture project under different key-affecting
options (a project option that changes an element variable, passed as
`-o`), each key set read from its own Plane 1 log, equals an
option-aware `bst show -o ...` for that variant, and the two sets
differ. Unmarked: a snapshot issues no `bst show` before the build
(fake `bst` on PATH recording argv), and a log with no `Pipeline`
block yields an unread key set, not an empty one. Mutation: read the
keys from an option-less `bst show`, and the two-variant case reds;
restore the pre-build call, and the argv count reds.
