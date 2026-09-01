# UX-483: a provenance record inlines whatever its path resolves to, and only convention keeps that from being a whole population

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 73, `UX-479`'s export measurement | **Serves:** the round that adds a claim, cites the map its finding is about, and ships a report carrying that population once per claim | **Topic:** contracts

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

## Outcome (round 73, 2026-09-01) — 🟢 Done

### Item 1: the shape of the risk, measured first

Every path the claims actually cite, on two scales, with what each one
resolves to:

```text
=== macro_micro (11): 26 cited path(s), 154 B if every one is inlined
        18 B  scalar  elements.zero_slack_share           (chain-graph)
        18 B  scalar  confidence.primary                  (confidence)
        17 B  scalar  capacity_recommendation.cores_busy  (capacity-recommendation)
         8 B  scalar  total_duration_us                   (wait-category)
  provenance as published: 10,706 B

=== scale (1,202): 11 cited path(s), 91 B if every one is inlined
        18 B  scalar  headline.chain_share       (blast-radius-ranking)
        18 B  scalar  floors.efficiency_score    (efficiency-score)
         4 B  scalar  elements.blast_radius[toolchain.bst].downstream_count
  provenance as published: 6,171 B
```

**Every cited path on both scales resolves to a scalar**, and 154 B is
what inlining all of them costs. So the answer the item asked this
measurement to choose between - a rule, a cap, or a guard - is a rule
and a guard, and *not* a cap: there is nothing to cap, and a size
threshold would have been a constant with no measurement behind it.

### Item 2: the rule the builder enforces

`record` no longer inlines whatever a path resolves to. A **scalar**
is carried, because a reader checking the claim wants the number in
front of them; a **container** is cited and not copied:

```json
{"path": "elements.blast_radius", "resolved": true, "elided": "dict[40]"}
```

Any container, not one over a size — the measurement above is why that
costs nothing. The schema describes `elided` (`value` was already
optional, `required` is `path` and `resolved`), and `decision.js`
renders `dict[40] - follow the path` where it would otherwise have
printed `undefined` for an absent key.

**Thinned, not refused.** The item called refusal "the stricter and
probably better answer". It is not taken, and this is the deviation:
`paths` can be computed from the run — `_blast_paths` is — so a path
that resolves to a container on some graph nobody has built yet would
raise inside a user's `bga analyze`. A citation without a copy loses
nothing a reader needs and cannot break a run.

### Item 3: one guard that counts rather than reads

`TestNoRecordCarriesAPopulationTwice`, in
`test_the_report_you_can_attach.py`. No clause in it knows which paths
the claims cite:

- no evidence row carries a container, on either committed run;
- no evidence `value` is over **400 B** — the widest measured is 18 B,
  and this catches by weight what the shape clause catches by type;
- no single record is over **2,000 B**.

That last bound is the one the measurement chose. The obvious
instrument — provenance as a *share* of the report — reads 26.7% /
13.6% / 1.0% on golden / macro_micro / scale, so it measures the
report's size rather than the records'. The **largest single record**
is 959 / 1,077 / 902 B on the same three and does not move with the
graph, which is exactly the quantity that explodes when one record
inlines a population: `UX-479` measured +4,955 B on one record.

```text
golden         11 records,  7,671 B (26.7% of a  28,734 B report); largest   959 B
macro_micro    15 records, 10,676 B (13.6% of a  78,650 B report); largest 1,077 B
scale (1,202)   9 records,  6,153 B ( 1.0% of a 628,122 B report); largest   902 B
```

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| S1 | the builder inlines a container again | 1 of 31 — `test_a_cited_container_is_thinned_rather_than_dropped` |
| S2 | S1 **and** `wait-category` cites `attribution` rather than one of its keys — `UX-479`'s defect, reproduced on a committed run | 3 of 31 — the container clause on both runs, plus the synthetic one |
| S3 | a scalar value is published 400x longer, heavy without being a container | 3 of 31 — the value-size clause, the per-record ceiling, and the export bound |

Each was proved to have landed with a `grep -c` before the run, and
reverted from a copy after it.

**S1 alone only reddens the synthetic clause**, and that is worth
recording rather than hiding: with the rule in place, no change to the
claim list can make a committed report carry a container, so the
report-level clauses can only be falsified by breaking the builder
*and* pointing a claim at a population — which is what S2 does, and
which is the defect as it actually happened.

### Deviation from the Required Fix

- **Thinned rather than refused**, for the reason above.
- **No size threshold on the container rule.** The item proposed "a
  container above some size"; the measurement found no container cited
  at all, so any threshold would have been unmeasured. Every container
  is cited by path.
- The guard's third clause measures **one record** rather than "a
  population another document publishes, measured by size". The share
  version was written first and is what the measurement rejected — it
  ranges 26.7% to 1.0% across three runs of the same code.

### The runs

```text
python3 -m pytest tests/unit/test_the_report_you_can_attach.py -q
                     31 passed in 5.70s
make test-touching   273 passed in 32.71s
make test            5,682 passed, 27 skipped in 320.64s (0:05:20)
make lint            ruff + PyMarkdown, both clean
```
