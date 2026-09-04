# UX-655: a contract bump landed one level below the key population

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-628, UX-636 (which built the key population and walked its register to zero) | **Found by:** architecture review 16 | **Serves:** anyone reading an `analyze/v6` payload against the prose that describes it | **Topic:** docs

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
