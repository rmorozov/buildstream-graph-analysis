# UX-1307: about twenty user-facing flags are named by no doc at all

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R4, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Flags a user can pass that no guide, and in most cases not cli.md,
names: `extract`/`run-context`'s `--build-type`, `--variant`,
`--cache-usage`, `--memory-budget-mb`, `--estimated-job-memory-mb`,
`--native-max-jobs`, `--trace-epsilon-us`, `--start-time`,
`--interrupted`, `--strict`, `--bst-bin`; `bga view --compare` and
`--port`; `bga baseline --remote` and `--workdir`; `rebuild-set --cut`
and `--count-only`; `capture run --host-samples`.

```text
$ grep -rn -- '--workdir' docs | wc -l
0
$ grep -rn -- '--count-only' docs | wc -l
0
```

Method and the full list: the audit's `flagscan.txt` (126 flags over
41 `--help` outputs, grepped against `docs/guides`, README, `docs/cases`).

## Required Fix

Each flag gets a line in its command's cli.md section, and the
user-facing ones (`view --compare`, `baseline --remote`) a sentence in
the task guide that needs them.

## Out of Scope

The translated flags (`UX-1301`).

## Acceptance Test

A guard walks every `bga` subcommand's argparse and reddens on a flag
cli.md does not name. Reading taken in this container.

## Outcome
