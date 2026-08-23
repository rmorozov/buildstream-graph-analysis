# UX-240: a session has no cheap entry point

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-238 (the tiers a skill would name), UX-239 (the map and the streams it would carry) | **Serves:** the maintainers, and every agent session | **Topic:** docs

## Motivation

The user's proposal: skill files, so an agent's interaction with the
codebase is more efficient.

The cost this is about is measurable. Every session in this repository
begins by re-reading the same things — the fixing guide, the style
guide, the backlog index, the Makefile, the test layout — before it can
do anything, and then re-derives the same procedures: how to falsify a
guard, how to regenerate the golden snapshot, which budget guards exist
and what their numbers mean. Round 28 rediscovered the golden-snapshot
recipe from a docstring, and rediscovered the falsification discipline
by getting it wrong four times.

A repository skill is the right shape for a *procedure that is followed
identically every time and is currently prose in a guide*. It is the
wrong shape for judgment, and this repository is mostly judgment — so
the scope is deliberately narrow.

## Required Fix

Skills only where the procedure is mechanical and repeated:

1. **verify** — the Definition of Done as a runnable checklist: the
   acceptance command, the right test tier, the full suite, lint, the
   status-row-and-file pair, the Outcome section.
2. **falsify** — the mutation discipline: apply, confirm the edit
   landed, run the one guard, confirm red, revert, confirm green. With
   the two failure modes this repository keeps hitting written into it:
   a mutation that does not discriminate, and a revert that resets past
   your own work.
3. **measure** — the recipes that get re-derived: the golden snapshot,
   the 1,202-element synthetic, the export size, the durations run.

Each skill points at the guide that owns the rule rather than restating
it, so there is one source and the skill is the entry point.

## Out of Scope

- A skill for "how to fix a task". That is judgment, and a skill that
  pretended otherwise would be a worse fixing guide.
- Anything that duplicates a guide's *content* rather than pointing at
  it. Two copies of one rule is the defect this repository has fixed
  more times than any other.

## Acceptance Test

Each skill's commands run as written against this tree, with output
pasted; a guard asserts every command a skill tells you to type exists
(the same check `test_docs_links_and_commands.py` already makes for the
guides); the skills contain no rule that is not also in a guide, and a
guard names where each points.
