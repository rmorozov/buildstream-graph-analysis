# UX-1353: a guard auditor reads every new test against what its task says it guards

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1351 | **Found by:** the Haiku 5.5 workflow review, 2026-10-10 — Ruslan in the project thread, 15:45; the 2026-09-28 reviewer review proposed the class | **Serves:** every round's guards, and the escapes that are guards bound to a proxy | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

12 of the 23 confirmed escapes counted on 2026-09-27 were a guard that
could not fail on the defect it named: a vacuous regex, an echo read
instead of the check, a proxy. The verifier mutates one track; nothing
reads every new guard in a round. The 2026-10-10 probe planted that
class in UX-1341 (the guard ran a hardcoded `--from 1`, not the guide's
spelling) and a Haiku 5.5 verifier found it for $0.017.

## Required Fix

A `.claude/agents/guard-auditor.md` on `model: haiku` at `effort: high`,
read-only. It reads each test file a round adds or changes and the
Acceptance Test of the task it names, and answers per guard: can it
fail on the defect its task names, or does it read a proxy, an echo or
nothing? A guard it suspects goes to one `opus` reader at `medium` with
the auditor's reason; only that reader's confirmed findings go to the
round's fix list, never to new filed rows.

## Out of Scope

Running mutations (the verifier's). A whole-diff PR reviewer.

## Acceptance Test

Run on a round's merged tree with UX-1341's planted guard restored, it
flags that guard and the opus reader confirms it. Its false-flag share
over the round is stated, priced by `UX-1351`'s cost cell.

## Outcome
