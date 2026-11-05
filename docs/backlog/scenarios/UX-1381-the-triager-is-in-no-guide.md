# UX-1381: the `triager` agent is in no guide and not in `CLAUDE.md`'s pipeline

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 39 (2026-11-05) | **Serves:** R8 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1352` added `.claude/agents/triager.md`, the agent that reads a red
log so the session reads a table. `git grep -n -i "triage" -- CLAUDE.md
docs/contributing .claude/skills` finds it in `.claude/skills/decompose/SKILL.md`
alone: the pipeline paragraph in `CLAUDE.md`, the fixing guide and
`rules.md` do not name it, while `CLAUDE.md` says the session "reads
reports, never diffs or logs".

## Required Fix

The pipeline names the `triager` where a red log is read, and a guard
holds that every file under `.claude/agents/` is named in `CLAUDE.md` or
the fixing guide.

## Out of Scope

The agent's own definition.

## Acceptance Test

The guard reddens on a new agent file that no document names.

## Outcome
