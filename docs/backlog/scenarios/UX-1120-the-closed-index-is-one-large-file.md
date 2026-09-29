# UX-1120: the closed index is one 729 KB file the markdown lint reads superlinearly

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the implementing session, which pays the full markdown scan | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

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

## Outcome (round 151, 2026-09-29)

**Premise:** held — one 729 KB file dominated `make lint-docs`.

### The gap, measured

```text
$ make lint-docs        # single process, load 2.4, before the split
real    2m52.831s       (172.8 s)
```

### The close measured

```text
$ make lint-docs        # after: 9 chunks of <=128 rows + history.md, load 4.0
real    1m22.428s       (82.4 s)
$ closed_rows() vs `git show d3ef4bf6:.../closed.md` rows: 1039 == 1039, equal in order
$ python3 tools/dev_close_task.py --check   -> 0 problem(s) over 10 propert(y/ies), 1075 backlog row(s)
```

Row content: relative links in chunks are one directory deeper, so a
chunk holds `](../X)` where the row had `](X)`; `closed_rows()` strips
that one `../`, so the rows read back byte-identical (the guard pins their
sha256). The append adds the prefix.

### Mutation table

| Mutation | Reddened | Count |
|---|---|---|
| `bga_release_notes` binds and reads `closed.md` directly | `test_no_reader_outside_the_tool_opens_a_closed_path` | 1 failed, 6 passed |
| the append's `>= CHUNK_ROWS` check made `>= 10**9` | `test_the_129th_row_opens_a_new_chunk` | 1 failed, 6 passed |
| function-local `p = SCENARIOS / "closed.md"; p.read_text()` in `bga_release_notes._rows` | `test_no_reader_outside_the_tool_opens_a_closed_path` | 1 failed, 8 passed |
| the append drops its `../` link prefix | `test_an_appended_row_links_from_the_chunks_directory` | 1 failed, 8 passed |

### Deviation

- `backlog_files()` is now `(README.md, *closed_files())`; `closed.md` holds no rows.
- `tests/quality_reference.json`: `dev_close_task.py` file_lines 1302 -> 1331 adopted with `--force`.
- `test_the_closed_index_reads_as_one.py` walks every tracked `.py`, so
  `tests/tiers.py` CENSUS needs its row (orchestrator's file); until then
  `test_every_derived_census_guard_is_declared` is red.
- Prose the Decision missed, updated: README.md lines 18 and 902 (prose only), spec line 1895 (inside Part 32), architecture.md:1333, `.pymarkdown.json:50`, `dev_close_task.py` help and comments.
- `closed_rows(scenarios=None)` takes a sandbox directory: the fixtures that run `--scenarios` read their copy.
