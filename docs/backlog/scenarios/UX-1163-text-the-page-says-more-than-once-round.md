# UX-1163: text the page says more than once, round 155's residue

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_each_sentence_is_drawn_once.py`

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

"Dominant binary, ran one process at a time" x19; "Below the sample floor" x3; "6 rows" up to 4x per drawing (`#utilisation` 6 rows x3, beside "Copy N rows"); the floors symbols T∞/gap in the drawing, the sentence and the pairs; `#confidence` "Name" header beside "Ordering violations 0".

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- **Evidence label** (`element.js`): a block's label leaves the card when an advice line on it already makes that claim (`dominant_binary` = `cpu-concentration`, `serial_binary` = `serialization-point`); the summary names the fold.
- **Sample floor** (`shapes.js`): a self-built strip beside a table of two rows or fewer is not drawn; the rows are the values. Published strips keep `UX-226`'s sentence.
- **Row count** (`structured.js`): the badge draws only `N of M` / `none of M match`; at rest `Copy N rows` beside it is the count, as `UX-1152` made it at two rows. The strip keeps its `n` (§2).
- **Floors** (`drawings.js`): an exhibit decomposition's sentence says the total, the parts the axis dropped and the mark; a ticked part is said by its tick, and the twin still holds every row. The pairs stay: they carry the symbols' definitions.
- **`#confidence`** (`structured.js`, `sections.js`): a table left one column by `statedOnce` draws no header; `confidence.ordering_violations` is a `FIELDS_DRAWN_ELSEWHERE` member (the gate row, and above zero the chapter answer).
- Guard: `test_each_sentence_is_drawn_once.py` gains a census of the five on `golden`, `macro_micro`, two-plane. Mutation: restore each repeat.

## Required Fix

Each repeated string is said once, at the place a reader looks for it.

## Out of Scope

The T∞/LB/T_C names (`UX-1159` keeps a plain name beside each use, an owner default).

## Acceptance Test

`test_each_sentence_is_drawn_once.py`'s census reads 0 for each named string on the three pages. Mutation: restore one repeat, and the census reds.

## Outcome

### Gap measured

The guard's census (`census.py`, `test_each_sentence_is_drawn_once.py`'s `_MEASURE`, every fold open, 1440) on the base viewer (`3e6feb45`):

```text
             evidenceLabel  sampleFloor  rowCount  floorTick  header  gatePair  opened height
golden             0             2           8         4         1        1       32,220 px
macro_micro        8             3          16         4         1        1       58,163 px
two_plane          7             3          11         5         2        1       62,975 px
```

`rowCount` counts tools saying one table's count twice outside a control (badge, strip, "All N rows:").

### Close measured

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_each_sentence_is_drawn_once.py -q
42 passed
             evidenceLabel  sampleFloor  rowCount  floorTick  header  gatePair  opened height
golden             0             0           0         0         0        0       32,065 px  (-155)
macro_micro        0             0           0         0         0        0       57,758 px  (-405)
two_plane          0             0           0         0         0        0       62,277 px  (-698)
golden page (export minus data)   149,988 B -> 150,232 B   (+244 B)
```

The 82 test files naming the touched modules, single process: 1379 passed, 20 skipped, 2 failed - both the 150,000 B page budget (`test_the_page_itself_stays_within_its_budget`, `test_the_page_half_is_under_its_bound`), which the base already sat 12 B under; the owner's 160,000 B is `UX-1167`'s.

### Mutations verified red and reverted (9)

| # | mutation | reddened |
|---|---|---|
| M1 | evidence label always drawn | `evidenceLabel` on `macro_micro`, two-plane (golden has no Plane 2), 2 failed |
| M2 | strip drawn at two rows | `sampleFloor`, 3 failed |
| M3 | badge created visible | `rowCount`, 3 failed |
| M3b | refresh never hides the badge | none: at rest `refresh` does not run on an unbounded table; only a filter set then cleared shows it |
| M3c | refresh never unhides the badge | `hiddenBadge` x2 and the two-plane reach clause, 3 failed |
| M4 | uniform note "All N rows:" | `rowCount`, 3 failed |
| M5 | exhibit sentence names ticked parts | `floorTick`, 3 failed |
| M6 | one-column header kept | `header`, 3 failed |
| M7 | `ordering_violations` pair drawn | `gatePair`, 3 failed |

### Deviation

- Two-plane keeps 12 of its 19 "Dominant binary, ran one process at a time" labels: those cards have no `cpu-concentration`/`serialization-point` advice, so the label is the claim's only statement there. `macro_micro`'s 9 all go.
- Re-based guards that asserted the old behaviour: `test_the_shape_before_the_rows.py` (a two-row table draws no strip), `test_the_shape_channel_is_built.py` (no fixture has an under-floor strip now; the existence clause goes), `test_the_tools_scale_with_the_table.py` (note reads "Every row:"; a headerless table must be one column).
