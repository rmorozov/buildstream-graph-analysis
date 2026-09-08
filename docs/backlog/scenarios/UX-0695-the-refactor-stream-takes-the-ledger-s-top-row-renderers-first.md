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
