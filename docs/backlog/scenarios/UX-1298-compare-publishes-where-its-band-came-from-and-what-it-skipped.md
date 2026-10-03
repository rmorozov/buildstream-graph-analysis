# UX-1298: `compare/v2` publishes where its band was read from and how many members it skipped for host

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 36, checklist item 2 (2026-10-02) | **Serves:** R4 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_compare_publishes_where_its_band_came_from.py

## Motivation

`UX-1285` and `UX-1286` added two answers to a band comparison: how
many class members were skipped as measured on another host, and that
the band was read from a `--bundles` tree. Both reach stderr and the CI
comment (`bga/report/ci_comment.py:_band_selection`) and no contract:

```text
$ grep -rn "band_skipped_for_host" bga --include=*.py | cut -d: -f1 | sort -u
bga/cli.py
bga/report/ci_comment.py
$ bga compare BASE CAND --format json --band-from-class 10 --bundles kept/review/default
  (pilot fixture, four kept runs)  schema compare/v2, 34 keys;
  baseline_band_sources lists 3 stamps; "skipped" in the document: False; the tree's path: False
```

`continuous-build-improvement.md` section 5 fixes the order for every new
answer: a key in a published contract, then the report line. This one
went report-first, so a JSON consumer of the gate cannot tell a band of
three from a band that dropped seven for host.

## Required Fix

`compare/v2` gains the skipped count (and which host fields differed)
and the band's source (store or tree) as added keys, no version bump;
the CI comment reads them from the comparison rather than from `args`;
`cli.md`'s compare key list and `architecture.md`'s `compare/v2` entry
name them.

## Out of Scope

A fuzzy host class (`UX-1285`'s own Out of Scope).

## Acceptance Test

A band comparison with one member on another host publishes the count
and the source in `--format json`; the comment's sentence is rendered
from those keys; removing either key reddens the guard.

## Outcome (2026-10-03)

**Premise:** held — neither answer was on the document.

### The gap, measured

`fixture1298.py` (four same-class bundles under `kept/100..103/`, the
newest on host B, baseline and candidate on host A under `ci-job/`),
base tree `13baccdaf`:

```text
$ bga compare BASE CAND --band-from-class --bundles FX/kept --format json
compare/v2 34 keys; {'baseline_band_origin': 'ABSENT', 'baseline_band_skipped_for_host': 'ABSENT'}
$ … --format ci-comment
… — read from the bundles under `FX/kept` — 1 run of this class skipped, measured on another host
```

The comment's sentence came from `args`; the document had neither.

### The close, measured

The same fixture, this branch:

```text
compare/v2 36 keys; {'baseline_band_origin': {'kind': 'bundles', 'path': 'FX/kept'},
                     'baseline_band_skipped_for_host': {'count': 1, 'fields': ['cpu_model']}}
… — read from the bundles under `FX/kept` — 1 run of this class skipped, measured on another host
```

Both keys are permitted and in `bga:always_written` (`null` without
`--band-from-class`), so `compare/v2` does not move (`UX-629`). The
comment's `_band_selection` takes the comparison, not `args`. The
consumer surface the guide states moved 624 → 626 keys;
`tests/quality_reference.json` adopts `cli.py` 3625 → 3635,
`compare.py` 1772 → 1777, `schemas.py` 7172 → 7177 lines.

### Mutations verified red and reverted (7)

`test_compare_publishes_where_its_band_came_from.py`, 5 tests:

| # | mutation | reddened |
|---|---|---|
| N1 | `baseline_band_origin` dropped from `to_dict` | 3 failed |
| N2 | `baseline_band_skipped_for_host` dropped from `to_dict` | 3 failed |
| N3 | skipped count `len(skipped) + 1` | tree, store: 2 failed |
| N4 | origin always `store` | tree: 1 failed |
| N5 | comment reads `bundles` off the comparison, not the key | comment: 1 failed |
| N6 | comment reads `band_skipped_for_host`, not the key | comment: 1 failed |
| N7 | both keys out of `bga:always_written` | pair: 1 failed |

Restored: 5 passed.
