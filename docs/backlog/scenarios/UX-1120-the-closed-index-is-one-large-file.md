# UX-1120: the closed index is one 729 KB file the markdown lint reads superlinearly

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the implementing session, which pays the full markdown scan | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_the_closed_index_reads_as_one.py, absent from tests/

## Motivation

`docs/backlog/scenarios/closed.md` is 729 KB and append-only. PyMarkdown
spends **96 s** on it alone of the 154 s full `make lint-docs` on a 4-core
container; the other 1,302 files share the rest. It is read by 17 test files
and two tools (`dev_close_task.py` 11 references, `bga_release_notes.py` 2),
so the split is a reader change, not a file move.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     split by append position: docs/backlog/scenarios/closed/NNNN.md, 128 rows each in close order (1,039 rows, 9 files); closed/history.md takes the narrative sections; closed.md shrinks to a header linking the directory once. dev_close_task.py gains `closed_files()`/`closed_rows()`; the append goes into the last chunk and opens the next when full; bga_release_notes and every test read through closed_rows(); `.gitattributes` `closed/*.md merge=union`
Rejected:  quarters (all 1,039 rows fall in one quarter, no saving); ID ranges (264 ID descents in close order; release-note markers are close-order counts)
Files:     closed.md; closed/*.md; .gitattributes; tools/dev_close_task.py; tools/bga_release_notes.py; the 17 tests that read closed.md; .claude/agents/{implementer,closer}.md; .claude/skills/{decompose,orient,verify}/SKILL.md; docs/contributing/{fixing-guide,release-guide,style-guide}.md; tests/unit/test_the_closed_index_reads_as_one.py
Guard:     closed_rows() equals the pre-split closed.md's rows in order; a 129th row opens a new chunk; no tracked .py outside dev_close_task.py opens a `closed.md` or `closed/` path
Mutation:  bga_release_notes reads closed.md directly - reddens; the append skips the size check - reddens
Class:     optimization - pymarkdown on one file: 130 rows 1.5 s, 260 5.1 s, 520 29.8 s; nine 128-row chunks ~14 s against 96 s
Split:     own track, parallel with the B track; merges before 1118
```

## Required Fix

`closed.md` becomes one file per quarter under
`docs/backlog/scenarios/closed/` plus a short `closed.md` that links them;
every reader goes through one function in `dev_close_task.py` that yields
the rows of all of them.

## Out of Scope

Changing the row format; lint scoping (`UX-1112`).

## Acceptance Test

`tests/unit/test_the_closed_index_reads_as_one.py`: the union of the
quarter files' rows equals the pre-split rows, and every one of the 19
readers resolves through the one function (grep for a direct `closed.md`
open outside it). Mutation: a reader opening `closed.md` directly reddens.
The Outcome carries `make lint-docs`' wall before and after.
