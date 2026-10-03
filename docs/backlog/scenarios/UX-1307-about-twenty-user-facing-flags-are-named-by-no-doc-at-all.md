# UX-1307: about twenty user-facing flags are named by no doc at all

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R4, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_every_bga_flag_is_named_in_the_cli_reference.py`

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

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held — every flag on the audit's list was absent from its
command's cli.md section; `--build-type`/`--variant` were only in the
environment table.

### The gap, measured

```text
$ python3 scratchpad/inv.py   # (command, --flag) pairs cli.md names nowhere, native parser + AST inventory
analyze ['--explain'] ... extract [9 flags] ... run-context [6] ... view [4] ... baseline [6] ...
50
```

50 (command, flag) pairs unnamed; the audit's list was 22 of them. The
rest (`--explain` on six commands, `--band-k`, `--exclude`, `gen-synthetic`'s
six, ...) were pre-existing.

### After

```text
$ python3 scratchpad/inv.py
0
$ pytest tests/unit/test_every_bga_flag_is_named_in_the_cli_reference.py tests/unit/test_the_documented_invocations_parse.py
36 passed
```

50 pairs before, 0 after. All 22 audited pairs sit in their command's own
`cli.md` section; `--compare` is also in viewer.md's band bullet and
`--remote`/`--workdir` in ci-comment.md. The 19 older gaps (`--explain`,
`--band-k`, `--count`, `--exclude`, `--repo`, `--consolidated`,
`--individual`, six `gen-synthetic` flags, `--from`/`--to`, `--prune`,
`--no-browser`, `--perfetto`, `--element`) are documented too; no allowlist.

### Mutations verified red and reverted (11)

| # | mutation | reddened |
|---|---|---|
| A1 | drop the `--count-only` bullet | 2 (named, pinned) |
| A2 | rename the `baseline --workdir` bullet | 2 |
| A3 | drop `extract --build-type` bullet (env table still names it) | 1 (pinned section clause) |
| A4 | inventory without the shared `_run_context_common` flags | 4 |
| A5 | drop `gen-synthetic --layers` bullet | 1 |
| A6 | drop the `--explain` heading and paragraph | 1 |
| A7 | revert the `_alias_flags` helper-module fix in the parse test | 4 |
| A8 | move `baseline --exclude` into `whatif`'s section | 2 |
| A9 | drop `graph` from the `--explain` paragraph | 1 |
| A10 | drop `cache-logs --all` (a stub section's flag) | 1 |
| A11 | drop `extract --cpu-budget` bullet | 1 |

The guard binds the 22 audited pairs, the 19 formerly held, and every flag of
a stub section (one saying "every flag is in `--help`") to the command's own
section; other native commands' older flags are held to "named somewhere in
cli.md" only (their prose is spread over several sections).

### Deviation from the Required Fix

None beyond one: `--build-type`/`--variant` are added by a helper the alias
AST scan could not see, so `_alias_flags` in the parse test now reads
`tools/_run_context_common.py` for any module calling it. `snapshot --prune`'s
argparse help also said it needed `--keep`/`--older-than`; `--max-store` alone
is accepted, so help and doc now say so.
