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
timeout while the build has not started. Inferred from the code: this
container has no `bst` to run it.

## Decomposition

Input classes: no global options, `-o` pairs, `--option`, `-c config`,
a `bst` given by path; a timeout; a project `bst show` cannot resolve.
Journey: `bga snapshot`'s pre-build window.

## Required Fix

In `tools/bst_native_build_tracer.py`: the key-set call uses the
build's own `cmd[0]` and `_bst_global_options(cmd)`, and runs under
`progress.ticker` like `extract_graph`'s `bst show`.

## Out of Scope

Folding it into the post-build `bst show` (non-strict builds can change
keys during the build; `UX-1080` decides).

## Acceptance Test

`tests/unit/test_the_key_set_reads_the_builds_options.py`: with a fake
`bst` on PATH recording its argv, `bst -o arch aarch64 build all.bst`
issues `show` with `-o arch aarch64` and the build's executable.
Mutation: drop the options, and it reds.
