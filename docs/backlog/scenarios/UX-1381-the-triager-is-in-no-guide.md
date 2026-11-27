# UX-1381: the `triager` agent is in no guide and not in `CLAUDE.md`'s pipeline

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 39 (2026-11-05) | **Serves:** R8 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_every_agent_file_is_named_in_a_steering_document.py`

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

**Gap measured.** `CLAUDE.md` named `triager` 0 times, and the fixing guide
0 times (it has no agent list). The guard's first draw found a second
unnamed agent: `guard-auditor` (0 and 0), which `UX-1353` added.

**Close measured.** `CLAUDE.md`'s pipeline now says "a red log goes to
the `triager`, which returns a table" and names `guard-auditor` after
`integrator`. The guard globs `.claude/agents/*.md` (9 files) against
the two documents: `1 passed`. `CLAUDE.md` has no size guard that this
touches; `AGENTS.md` already differs from it and is not held equal.

| mutation | reddened | run |
|---|---|---|
| remove the `triager` clause from `CLAUDE.md` | the guard | 1 failed |
| add `.claude/agents/zz-temp.md` no document names | the guard | 1 failed |

**Deviation.** Not a row-listed fix: `guard-auditor` named too, or the
guard would be red on arrival. `make test-touching` is blocked in a
worktree (`UX-1041`); the session runs it.
