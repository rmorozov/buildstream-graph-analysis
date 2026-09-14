# UX-838: `fan_in[].direct` ships with no prose, and no guard can see it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-628 (the undocumented-key ratchet), UX-655 (a walk that stops one level short), UX-829 (which added the key) | **Found by:** review 23 | **Serves:** anyone reading `elements.fan_in` against the guide that describes it | **Topic:** contracts | **Area:** bga | **Shape:** judgement

## Motivation

`UX-829` (round 116) gave `analyze/v6`'s `elements.fan_in[uid]` a
`direct` field — the incoming names, capped at 40 — and drew it on
the element card. `docs/guides/cli.md:1077` documents the row's other
four fields and not this one:

```text
$ sed -n '1077p' docs/guides/cli.md
| `direct_count`, `transitive_count`, `immediate_dominator` | A row of `elements.fan_in` (`UX-681`): ...
$ grep -rn '`direct`' docs/guides/ docs/design/
(no output)
```

`test_the_documents_keep_up_with_the_contracts.py`'s
`test_a_new_key_with_no_prose_reddens_naming_the_key` — the guard
this exact shape (`UX-628`) is supposed to catch — is green with
`direct` in neither its undocumented set nor its population at all:

```text
$ python3 -c "
import sys; sys.path.insert(0,'tests/unit')
import test_the_documents_keep_up_with_the_contracts as t
surf = t._consumer_surface()
print('direct' in surf, 'direct' in t._undocumented_keys())"
False False
```

`_row_keys` (the walk `_consumer_surface()` runs) reads a row's keys
two ways: an array's `items.properties`, and a `bga:columns` list.
`fan_in` is neither — it is `additionalProperties: {properties: {...}}`,
a dict keyed by element uid — so its five fields, `direct` included,
are invisible to the walk in both directions: an undocumented one
never reddens, and a documented one (`direct_count`) is not proof the
walk saw it either. `UX-655` fixed the same shape one level up
(`bga:columns` for a row an array's `items` did not reach); this is
the sibling gap `additionalProperties` leaves, unfixed.

## Required Fix

`_row_keys` gains a third case: `additionalProperties.properties`,
keyed exactly like `items.properties`. `docs/guides/cli.md:1077`'s row
gains `direct` beside the other four, describing it as `UX-829` did —
the incoming names, capped, drawn on the element card rather than the
table. A regression fixture (a schema with an `additionalProperties`
row and one undocumented key inside it) holds the walk to the new
case the way `test_a_row_can_be_declared_by_its_columns_alone` holds
`UX-655`'s.

## Out of Scope

- Auditing every other `additionalProperties`-shaped row for a second
  silent gap — this item's mutation proves the walk now reaches the
  shape; a second instance, if one exists, is its own row.
- Drawing `direct` anywhere but the element card — `UX-829` already
  decided that; this item is documentation and the walk that verifies it.

## Acceptance Test

`python3 -m pytest tests/unit/test_the_documents_keep_up_with_the_contracts.py -q`
green with `direct` reachable from `_consumer_surface()['direct']`
naming `analyze/v6`; mutation: revert `_row_keys` to the two-case walk
— the new regression fixture's undocumented-key clause reds, proving
the case, not just the row, is what closes the gap.

## Outcome

**Gap measured.** Before: `_consumer_surface()['direct']` raised
`KeyError` — the two-case walk never put `direct` in the surface, so
`'direct' in _undocumented_keys()` read `False` for absence, not
clearance. After the third case, `_consumer_surface()['direct'] ==
['analyze/v6']`. The wider walk reached **289** keys (was 269), 20 of
them newly reachable, 12 named nowhere in the documents:
`baseline_share`, `candidate_share`, `coefficient_of_variation`,
`delta_share`, `high_variability`, `is_foundation`, `median_us`,
`p75_us`, `p95_us`, `probability`, `risk_score`, `slack_us` — across
`elements.blast_radius`, `elements.criticality_probability`,
`elements.duration_variability` and `compare/v2`'s
`attribution_deltas`, all `additionalProperties` rows like `fan_in`.
Per this round's decision, each got one sentence in `cli.md`'s
contract table rather than narrowing the walk to `fan_in`.

**Close measured.** `python3 -m pytest
tests/unit/test_the_documents_keep_up_with_the_contracts.py -q` — 25
passed (was 24). `make test-touching`: 52 files (27 census + 25
naming the change), 1654 passed, 4 skipped. `make lint`: clean, 0 new
findings.

**Mutations verified red and reverted (2 discriminating, 1 rejected):**

| mutation | file | guard reddened | count |
|---|---|---|---|
| drop `additionalProperties` from `_row_keys` | test file | new fixture `test_a_row_can_be_declared_by_additional_properties_alone`, plus `test_the_guide_states_the_reach_it_actually_has` (289 stated, 269 actual) | 2 failed |
| walk restored; drop the `risk_score`/`is_foundation` row from cli.md | `docs/guides/cli.md` | `test_a_new_key_with_no_prose_reddens_naming_the_key` — `is_foundation (analyze/v6)`, `risk_score (analyze/v6)` | 1 failed |

**A guard that did not discriminate.** The Acceptance Test's own
mutation — dropping `direct` alone from cli.md's `fan_in` row, walk
restored — passed all 25 clean. `direct` is already named in
`docs/design/architecture.md:518` (UX-829/UX-837's changelog:
`` `fan_in[].direct`, `price_cost_us`, ... ``), which
`test_a_new_key_with_no_prose_reddens_naming_the_key`'s own message
accepts ("...or the row in docs/design/architecture.md's inventory").
Confirmed: `_named_in_the_documents()` holds `'direct'` before and
after the cli.md edit. Substituted `risk_score`/`is_foundation`
(named nowhere else) above to prove the same clause does discriminate
on a real gap; `direct`'s cli.md prose stands per the Required Fix.
