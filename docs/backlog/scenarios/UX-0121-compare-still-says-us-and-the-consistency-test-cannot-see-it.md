# UX-121: compare still says "Us", and the consistency test cannot see it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-111 (done — this is its unfinished sixth surface) | **Topic:** guards

## Motivation

UX-111 item 1 fixed `Execution On Chain Us` → `Execution On Chain` —
on `analyze`. `bga compare` still renders the raw field name through a
naive `.title()` (`bga/report/text.py:1157`) beside a value formatted
in seconds (`_fmt_us`, `:939-940`), on the one surface a CI reviewer
reads most. The guard test asserts against the **helper**
(`test_report_consistency.py:88-95` checks `_attribution_label`), not
against rendered output — so the test that exists to keep six surfaces
consistent passed while one of the six stayed wrong. That is the UX-85
pattern (a guard bound to the wrong layer) recurring in the round that
was fixing rendering.

## Required Fix

Route compare's attribution-delta rendering through the same
`_attribution_label` path as analyze, and re-point (or extend) the
consistency test to assert against **rendered surfaces**: render all
six on one fixture and grep the actual text for the forbidden raw
labels, so a seventh surface added later is covered by construction.

## Out of Scope

- Any numeric change; labels only.

## Acceptance Test

`bga compare` on any pair shows `Execution On Chain (s)`-style labels,
none ending in `Us`; the reworked consistency test fails when a raw
label is reintroduced into any rendered surface (verified by
mutation); golden compare fixtures updated in the same commit.

---

## Fix Implemented

`bga compare`'s attribution-delta rendering now calls
`_attribution_label`, the same path `analyze` uses:

```text
Attribution Deltas:
  Execution On Chain        3610.50s ( 99.9%) -> 2708.55s ( 99.9%)   -901.95s (-0.0pp)
```

One line of renderer. The interesting half is the test.

### The guard was bound to the wrong layer

`UX-111`'s consistency test asserted `_attribution_label` — the helper —
so it passed while one of the six surfaces it existed to police rendered
the raw field name throughout the audit. That is `UX-85`'s pattern
recurring inside the round that was fixing rendering.

The test now **renders every surface** and greps the real text:

```python
for name, text in _rendered_surfaces().items():
    for token in (" Us ", " Us\n", "_us ", "Wait Us", "Chain Us"):
        assert token not in text, f"{name} renders a raw field name: {token!r}"
```

`_rendered_surfaces()` builds all nine text surfaces from one fixture, so
a tenth added later is covered without anyone remembering to extend a
list of helpers.

Checked against the unfixed renderer before shipping, since a guard that
has never failed is a guard nobody has tested:

```text
E   AssertionError: compare renders a raw field name: ' Us '
```

## Verification Log

Done 2026-08-19. The failing-then-passing check was run by reverting the
one-line renderer fix with the new test in place.
