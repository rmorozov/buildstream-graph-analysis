# UX-566: two "recommended" Parts describe a tool that was never built that way

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the reader who opens the spec's tail for the report or the tree | **Topic:** docs

## Motivation

```text
Part 38 (specification.md:2349-2416)   11 upper-case report chapters — RECOMMENDATIONS, REBUILD LEVERAGE, TRACE QUALITY…
golden text report                      Key Findings / Confidence / Certified Floors / Attribution Breakdown / CPU Utilisation /
                                        Advanced Diagnostics / Structural Analysis / Plane 2 / Next
Part 39 (specification.md:2427-2489)   32 modules — reachability.py, depth.py, dominators.py, slack.py, ready_queue.py, retry.py, timeline.py…
tree                                    12 modules in those packages; bga/structural/ (6 files) and validation/provenance.py unnamed
  round 83, counted off the tree:       Part 39 names 40, not 32; 13 of them exist, not 12; 20 real
                                        modules live in those packages and 7 are unnamed by it
Part 37                                 `--cold` requires `--history-dir`, which the spec never names
specification.md:1714                   "additionalProperties is true in all three" — there are eight printable contracts
```

The spec's header disclaims Parts 38-40 as recommended, and the
house rule keeps the body unedited; nothing tells a reader which
Parts are the design and which are the archaeology.

## Required Fix

A Part 32 registry note listing the Parts that are advisory and
superseded by the tree (37's flag, 38, 39, 40, the "all three"
sentence), each with the document that is current — so the spec
carries its own map of what to trust. No body edit.

## Out of Scope

- Rewriting the Parts — the body is ground truth and stays unedited (§3.12); the registry note is the whole change.

## Acceptance Test

The note exists and names each Part; `test_a_counted_figure_is_derived`
covers the "all three" sentence.

## Outcome (round 83, 2026-09-03) — 🟢 Done

Spec Part **32.7.3**: a four-row table naming 37.1, 38, 39 and 40 as
advisory, each with the document that is current. No body edit; the
one sentence changed is inside Part 32.

**Two filed figures were low.** Counted off the tree:

```text
$ python3 - <<'PY'   # parse Part 39's fenced tree, stat each name
Part 39 names 40 modules in 11 packages
present in the tree: 13 ['attribution/blame_chain.py', 'floors/capacity.py',
  'floors/cold.py', 'floors/observed.py', 'floors/serialization.py',
  'graph/edg.py', 'normalize/timestamps.py', 'occupancy/sweep.py',
  'replay/scheduler.py', 'report/json.py', 'report/text.py',
  'validation/determinism.py', 'validation/invariants.py']
absent: 27
real non-__init__ modules in those packages: 20
real but unnamed by Part 39: 7 ['diagnostics/analyzer.py', 'ingest/loader.py',
  'ingest/models.py', 'report/_shared.py', 'report/ci_comment.py',
  'utilisation/detection.py', 'validation/provenance.py']
packages Part 39 never names: ['structural']
```

Forty named, not 32; thirteen present, not 12. Both are now in the
note's row and both are derived by the guard, per §3.12. Motivation
corrected in place.

The other premises held. Part 38 lists eleven upper-case chapters
against nine the tool prints (`Key Findings`, `Confidence`, `Certified
Floors`, `Attribution Breakdown`, `Advanced Diagnostics`, `Structural
Analysis`, `Plane 2`, `Next`, plus `CPU Utilisation` conditionally);
`git grep -n "history-dir" docs/spec/specification.md` returns nothing
while `bga floors` takes it; and `bga/schemas.py` defines eight
schemas, all `additionalProperties: true`, against the sentence's
"three".

| mutation | applied to | reddened | run |
|---|---|---|---|
| "in all eight schemas" → "in all three" | `specification.md` | `test_the_versioning_rule_counts_the_schemas_it_describes` | 1 failed, 13 deselected |
| a ninth well-formed schema in `_SCHEMAS` | `bga/schemas.py` | same guard, on the count: `'…all nine schemas…'` | 1 failed, 13 deselected |
| Part 40's row deleted | `specification.md` | `test_the_four_parts_each_have_a_row` | 1 failed, 5 passed |
| Part 40's "what is current" cell → `—` | `specification.md` | `test_every_row_names_a_current_document` | 1 failed, 5 passed |
| `bga/graph/slack.py` created — a module Part 39 names | tree | `test_the_named_and_present_counts…`: "should say 'fourteen exist'" | 1 failed, 5 passed |
| `bga/newpkg/` created | tree | `test_the_package_the_part_never_names…`: `['newpkg', 'structural'] == ['structural']` | 1 failed, 5 passed |
| `"CPU Utilisation:"` → `"REBUILD LEVERAGE:"` | `bga/report/text.py` | `test_no_report_chapter_of_part_38_is_a_heading_the_tool_prints` | 1 failed, 5 passed |
| `--history-dir` → `--history-directory` | `bga/cli.py` | `test_the_history_dir_flag_the_spec_never_names_is_named_here` | 1 failed, 5 passed |

All reverted; `20 passed in 0.39s`. The first mutation of the schema
count read green on the wrong assertion (the new schema set no
`additionalProperties`, so it failed the completeness clause rather
than the count) — rejected and rewritten, per `falsify`'s first
failure mode.

**Acceptance Test** — "the note exists and names each Part;
`test_a_counted_figure_is_derived` covers the 'all three' sentence":

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_the_spec_says_which_parts_are_advisory.py tests/unit/test_a_counted_figure_is_derived.py -v
...::TestTheNoteNamesEveryAdvisoryPart::test_the_four_parts_each_have_a_row PASSED [  5%]
...::TestTheNoteNamesEveryAdvisoryPart::test_every_row_names_a_current_document PASSED [ 10%]
...::TestTheNoteNamesEveryAdvisoryPart::test_the_history_dir_flag_the_spec_never_names_is_named_here PASSED [ 15%]
...::TestPart39sFiguresAreCountedOffTheTree::test_the_named_and_present_counts_are_the_ones_the_row_states PASSED [ 20%]
...::TestPart39sFiguresAreCountedOffTheTree::test_the_package_the_part_never_names_is_the_one_the_row_names PASSED [ 25%]
...::TestPart38sChaptersAreNotIdentifiers::test_no_report_chapter_of_part_38_is_a_heading_the_tool_prints PASSED [ 30%]
...::TestTheSpecCountsItsOwnTable::test_the_versioning_rule_counts_the_schemas_it_describes PASSED [ 70%]
============================== 20 passed in 0.39s ==============================

$ make test-touching
20 file(s) selected · 430 passed, 4 skipped in 9.90s
```

**Deviation and one thing found, not fixed:** `docs/design/architecture.md:41`
lists `bga floors RUN [--cold] [--allow-partial-cold]` and omits
`--history-dir` too — the same gap, one document over. Out of this
item's scope (32.7.3 points at `bga floors --help`, which is right);
it wants a row.
