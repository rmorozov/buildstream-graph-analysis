# UX-1334: wrapper-script capture, `cache-logs` across junctions, doctor's junction check and help's start block are in no guide

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 37, checklist item 4 (2026-10-03) | **Serves:** R1, R2 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

Not yet worked.
