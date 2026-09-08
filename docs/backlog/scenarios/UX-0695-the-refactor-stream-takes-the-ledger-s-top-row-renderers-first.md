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
report section plus a `_TEXT_REPORT_SECTIONS` list `format_text` walks;
`Structural Analysis` and `CPU Utilisation` further split by sub-block
to clear 80 lines. Ledger (`tools/dev_sizes.py --check`/`--adopt
--force`, `bga/report/text.py`): `{"file_lines": 1696, "longest_function":
570}` → `{"file_lines": 1825, "longest_function": 254}` — `file_lines`
grew from the per-function `lines = []`/`return lines` boilerplate,
so `--force` was needed; `longest_function` is `format_compare_text`
now (pre-existing 254 lines, untouched — out of scope for this track,
still over 80). `bga analyze --diagnostics` on
`tests/fixtures/golden/mixed_task_kinds`: byte-identical before/after
(diffed directly; no test asserts full-text order). `make
test-touching`: 2287 passed, 4 skipped. Mutation: swapping
`_render_floors_section`/`_render_attribution_section` in the list
moved "Certified Floors:" after "Attribution Breakdown:" in the
rendered text (diff below), reverted from a pre-mutation copy.
`ruff` baseline shrunk 3 stale entries (`dev_baseline.py --shrink`)
for `format_text`'s retired C901/PLR0912/PLR0915 findings.
