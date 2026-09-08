# UX-695: the refactor stream takes the ledger's top row — renderers first

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the ledger) | **Serves:** the session that opens a round and has no refactor to pick because none is filed | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

§6a says what a refactor is and §6 how a round picks work; neither
says how a refactor gets *chosen*, so the stream has run zero times
against a tree with 84 functions over the threshold. The largest
bodies are renderers — `format_text` 548 lines (CC 135),
`format_compare_text` (CC 63), `build_document` 339 lines (CC 86) —
and renderers are the cheapest refactor in the tree: the golden
snapshot and the schema guards already judge that no behaviour moved.

## Required Fix

One sentence in §6a's refactor row: the candidate is the size ledger's
top row by longest function, and a round with two or more tracks
gives one to it. The first three tracks, filed here as the
acceptance: `format_text` split by section (one function per report
section, the section order a list), `build_document` the same,
`create_parser` split per subcommand. Each track's Outcome pastes the
ledger row before and after, and the golden diff (empty).

## Out of Scope

- `bga/schemas.py` (5,517 lines) — a contract surface; a split moves
  the `--schema` output's provenance and is a `UX-190` question, not
  a refactor.
- `tools/bst_native_build_tracer.py` (6,960 lines) — the tracer is
  hardware-adjacent and its suite runs on `bst`; a split is a capture
  track (`UX-536`'s neighbourhood), priced separately.

## Acceptance Test

After the first track: `tests/quality_reference.json`'s row for
`bga/report/text.py` shows the longest function under 80 lines; the
golden snapshot guard and `bga analyze --json` on every fixture
byte-identical to before; mutation: reorder two sections — the golden
reddens.

## Outcome

**2026-09-08, track 1 (`format_text`):** `format_text` (570 lines, `ruff`
C901/PLR0912/PLR0915) split into one `_render_*_section` function per
report section plus a `_TEXT_REPORT_SECTIONS` list `format_text` walks.
Ledger (`bga/report/text.py`): `{"file_lines": 1696, "longest_function":
570}` → `{"file_lines": 1825, "longest_function": 254}` (`--adopt
--force`: `file_lines` grew from per-function boilerplate).
`longest_function` is now `format_compare_text` (pre-existing 254
lines, untouched) — the Acceptance Test's "under 80" needs a fourth
track for it. Golden fixture text byte-identical before/after; `make
test-touching`: 2287 passed. New guard
`test_text_report_sections_render_in_the_declared_order`
(`test_report_key_findings.py`) renders the golden fixture and checks
each heading (read via `.heading`, never typed) appears in an
independent expected order, not `_TEXT_REPORT_SECTIONS` itself, which a
reorder would otherwise move in lockstep with. Mutation: floors/
attribution swapped in the list -> `sections rendered out of the
declared order: [..., (7451, '_render_floors_section'), (7051,
'_render_attribution_section'), ...]`; reverted from a copy, 19 passed.
`ruff` baseline shrunk 3 stale findings (`--shrink`).
**2026-09-08, `build_document` (bga/report/json.py):** split into 24
`_add_*(data, result, section, by_kind)` functions, one per assembled
block, walked by an ordered tuple `_SECTIONS`; `build_document`'s body
is that loop plus the closing `schemas.stamp`. Ledger row
(`tools/dev_sizes.py`), `bga/report/json.py`: before
`{duplicate_blocks: 0, file_lines: 551, longest_function: 365}`, after
`{duplicate_blocks: 0, file_lines: 640, longest_function: 107}` —
`file_lines` grew (function boilerplate) so `--adopt --force` moved
that one cell; `longest_function` shrank 365→107 and is the cell the
track was filed for. Guards: `tests/unit/test_part_29_reads_the_store_it_has.py`,
`test_what_an_element_pulls_in.py`, `test_why_bga_believes_what_it_believes.py`,
`test_a_committed_analysis_matches_the_analyzer.py`,
`test_the_report_has_chapters.py` — 81 passed, golden diff empty.
Mutation: swapped `_add_findings`/`_add_floors` in `_SECTIONS` →
`test_a_committed_analysis_matches_the_analyzer.py` reddened 2 of 6
(`mixed_task_kinds`, `with_timeline`), naming "the committed order is
not the emitted order"; reverted from a scratchpad copy, re-ran green
(81 passed). `python3 tools/dev_baseline.py --shrink` retired the three
`build_document` rows the split obsoleted (`tests/quality_baseline.json`:
ruff `C901`, `PLR0912`, `PLR0915`, all on `def build_document(...)`);
`--check` and `make lint` both clean.
