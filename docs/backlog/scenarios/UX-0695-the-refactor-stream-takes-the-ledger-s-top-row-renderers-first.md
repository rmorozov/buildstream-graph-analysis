# UX-695: the refactor stream takes the ledger's top row — renderers first

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the ledger) | **Serves:** the session that opens a round and has no refactor to pick because none is filed | **Topic:** docs

## Motivation

§6a says what a refactor is and §6 how a round picks work; neither
says how a refactor gets *chosen*, so the stream has run zero times
against a tree with 84 functions over the threshold. The largest
bodies are renderers — `format_text` 548 lines (CC 135),
`format_compare_text` (CC 63), `build_document` 339 lines (CC 86) —
and renderers are the cheapest refactor in the tree: the golden
snapshot and the schema guards already judge that no behaviour moved.

## Required Fix

One sentence in §6a's refactor row: the candidate is the ledger's
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
