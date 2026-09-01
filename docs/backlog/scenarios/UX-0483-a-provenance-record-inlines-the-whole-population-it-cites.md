# UX-483: a provenance record inlines whatever its path resolves to, and only convention keeps that from being a whole population

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 73, `UX-479`'s export measurement | **Serves:** the round that adds a claim, cites the map its finding is about, and ships a report carrying that population once per claim | **Topic:** contracts

## Motivation

`bga/provenance.py::record` builds one evidence row per cited path:

```python
value = resolve(document, path)
row = {"path": path,
       "value": None if value is UNRESOLVED else value,
       "resolved": value is not UNRESOLVED}
```

`value` is whatever the path resolves to. For a scalar
(`headline.chain_share`) that is right and reads better for it. For a
**population** it is a second copy of a document the report already
publishes — `UX-288`'s rule, which `UX-344` applied to the finding
itself and not to the record beside it.

`UX-479` walked into it. Both blast claims cited
`elements.blast_radius`, the whole map, and neither had ever fired on a
committed capture: both fixtures are chain-bound and that arm was
closed. The moment it opened, `macro_micro`'s provenance grew 4,955 B
against the finding's own 1,485 B, and **fifteen guards reddened** —
among them "every numeric leaf declares a unit", "no map is keyed by
data it cannot describe" and the leaf-depth ceiling. All three were
right: `downstream_count` under a uid key is a leaf the schema
describes at `elements.blast_radius.*.downstream_count` and cannot
describe at `provenance[].evidence[].value.<uid>.downstream_count`.

`UX-479` fixed **those two claims**, by citing one scalar per element
the sentence names:

```json
{"path": "elements.blast_radius[base.bst].downstream_count",
 "value": 2, "resolved": true, "quantity": "count"}
```

Provenance went 13,217 B → 10,039 B on `macro_micro` (8,262 B before
either claim could fire), and all fifteen guards went green.

**What is left is the general case.** Nothing stops the next claim
from citing a map, and the fifteen guards that caught this one caught
it only because the population happened to be uid-keyed and numeric.
A population of strings, or one nested a level deeper, would have
travelled silently — and at 1,202 elements
(`bga gen-synthetic /tmp/scale --seed 1`) one such citation is
megabytes.

## Required Fix

- **Measure the shape of the risk first**: for each path in `_CLAIMS`,
  the size of what it resolves to, at eleven elements and at 1,202.
  Pasted. That says whether the answer is a rule, a cap, or a guard.
- **A rule the builder enforces**, rather than a convention each claim
  keeps: an evidence row whose resolved value is a container above some
  size cites without copying — path and `resolved: true`, no `value` —
  or the builder refuses the path outright, which is the stricter and
  probably better answer since every claim so far can name a scalar.
  Whichever, the schema says which shape a consumer will find.
- **One guard that counts rather than reads.** No embedded document may
  carry a population another document publishes, measured by size.
  `tests/unit/test_the_report_you_can_attach.py` already splits an
  export into page and data and is the place for it.

## Out of Scope

- **The two blast claims** — `UX-479` narrowed both to scalar
  citations; this row is about the builder that let them be written
  that way.
- **`EXPORT_BUDGET_B`** — whether 8 MiB is the right ceiling is
  `UX-360`'s question and was argued there.
- **Scalar inlining** — a resolved `headline.chain_share` costs
  nothing to carry and a reader checking the claim wants the number in
  front of them, so this row must not take that away.

## Acceptance Test

```bash
bga gen-synthetic /tmp/scale --seed 1
bga view /tmp/scale --export /tmp/report.html
python3 - <<'PY'
import json, re, pathlib
text = pathlib.Path('/tmp/report.html').read_text()
doc = json.loads(re.search(
    r'<script type="application/json" id="bga-report">(.*?)</script>',
    text, re.S).group(1))
print('elements  ', len(json.dumps(doc['elements'])))
print('provenance', len(json.dumps(doc['provenance'])))
PY
```

with the figures before and after, plus a claim deliberately pointed at
a population showing the new rule refuses or thins it, and the guard
that reddens on the "before" payload.

## Outcome

_Not started._
