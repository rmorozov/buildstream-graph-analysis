# UX-499: "where is it" costs one line, not one file

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-239 (the context map this sits under) | **Serves:** every session's first ten minutes | **Topic:** docs

## Motivation

The context map (fixing guide §6) says which directory owns what and
stops there. Below it, every session re-derives the same lookups —
where a finding id is emitted, which command publishes a key, which
section renders it, which test names a module, which task file
explains a number — and the cheap way (one `grep`) competes with the
expensive way (open `findings.py`, 1,000+ lines) each time. The
researcher agent exists for sweeps; nothing says where the line is
between a lookup and a sweep.

## Required Fix

An `orient` skill: a ten-row table, *I want… | run*, one command per
row returning lines rather than files (`grep -rn` on the finding,
schema, chapter and tier files; `git grep -l` over the task files;
`git log -L` for why a line is the way it is; `sed -n 1,25p` for a
dev tool's docstring, which `UX-497` caps at that). Three rules under
it: read a line range not a file; hand anything over five files or
~400 lines to the researcher; trust the guards' names (`ls tests/unit` piped
to `grep`). Named in `CLAUDE.md`'s skills line as the first step.

## Out of Scope

- A generated symbol index (`tags`) — the greps are milliseconds on
  this tree and an index is one more artifact to keep true.
- Folding §6 into the skill — the map is the guide's, guarded by
  `test_the_context_map_is_the_tree.py`; the skill points below it.

## Acceptance Test

Every command in the table runs on this tree and returns at least one
line for a real id (`bga.findings` id, a schema key, a module name);
`test_the_agent_configuration_holds.py` green.

## Outcome (round 74, 2026-09-01) — 🟢 Done

### The gap, measured

```text
fixing guide §6 (the context map)   directories and files, no lookups
bga/findings.py                     the file a "where is finding X" opens today
```

### After

`.claude/skills/orient/SKILL.md`, 44 lines: ten lookups, each one
command; three rules on the line between a lookup and a sweep. Each
command was run on this tree against a real id before the table was
written. `CLAUDE.md` lists it first in the skills order.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M1 | description loses its "Use when" trigger | `test_each_description_says_when_to_use_it` |

### Deviation from the Required Fix

None.
