# UX-785: the flake census clears any file a task ever mentioned

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-691 (the ledger this reads) | **Found by:** round 109, retro-verifying round 102's unverified tracks | **Serves:** the round that expects the third excursion to name a file and gets silence | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`tools/dev_flake_census.py`'s `filed()` is a substring search over
every file in `docs/backlog/scenarios/` — open, closed, both indexes:

```console
$ python3 -c "
from tools import dev_flake_census as census
doc = {'entries': [{'file': 'tests/unit/test_the_query_asks_about_this_run.py',
        'run_id': str(i), 'shift': 1.7, 'confirmed': False} for i in range(3)],
       'declared': {}}
print(census.unaccounted(doc), census.filed(doc['entries'][0]['file']))"
[] True
```

All three files in the real `tests/flake_ledger.json` are already
"filed" — by `UX-0199`, `UX-0219`, `UX-0302`, `UX-0402`, `UX-0495`,
`UX-0527`, `UX-0537`, `UX-0557`, `UX-0582`, `UX-0667`, none about
flakiness. A mature test file is named in some task file almost by
construction, so the guard `UX-691` exists to add reds on nothing.
The two guard fixtures (`tests/unit/test_x.py`, `test_y.py`) are
named nowhere, which is why the guard's own suite never saw it.

## Required Fix

`filed()` in `tools/dev_flake_census.py` counts a task only when its
header carries a `**Flake:**` field naming the file (or the ledger's
`declared` map does). One marker, one field; the substring search
goes.

## Out of Scope

- Filing the three real ledger files — each has one excursion today;
  the floor is three.

## Acceptance Test

`tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py`
gains a clause on a copy of the real backlog: a file named only in an
unrelated closed task stays unaccounted at three excursions; mutation:
restore the substring search — red.

## Outcome

_Not started._
