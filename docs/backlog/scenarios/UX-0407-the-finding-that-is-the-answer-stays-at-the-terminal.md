# UX-407: the finding that *is* the answer stays at the terminal

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-389 (the same disease, plane2 blocks), UX-401 (the census that would have caught it) | **Serves:** R1 and R8 — the reader deciding what to restructure | **Topic:** analysis

## Motivation

Round 64 walked example 06 against its `optimized/` answer key. The
single output that names the *entire* key in one paragraph is
correlate's restructuring synthesis (`bga/correlate.py:1856`):

```text
Restructuring opportunity: 18 declared build edge(s) among 7
element(s) were measured never-read, and they chain those elements
along the critical path: ... Replaying this run with those edges
removed ... finishes in 8.0s against 20.9s: 12.9s
```

That paragraph appears in no `analyze.json` key, no page section,
and not in the default snapshot output — a grep of the round's
export finds zero hits for "Replaying this run" or "edges removed".
The page carries the per-element crumbs (`unused_dependencies`,
"opened no file staged by 3 declared build dependencies…"), so a
reader must open seven element folds and re-do the aggregation the
tool already did, projection and all. `UX-82` asked for exactly this
finding years of rounds ago; it exists — it just never leaves the
terminal. This is the walk's sharpest instance of "the tool had the
data and made the reader do the reasoning."

## Required Fix

- Publish the restructuring synthesis as a keyed finding in the
  correlate contract (addition — no version bump under `UX-190`),
  with its edge list, the replayed wall-clock pair and the saving.
- Render it as a section — it is table-shaped (edges) under one
  sentence (the projection), and by rank it belongs beside the
  headline's cards: on this walk it is the largest single saving the
  analysis computed (12.9 s against a 6.0 s #1 card).
- The default snapshot print keeps pointing at `bga correlate` (it
  does today); the page stops being the one surface without the
  answer.

## Out of Scope

- Trusting the projection as a promise — the existing "evidence,
  not a verdict" caveat travels with the finding wherever it goes.
- The other terminal-only blocks — `UX-389` owns the plane2 block
  triage; this is the correlate document's one synthesis.

## Acceptance Test

- On the round-64 capture: the export contains the synthesis, its
  section renders with the edge table, and the terminal and page
  print the same 8.0 s / 20.9 s / 12.9 s triple.
- Falsification: drop the key from the correlate emitter — the
  contract guard and the section's presence guard both go RED.

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, measured

The synthesis on the surface it already had:

```console
$ PYTHONPATH=. python3 -m bga.cli correlate tests/fixtures/macro_micro/run \
    | grep -A 3 "Restructuring opportunity"
Restructuring opportunity: 18 declared build edge(s) among 8 element(s)
were measured never-read, and they chain those elements along the
critical path:
    app.bst -> core.bst -> lib-a.bst -> ... -> lib-f.bst
    Replaying this run with those edges removed - same durations, same
    capacity - finishes in 19.1s against 43.2s: 24.1s
```

And on the surface the page reads:

```console
$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/macro_micro/run \
    --format json | python3 -c \
    'import json,sys; print("restructuring" in json.load(sys.stdin))'
False
```

### After

```console
$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/macro_micro/run \
    --format json | python3 -c \
    'import json,sys; print(json.load(sys.stdin)["restructuring"][0]["projection"])'
{'replayed_baseline_us': 43200000, 'projected_us': 19050000,
 'saving_us': 24150000, 'capacities': {'PROCESS': 4, 'DOWNLOAD': 10,
 'UPLOAD': 4}}
```

The section, driven in Chrome on the exported page:

```text
Which dependency edges are never read?   restructuring   [act]
  Severity   Unread edges              Replayed without them
  high       Edges · 2 levels, 18 rows  Projection · 2 levels, 4 rows
             Staged by    Never read by  replayed_baseline_us  43.2 s
             core.bst     app.bst        projected_us          19.1 s
             core.bst     lib-a.bst      saving_us             24.1 s
             ... 18 rows                 capacities  PROCESS 4 ...
```

`43.2 s / 19.1 s / 24.1 s` on the page against `19.1s against 43.2s:
24.1s` at the terminal - the acceptance test's triple, on the committed
fixture rather than the round-64 capture (which is not in the tree; its
own numbers are 8.0 / 20.9 / 12.9).

### One declaration, and the two renderings that had to change

The finding is published under one `_RESTRUCTURING_HINT`, used by
`analyze/v4` and `correlate/v2`. `bga/analyzer.py` now holds the
normalized tasks and the run context on the result, because the join in
`bga/report/json.py` cannot compute the *replay* without them and the
finding would otherwise arrive with `projection: null` - the defect
wearing the fix's clothes.

Two older renderings kept the page from saying what the terminal says,
and neither had a value that showed them until a **record** - a schema
node whose members are named in `properties`, each with its own unit -
was nested in a table cell:

- `mapTable` declared one quantity for the whole `value` column,
  falling back to `count`. Right for `{element: duration_us}`; on a
  record it printed `43200000` where the member is declared
  `duration_us`, and drew a density strip across three numbers that
  are not one measure.
- `buildTable` resolved the *schema node* from the row's key (`UX-290`)
  and kept reading the **column's** `spec.quantity` when rendering.

And one state key: `UX-292` keyed a nested table by its row, which is
right for a map table's single `value` column and wrong for a record
row with three structural cells - all three of this section's folds
shared one key until the path gained the column.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it. Applied
against the committed tree - the first attempt used `git checkout` to
revert against an *uncommitted* one and destroyed three files' worth of
work, which is the reason the fixing guide says "committed".

| # | mutation | reddened |
|---|---|---|
| A1 | drop the key from the analyze emitter (the filing's own falsification) | 7 of 13, incl. `test_analyze_carries_the_synthesis` and `test_the_section_is_on_the_page` |
| A2 | call the join without `tasks`/`run_context` again | 7 of 13, incl. `test_it_carries_the_replay_rather_than_a_null` |
| A3 | drop `bga:columns` from the edge list | 8 of 13, incl. `test_the_edges_are_declared_as_a_table` and `test_the_edges_render_as_a_named_table` |
| A4 | restore the fabricated `count` column quantity on a record | 2 of 13: `test_the_projection_draws_no_distribution`, `test_each_member_renders_in_its_own_unit` |
| A5 | cell reads `spec.quantity` again (`UX-290`'s half-fix) | 2 of 13: `test_the_page_prints_the_terminal_s_triple`, `test_each_member_renders_in_its_own_unit` |
| A6 | nested table path is the row again (`UX-292`) | 2 of 13, incl. `test_its_three_folds_are_three_state_keys` |

### Two guards of my own that did not discriminate

Both were written for the two rendering fixes, both were green under
the mutation that reintroduces the defect, and both are corrected
rather than counted:

- the node probe built a record of **three scalar members**, so
  `classify` returned `definition list` and it exercised
  `inlineObject` - not the table path either fix touches. A fourth,
  structural member (`capacities`, which `projection` really has) puts
  it on `mapTable`, and A4 and A5 then redden it.
- `test_a_record_draws_no_distribution` asked the same probe whether a
  density strip was drawn. The strip is `interrogable`'s, drawn around
  the table rather than inside `renderStructured`, so the probe could
  never see one. It is now `test_the_projection_draws_no_distribution`
  on the browser page, and A4 reddens it with the sentence it was
  filed against: `19050000 -> 43200000 across 3 rows`.

### Deviation from the Required Fix

- **The first bullet was already satisfied - a fourth false premise of
  this round.** "Publish the restructuring synthesis as a keyed finding
  in the correlate contract" describes what `correlate/v2` has
  published since `UX-82`, projection and all. Recorded rather than
  quietly done: the gap is one door further along, in the document
  `bga view` actually renders.
- **`elements` is published and not drawn.** The filing asks for the
  section; it did not say which columns. The element list is the union
  of the edge endpoints, so a column for it is the same population as
  the edge table beside it - `UX-338`'s rule, and `UX-288`'s payload
  sweep and `UX-338`'s page sweep both said so when it was drawn.
- **Two guards were amended, narrowly and on the record.**
  `test_no_two_fields_carry_the_same_elements.py` gained
  `_is_an_edge`: a member of a published edge list is a relation, not a
  selection, and every unread declared edge coincides with a
  `serialized_pairs` entry by construction (7 pairs on this fixture).
  The exclusion is on the member, not the list, so
  `restructuring[0].elements` is still swept against everything.
  `test_the_report_you_can_attach.py`'s two committed bounds moved,
  with the split pasted: +2,212 B contract, +838 B data (macro_micro
  only), +295 B source. `PAGE_BUDGET_B` did **not** move; the source
  half is 273,635 B against its 274,000 B ceiling, which is 365 B of
  headroom and the next viewer item in this round will have to raise it
  with its own note.
