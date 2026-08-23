# UX-231: every direction names its reader

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** the role model (`../../design/roles.md`) | **Serves:** all roles, by making their coverage visible

## Motivation

Round 27 wrote the role model: eight roles, their interests, the
contradictions between them, and the finding that twenty-six rounds
of audits served four of them thoroughly and four almost not at all
— invisibly, because nothing required a direction or a filing to say
whose problem it solves. The gap analysis only stays true if the
tracing becomes routine.

## Required Fix

1. Directions 1-7 gain a `Serves:` line retroactively (8 and 9 were
   born with one); every future direction carries one at birth.
2. New backlog filings carry `Serves:` in their header line, with
   role ids from the role model (UX-227..234 already do; the style
   guide documents the convention).
3. The two guides state their role in their opening line
   (`real-project.md` is R1's journey; `ci-comment.md` is R4's).
4. The fixing guide's checklist gains the line: *does this change
   which roles are served, or how well? Then `roles.md`'s table
   changes in the same commit.*
5. A guard: every `## Direction N` section in `directions.md`
   contains a `Serves:` line; every task file from UX-227 up carries
   one. (Older filings are history; retro-tagging them is explicitly
   not required.)

## Out of Scope

- Retro-tagging UX-1..226 (the archaeology would be guesswork; the
  round history already tells that story).
- Any reorganisation of the backlog itself (`UX-232`).

## Acceptance Test

The guard reddens on a direction section without `Serves:` and on a
new task file without one (mutation: strip the line from Direction 8
→ red); both guides name their role; the fixing-guide checklist
carries the roles line; `grep -l "Serves:.*R6"` over the backlog
returns the R6 filings — the query the role model promised works.
