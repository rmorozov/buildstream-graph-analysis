# UX-829: five of seven joined fields on the elements table draw no column

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-681 (fan-in joined), UX-382 (the join), UX-808 (§1b's last instance) | **Found by:** round 115, the design review | **Serves:** R2 and R3 reading one element's row | **Topic:** viewer | **Area:** bga-viewer | **Shape:** judgement

## Motivation

`structured.js:1457` marks the `elements` table `data-joined` with what
it merged; the rendered headers are what it drew:

```text
data-joined   element_durations, slack, downstream_count, unweighted_depth, blast_radius, fan_in, criticality_probability
th            element · Element durations · Downstream count · Is leaf · Element kind · Observed critical
no column     fan_in · slack · blast_radius · unweighted_depth · criticality_probability   (5 of 7)
```

§1b: every published field reaches a reader or the page names the
ones that do not. `UX-681` joined `fan_in` for this table and the
reader still meets fan-in only as "Top fan in: storm.bst" in a `dt`.
The owner's ask for a per-element incoming-dependency list is the same
gap one level down: `fan_in[uid]` carries counts and the dominator,
never the names.

## Required Fix

Every `data-joined` field gets a header, the five beyond the width
budget behind a "more columns" disclosure (§3a's depth budget, one
level); `fan_in[uid]` gains `direct` — the incoming names, capped at
the row cap — drawn in the element card, not the table (§3c: forty
names is a cell no row survives). The section's lead sentence names
any field drawn elsewhere.

## Decomposition

Input classes: an element with 0, 4 and 1,004 direct dependencies
(scale), a leaf, and the golden fixture's eleven; the journey is R2's
"what does my element wait on" in the answer key.

## Out of Scope

- Transitive fan-in as a list — the closure of 1,004 names is the JSON door's.
- The bottleneck's own ranking — `UX-719`.

## Acceptance Test

On the scale export `th[data-column]` covers every `data-joined` field
or the lead sentence names the rest; the element card lists direct
fan-in; mutation: drop a header — `test_the_merge_carries_every_field.py`
extended to this table reds.

## Outcome

**Gap measured.** On the scale export (`gen-synthetic --seed 1`,
1,202 elements), cycling every `elements` preset's `<select>` and
collecting `th[data-column]`: the "All elements" default carried
`element, element_durations, downstream_count, is_leaf, element_kind,
observed_critical` only; across all five presets `unweighted_depth`
and `fan_in` (any of `direct_count`/`transitive_count`/
`immediate_dominator`) drew no column at all, and `criticality_
probability`/`blast_radius` reached one (`probability`,
`weighted_duration_us`) only by riding a different question's columns.

**Close measured.** A sixth preset, "What does my element wait on"
(`element, slack, unweighted_depth, probability, direct_count,
weighted_duration_us`), covers all 7 `data-joined` signal names once
`elementSignalTable`'s flattening is accounted for (`blast_radius` ->
`weighted_duration_us`, `fan_in` -> `direct_count`, `criticality_
probability` -> `probability`). `fan_in[uid].direct` (sorted incoming
names, capped at 40 via `DIRECT_NAMES_CAP`, mirroring `structured.js`'s
`TABLE_OPENS_BOUNDED_ABOVE`) is excluded from the table by construction
(arrays never flatten into a row) and drawn on the element card instead
— measured on the scale export, 9 on-demand cards built by clicking
every `a.inspect`, all 9 print `Depends on: <names>`. The elements
table's lead sentence now names where it went. Python: the golden and
macro_micro committed fixtures each carry `direct` per element (refreshed
via `dev_refresh_analysis.py --write`); a synthetic 1,004-predecessor
graph asserts `direct_count == 1004` and `len(direct) == 40`.

**Mutations verified red and reverted (2):**

| mutation | file | guard reddened | count |
|---|---|---|---|
| drop `direct_count` from the new preset's columns | `bga/schemas.py` | `TestEveryJoinedFieldOnTheElementsTableDrawsAColumn::test_every_signal_reaches_a_column_or_the_lead_names_it` — `fan_in` uncovered | 1 failed |
| drop the `[:DIRECT_NAMES_CAP]` slice | `bga/graph/fan_in.py` | `TestTheDirectListIsCappedAndNamed::test_the_cap_class` — `1004 == 40` | 1 failed |

Both reverted from copies under the scratchpad (never `git checkout`),
confirmed green after.

Extended beyond the declared surfaces, to keep the existing suite
green rather than narrow this item's fix: `docs/design/styleguide.md`
(§3c/§3d now name this test file, matching `test_the_styleguide_names_
its_guards.py`); `tests/unit/test_no_two_fields_carry_the_same_
elements.py` (the new `direct` list coincidentally names the same
3 elements as `bottleneck.high_fanout_elements` on `macro_micro` —
excluded the same way two earlier coincidences on this fixture already
are, documented in `_is_a_fan_in_measure`); `tests/unit/test_the_
report_you_can_attach.py` (the two committed-export byte bounds moved
by the added schema prose and per-element data, following that file's
own convention for a additive move).

Pre-existing, unrelated to this diff (confirmed by `git diff` touching
neither file): `test_a_new_key_with_no_prose_reddens_naming_the_key`
(`start_offset_us`, from `UX-823`) and `test_the_style_guide_states_
every_budget` (§3e's "36,300" vs the code's "36,900", from `UX-827`);
`make lint`'s `dev_baseline.py --check` also reports one new pyright
finding on `bga/analyzer.py`, a file this track never touched.
