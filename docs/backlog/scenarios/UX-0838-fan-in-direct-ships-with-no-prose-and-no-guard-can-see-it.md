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
