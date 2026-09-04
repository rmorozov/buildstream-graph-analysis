# UX-655: a contract bump landed one level below the key population

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-628, UX-636 (which built the key population and walked its register to zero) | **Found by:** architecture review 16 | **Serves:** anyone reading an `analyze/v6` payload against the prose that describes it | **Topic:** docs

## Motivation

`UX-628` replaced the contract guard's population — ids became keys —
and `UX-636` paid the resulting 80-key debt off, so `docs/guides/cli.md`
now states coverage rather than promising it:

> - **every key of every printable contract is named in a document**,
>   and a key added to one of those schemas has prose or the guard
>   reddens naming it;

The very next window bumped a contract, and the keys it published are
below where the population reaches:

```console
$ python3 - <<'PY'
import sys; sys.path.insert(0, "tests/unit")
import test_the_documents_keep_up_with_the_contracts as t
from bga import schemas
surface = t._consumer_surface()
row = schemas.schema("analyze/v6")["properties"]["parallelism"][
    "properties"]["levels"]
keys = [c["key"] for c in row["bga:columns"]]
print("analyze/v6 parallelism.levels row keys:", keys)
print("in the consumer surface:", [k for k in keys if k in surface])
print("surface size:", len(surface), " undocumented register:",
      len(t.UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS))
PY
analyze/v6 parallelism.levels row keys: ['level', 'width', 'elements']
in the consumer surface: ['elements']
surface size: 199  undocumented register: 0
```

`UX-641` is a **major bump** — `parallelism.levels` went from an array
of integers to an array of records, and the architecture row says so:
*"a consumer indexing it as integers breaks."* The three keys that
replaced the integers are exactly what a consumer now has to read, and
no document names one of them as a key of this row:

```console
$ git grep -c '`level`' -- docs/guides/ docs/design/ docs/spec/ README.md
$
```

`width` reaches the guard's code-font scan only inside the finding id
`graph-width`, which the identifier regex splits; `elements` reaches it
only as `analyze`'s own top-level key of that name, which is the one
the surface reports above. Neither is a sentence about a level.

The surface figure did not move: **199 keys before the bump and 199
after**, because `_consumer_surface()` reads each schema's top-level
properties plus the properties of a row directly under a *top-level*
array. `parallelism` is a top-level object; its `levels` array is one
level further in, and nothing there is counted. The register reads
zero and the guard is green.

That boundary was a deliberate, argued choice — the full recursive set
is 891 keys, and a document naming all of them is the second copy of
the schemas `UX-384` banned. The finding is not that the boundary is
wrong. It is that the *statement* above it is unqualified, so a bump
whose whole content lands outside the population reads as covered.

This is review 15's pattern one round on: a guard is written against
the vocabulary that existed when it was written, and here the
vocabulary is a shape rather than a name.

## Required Fix

The population reaches a row under an array at any depth, or the
statement of coverage names the depth it stops at and a second clause
holds the contracts whose published shape lives deeper.

Which one is a measurement, not a preference: count the surface under
"a row under an array at any depth" first. If it stays within one
order of the current 199 the population widens; if it approaches 891
the statement is what changes, and `parallelism.levels` gets prose in
the `UX-636` table either way.

## Out of Scope

- The 891-key recursive set. Declined by `UX-628` with its argument,
  and that argument does not change here.
- `run-context/v9`, `graph/v9` and `trace/v9`, outside the population
  because they have no JSON Schema — held by
  `test_the_input_contracts_are_outside_the_population_on_purpose`.
- The `analyze/v6` bump itself, which is correct: a type change under a
  live id is a break, and it moved the id.

## Acceptance Test

`level`, `width` and `elements` of `analyze/v6`'s `parallelism.levels`
row are each named in a document, and the guard reddens when a fourth
column is added to that row with no prose — shown by adding one.

## Outcome

The population widened, because counting it first said it could. The
Required Fix made that a measurement; the candidates, over the nine
printable schemas at `933de24`:

```text
199   today: top-level properties + a row directly under a top-level array
218   + a row under an array at ANY depth
236   + the `bga:columns` a row declares, at any depth      <- taken
514   every nested `properties` key, distinct
891   the same, counting repeats
```

236 is within one order of 199, so the population widens: 37 new keys,
**15** of them named in no document.

**A figure the task file quotes is a different quantity.** "The full
recursive set is 891 keys" is 891 *occurrences* of a `properties` key;
the distinct set is **514**. Both are in the walk's docstring now,
because the choice above is an order-of-magnitude argument and it
matters which end it is against.

**"A row under an array at any depth" does not reach this row.** That
widening alone is 218 keys and holds neither `level` nor `width`:
`parallelism.levels` has **no `type` and no `items`**, only
`description` and `bga:columns`, so its columns are the entire
declaration of what one of its rows holds. The walk reads both.

### Before and after

```console
$ PYTHONPATH=. python3 ...the Motivation's script, and after it...
in the consumer surface: ['elements']
surface size: 199  undocumented register: 0

in the consumer surface: ['level', 'width', 'elements']
named in a document: ['level', 'width', 'elements']
surface size: 236  undocumented register: 0   undocumented keys now: []

$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_the_documents_keep_up_with_the_contracts.py -q
23 passed in 0.31s        # 20 before, and green throughout the gap
```

The 15 keys are prose in `docs/guides/cli.md`: a new *inside a row of a
block below the top level* table for `analyze/v6`'s twelve, and rows in
`compare/v2`, `correlate/v2` and a new `sweep/v1` table for `presence`,
`envelope_bytes` and `makespan_us`.

### Mutations verified red and reverted (5)

| # | mutation | reddened | count |
|---|---|---|---|
| N1 | a fourth column `slack_us` on `parallelism.levels`, no prose | `..._reddens_naming_the_key` (`{'slack_us': ['analyze/v6']}`) and the guide figure | 2 failed 21 passed |
| N2 | the `bga:columns` half of `_row_keys` deleted | `..._reaches_a_row_below_a_top_level_object`, guide figure at **218** | 2 failed 21 passed |
| N3 | `_row_keys` back to top-level arrays only | the same two, guide figure at **199** - the state as filed | 2 failed 21 passed |
| N4 | the guide's surface figure to `**199 keys**` | `..._states_the_reach_it_actually_has` | 1 failed 22 passed |
| N5 | `"items": {"type": "object"}` on `parallelism.levels` | `..._a_row_can_be_declared_by_its_columns_alone` | 1 failed 22 passed |

**A guard of mine does not discriminate for one of the three keys.**
`width` was already counted as named before any prose existed - by
`el.style.width` in the architecture, `graph-width` in `roles.md` and
`cli.md`, `--width 200` in the styleguide, none of them a sentence
about a level. Of the three keys, only `level` would have reddened
`..._reddens_naming_the_key`. `code_spanned` splits identifiers and
cannot tell a CSS property from a payload key; that is the instrument
`UX-628` argued for and it is not re-decided here, which is why the
*reach* clause reads the row's own columns instead.

### Deviation from the Required Fix

The guide's surface figure is derived, so N1 reddened two clauses: a
key entering the surface moves it. Deliberate - that key already needs
a prose row in the same file. The second offered branch is not skipped
either: the guide still says what is outside the 236, with the 514
beside it, because the walk is a reach and not a claim over every
nested key.
