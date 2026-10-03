# UX-1334: wrapper-script capture, `cache-logs` across junctions, doctor's junction check and help's start block are in no guide

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 37, checklist item 4 (2026-10-03) | **Serves:** R1, R2 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** test_the_cli_guide_names_the_junction_round_changes.py

## Motivation

Round 170's twelve rows (`UX-1320`..`UX-1331`): eight name a guide, four do not.

```text
$ for u in 1322 1325 1328 1329 1331; do echo "$u: $(git grep -l "UX-$u" -- docs/guides docs/design/architecture.md README.md docs/README.md docs/contributing | wc -l)"; done
1322: 0   1325: 0   1328: 0   1329: 0   1331: 0
$ git grep -n -i "junction" -- docs/guides/cli.md | grep -ci "cache-logs\|doctor"      0
$ git grep -n -i "shim" -- docs/guides/cli.md | grep -ci "bst"                          0
```

- `UX-1322`: `bga snapshot -- ./build.sh` puts a `bst` shim on `PATH` and refuses a command that ran no `bst build`; `cli.md`'s snapshot and capture sections say a command starts with `bst`.
- `UX-1325`: `bga cache-logs PROJECT_DIR` reads every junction's log tree; `cli.md`'s `## bga cache-logs` does not.
- `UX-1328`, `UX-1331`: doctor's `sleep-policy` container reading and the junction-aware stage check.
- `UX-1329`: `bga --help` opens with a three-line *Start here*; `docs/README.md` and the README quote `bga --help`'s command list.

## Required Fix

One sentence each in the section that owns the command, citing the row; derive nothing new.

## Out of Scope

Rewriting `cli.md`'s structure (`UX-1290`).

## Acceptance Test

`git grep -l "UX-1322\|UX-1325\|UX-1328\|UX-1329" -- docs/guides` names `cli.md`; each sentence's command is run as written.

## Outcome

**Gap measured.** `git grep -l "UX-1322\|UX-1325\|UX-1328\|UX-1329" -- docs/guides` returned nothing; `git grep -n -i "shim" -- docs/guides/cli.md | grep -ci bst` was 0.

**Close measured.** Same grep names `docs/guides/cli.md`; `UX-1331` is in its doctor section too. Four sentences: snapshot (wrapper script, `bst` shim, refusal), doctor (container `sleep-policy`, junction-aware stage check, "read the error above"), `cache-logs` (junction trees), and the *Start here* block beside the alias paragraph. Run as written, in a project with `./b.sh` that runs no `bst`: `bga snapshot -- ./b.sh` printed "exited 0 without running `bst build`" and "Nothing was kept"; `bga --help` opened with the three-line *Start here*.

`python3 -m pytest -n 0 tests/unit/test_the_cli_guide_names_the_junction_round_changes.py` : 4 passed. It reads the id in the section that owns the command.

| mutation | result |
|---|---|
| cli.md: cache-logs sentence's `UX-1325` -> `UX-13x5` | 1 failed, 3 passed |
| cli.md: doctor sentence drops `UX-1331` | 1 failed, 3 passed |
| cli.md: `UX-1322` -> `UX-1399` in the snapshot sentence, and `UX-1329` -> `UX-1399` | 2 failed, 2 passed |

**Deviation.** The guard checks the id sits in the right section, not that the sentence is true; the sentences were run as written once, above.
