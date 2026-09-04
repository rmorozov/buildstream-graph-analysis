# UX-629: a required set grew under an unchanged id

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-343 (one contract version), UX-610 (which grew it) | **Found by:** architecture review 15 | **Serves:** a consumer validating a document it wrote yesterday | **Topic:** contracts

## Motivation

`UX-610` took `_COMPARE_REQUIRED` from 13 keys to 14, so
`schema('compare/v2')['required']` is 15 entries where it was 14 at
`147a49c`. The id did not move.

A `compare/v2` document a consumer wrote before this window no longer
validates against `compare/v2` after it. That is a breaking change by
any reading a consumer would recognise, and the rule does not call it
one:

- §3.7 names **rename** and **removal** as breaking, and is silent on
  a required set growing;
- `additionalProperties: true` protects extra keys, not missing ones;
- `test_output_schemas.py` catches a removal.

The window's `bga/schemas.py` diff is 87 insertions and one deletion,
and the deletion is a `description` string — so by the rule as written
this window is additions and no bump, which is true and insufficient.

**Corrected 2026-09-04, re-measured before implementing.** Both counts
hold exactly:

```text
147a49c : _COMPARE_REQUIRED 13, schema('compare/v2')['required'] 14
d8dfc46 : _COMPARE_REQUIRED 14, schema('compare/v2')['required'] 15
          the added key is `verdict_provenance`
```

The diffstat above is **stale, not wrong**: 87 insertions and 1
deletion was the window at `bcfdc59` (`UX-610`), which is what review
15 read. At `d8dfc46` it is **285 insertions and 1 deletion**, because
`UX-613` landed `capacity-model/v1` afterwards. The deletion is still
the same `description` string, so the conclusion is unchanged.

The three reasons nothing catches it all hold, and one is sharper than
filed: `test_output_schemas.py` does not merely miss a required-set
growth, it **pushes keys into `required`**. Its
`test_compares_schema_requires_every_key_it_emits` fails on any emitted
key that is neither required nor in a named `conditional` set — so a
key the emitter always writes has no way to land *permitted* today
without being called conditional, which it is not. That guard is why
`UX-610` made it required, and it is why the second Fix option needs a
declaration rather than an exemption.

## Required Fix

Either §3.7 gains a third clause — a key entering `required` under a
live id is a bump — or the addition lands as permitted-and-always-
written, declared optional in the schema and guaranteed by the
emitter, with a guard that says which was chosen.

Argued, not picked: the second shape keeps old documents valid and
costs a reader the certainty that the key is there.

## Out of Scope

- `UX-628`, the prose those keys lack.
- `UX-610` itself, which is closed and right about what it published.

## Acceptance Test

A key added to a live schema's `required` list, reddening a guard that
names the choice §3.7 made.

## Outcome (round 86, 2026-09-04) — 🟢 Done

**Premise:** held. 13→14 and 14→15 both exact; the diffstat was stale
and is corrected above.

### The gap, measured

```text
a compare/v2 document written before UX-610 - the 14 keys 147a49c
required - against compare/v2 today:
  required by compare/v2 today : 15
  FAILS: 'verdict_provenance' is a required property
```

Not a hypothetical: the id a consumer pinned stopped accepting the
document that consumer wrote, and the rule called it an addition.

### After

```text
  required by compare/v2 today : 14   VALIDATES against compare/v2
$ bga compare --schema | jq '."bga:always_written"'
["verdict_provenance"]
```

### The decision, and why

**Both**, and **no version bump.** §3.7 gains the third clause — a key
entering `required` under a live id *is* a bump — because without it
the next round breaks another pin. The clause alone does not help the
document already written, though: honouring it retroactively means
`compare/v3`, wider than this row and repairing nothing for the
consumer holding a `compare/v2`. So `verdict_provenance` lands under
the escape the same clause names: **permitted-and-always-written** —
declared, published in the schema's own `bga:always_written` so
`--schema` states the choice, and guaranteed against the real payload
rather than by `required`. The week-old document validates again and
`compare/v2` never moved.

The cost, stated: `required` was a guarantee a *validator* enforced and
the replacement is one a *guard* enforces, which is weaker for a
consumer — they cannot check it from the document alone. That is the
price of not breaking what they already wrote.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| B1 | `verdict_confidence_band` added to `_COMPARE_REQUIRED` (the Acceptance Test) | `…written_before_ux_610_validates`, *'verdict_confidence_band' is a required property*, 1 failed 12 passed |
| B2 | `to_dict` stops writing `verdict_provenance` | `…writes_every_declared_key`, 1 failed 12 passed |
| B3 | `_COMPARE_ALWAYS_WRITTEN = ()` | `…declared_permitted_rather_than_required` + `test_something_is_declared`, 2 failed 12 passed |
| B4 | `_document`'s required/always-written refusal removed | `…refuses_a_declaration_that_says_nothing`, 1 failed 13 passed |
| B5 | spec 32.5's third clause deleted | `…carries_the_third_clause[specification.md]`, 1 failed 13 passed |
| B6 | the rules-card row renamed to `test_output_schemas.py` | `test_the_rules_card_carries_its_own_row`, 1 failed 13 passed |

**B3 reddens two clauses and cannot be isolated** — a fact about the
tree, not a duplicated claim: `compare/v2` is the only contract
declaring anything, so *this key is undeclared* and *nothing is
declared* are the same world. The second declaration separates them and
the docstring says so. A first cut of `…is_the_pre_ux_610_required_set`
asserted `required <= document`, restating the validation clause, so B1
reddened two; it checks the fixture's own shape alone now.

### Deviation from the Required Fix

None on the decision. Three surfaces beyond the two the row implies,
each forced by an existing guard: `docs/design/styleguide.md` §1a
(every `bga:` keyword needs a row — seventeen becomes eighteen),
`test_the_verdict_record_is_a_published_key.py` (`UX-610`'s own guard
asserted the `required` this reverses), and `docs/contributing/
rules.md`. **`docs/contributing/fixing-guide.md` §3.7 still names only
rename and removal** — another track holds it, so the clause is in the
spec, the architecture, the guide and the rules card but not there.

The new guard is 14 tests, **0.58 s single-process** — below
`MEDIUM_FLOOR_S`, so small by default and no `tests/tiers.py` row.
