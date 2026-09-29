# UX-1122: a guard never retires, so every gate is paid on every pull request forever

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** Ruslan, who decides what the per-PR path costs | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — named test_the_retro_prices_its_guards.py, absent from tests/

## Motivation

Each process incident has been closed by adding a guard, and no rule moves
one off the per-PR path. #299's `**Guard:**` lines now join tests to tasks:
1,060 tasks, 395 `none`, 457 (43%) `inferred r149`; **215 of 686 test files
are named by no task**, and `test_docs_links_and_commands.py` answers for
35. `tests/ci_reference.json` holds each file's seconds (1,829 CPU-s).

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
