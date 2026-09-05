# UX-696: the register's unguarded rows — no round in code, a dated count, the commit body

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-497 (the register) | **Serves:** the reader who opens a module a year on and meets its history instead of its reason | **Topic:** guards | **Shape:** judgement

## Motivation

`test_the_register_is_terse.py` holds the docstring and Outcome rows.
The other two — a comment is one line of why, a commit body is eight
lines — are stated and unread. Round 93's census of what actually
drifts in comments: backticked identifiers, 1,585 checked, **0**
unresolved; round numbers in `bga/` and `tools/`, **31** lines
(`grep -rn "round [0-9]" bga tools --include=*.py`); counts and
promises — `pyproject.toml`'s "~30-module … widen in a later task",
104 modules and no task later. The stale shape is history and
numbers, not names.

## Required Fix

Three rows of the same guard. **No round in code**: the 31 lines are
grandfathered by path and may only shrink, like the docstring row.
**A count in a comment is dated or derived**: a comment containing a
bare count (`~N`, `N modules`, `N files`) must also carry a date or a
`UX-` id — the census lists today's; each is dated or its number
deleted. **The commit body**: CI reads the pull request's commits and
fails one whose body exceeds eight lines outside the footer. The
identifier check is *not* added — it found nothing, and a guard that
finds nothing is a proxy.

## Out of Scope

- `UX-NNN` ids in comments (2,948 across 81 files) — a pointer to the
  record is the register's sanctioned form of why.
- Comment density (`bga/report/json.py` 0.64 comment-to-code) — a
  ratio with no defect behind it; not a rule.

## Acceptance Test

Mutation: write `# since round 93` in `bga/blast.py` — red; write
`# about 40 modules` without a date — red; a commit body of nine
lines on a branch — the CI step reddens, and the pinned footer lines
do not count.
