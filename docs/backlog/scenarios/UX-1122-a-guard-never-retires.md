# UX-1122: a guard never retires, so every gate is paid on every pull request forever

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** Ruslan, who decides what the per-PR path costs | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_the_retro_prices_its_guards.py, absent from tests/

## Motivation

Each process incident has been closed by adding a guard, and no rule moves
one off the per-PR path. #299's `**Guard:**` lines now join tests to tasks:
1,060 tasks, 395 `none`, 457 (43%) `inferred r149`; **215 of 686 test files
are named by no task**, and `test_docs_links_and_commands.py` answers for
35. `tests/ci_reference.json` holds each file's seconds (1,829 CPU-s).

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     new `tools/dev_guard_prices.py`, pure `proposals(prices, guards, last_catch, current_round, n=10)`; `main` reads `dev_records.load("tests/ci_reference.json")["files"]`, the Guard map through `dev_area_pages.guard_files` (an `inferred r149` line reads "confirm first"), and last catch per file (None when unrecorded). Table: file, seconds, owner task(s), last catch or "unrecorded", proposal ("scheduled lane" | "needs owner" | "confirm inferred"), by seconds. None is never quiet. The retro skill runs it; N=10 lives in the skill
Rejected:  flake_ledger.json (timing drift, not reds); junit artifacts / gh (403, no gh here); round documents (3 test files named in rounds 141-150); folding into dev_retro.py (it prices bookkeeping)
Files:     tools/dev_guard_prices.py, .claude/skills/retro/SKILL.md, tests/unit/test_the_retro_prices_its_guards.py
Guard:     three in-memory files (named, caught last round; named, caught 12 rounds back; unnamed): the proposal lists the 2nd and 3rd only (small)
Mutation:  drop the last-catch filter - the 1st appears, reddens
Class:     optimization - per-PR 1,829 CPU-s; 215 of 686 files unnamed
Split:     T1 here; T2 (a red ledger CI writes from PR junit on push to main) is a new row after the ci.yml track
```

## Required Fix

The `retro` skill gains a step: join `ci_reference.json` to the Guard map
and to each file's last red on `main` or a PR (the flake ledger and the
junit artifacts), and propose moving to a scheduled lane any file whose last
true catch is older than N rounds (N set in the skill, starting at 10), and
any unnamed file for a Guard owner. An `inferred` line is confirmed before
it justifies a move. The retro proposes; the architect shapes; nothing moves
without a row.

## Out of Scope

Deleting any guard; building the scheduled lane (`UX-1121` builds its first use).

## Acceptance Test

`tests/unit/test_the_retro_prices_its_guards.py` runs the join over a
fixture of three files (named and recently red; named and quiet past N;
unnamed) and asserts the proposal lists the second and third only.
Mutation: drop the last-red filter; the first file appears and it
reddens.

## Outcome

**The gap measured:** `python3 tools/dev_guard_prices.py` before: no such
tool; 686 files in `tests/ci_reference.json`, 1852 CPU-s.

**The close measured:** `python3 tools/dev_guard_prices.py` on this tree:
"543 of 686 files proposed; 1193 of 1852 CPU-s" = 215 needs owner, 328
confirm inferred, 0 scheduled lane (no catch record, so unrecorded is no
evidence and never a move). `pytest tests/unit/test_the_retro_prices_its_guards.py`:
4 passed.

| Mutation | Reddened | Printed |
|---|---|---|
| drop the last-catch filter (`elif old:` -> `elif True:`) | the three-file test and the unrecorded test | 2 failed, 2 passed |
| unrecorded counts as old (`old = last is None or ...`) | `test_a_named_unrecorded_file_is_never_a_scheduled_lane` | 1 failed, 3 passed |

Deviation: also edited `docs/contributing/fixing-guide.md` (a §6 tool
row, no id cited while open); the last-catch source is a `--catches` JSON
`{test path: round}`, since no record holds one yet (T2's ledger).
