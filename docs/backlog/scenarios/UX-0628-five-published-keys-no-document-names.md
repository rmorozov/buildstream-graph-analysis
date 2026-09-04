# UX-628: five published keys no document names

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-233 (the mechanical half), UX-610, UX-612 (which added them) | **Found by:** architecture review 15 | **Serves:** anyone reading a payload against the prose that describes it | **Topic:** contracts

## Motivation

Five keys shipped in this window and no document outside
`docs/backlog/` and `docs/audits/` names any of them:

```text
verdict_provenance            compare/v2      UX-610
queue_wait_us                 store/v1        UX-594
queue_wait_absent_reason      store/v1        UX-594
requested_at_us               run-context/v9  UX-612
requested_at_source           run-context/v9  UX-612

$ git grep -l <key> -- 'docs/**/*.md' README.md ':!docs/backlog' ':!docs/audits'
(empty, for each of the five)
```

The prose that should carry them stops short. `architecture.md:946`
ends `compare/v2` at *"the candidate's diagnosis chain"*;
`architecture.md:1012` ends `run-context/v9` at *"the resolved
`native_max_jobs`"*. Both contracts gained keys after those sentences
were written.

**Corrected 2026-09-04, re-measured at `d8dfc46` before implementing.**
The five-key grep holds, all five empty. `compare/v2` is at 946 as
filed. `run-context/v9` is at **1012**, not 1011 — one line off, which
is why the sentence is quoted above and not only located. Both quoted
endings are verbatim. Filed as `:1011`; kept here because a reference
that drifts by one is the reference this repository asks to be quoted
rather than numbered.

Two premises the filing did not carry, measured the same way and
material to the Required Fix:

```text
$ PYTHONPATH=. python3 -c "from bga import schemas; schemas.schema('run-context/v9')"
KeyError: "unknown schema 'run-context/v9' - this tool produces
analyze/v5, blast/v2, capacity-model/v1, compare/v2, correlate/v2,
store-aggregate/v1, store/v1, sweep/v1, whatif/v1"
```

`run-context/v9` is an *input* contract (`contracts.reads()`) with no
JSON Schema in this tool, so no guard whose population is derived from
`bga/schemas.py` can ever see `requested_at_us` or
`requested_at_source`. Two of the five keys are outside any mechanical
key-level population, whatever that population is.

And the population's size, which the Required Fix asks to be measured
before it is chosen — the 9 printable contracts' consumer surface
(top-level properties plus the properties of a row directly under a
top-level array):

```text
distinct surface keys 199, of which named in no document outside
docs/backlog/ and docs/audits/:
  bare substring match   61
  code-span match (`key`) 84
```

`sweep/v1` and `whatif/v1` are the only two contracts of the nine
whose every surface key is already named.

`test_the_documents_keep_up_with_the_contracts.py` is green because it
guards **ids**. Five keys walked past it, which is `UX-233`'s
mechanical half doing exactly what it promised and no more.

## Required Fix

The prose rows for `compare/v2`, `store/v1` and `run-context/v9` name
what they now carry, and the guard's population is keys rather than
ids — or, if key-level coverage is deliberately out of scope, the
document says so where a reader will look.

## Out of Scope

- `UX-629`'s question about the required set, which is the same window
  and a different property.
- The keys themselves — they are right, and this row is about the
  prose beside them, not the payload.

## Acceptance Test

A key added to a live schema with no prose, reddening a guard that
names the key.

## Outcome (round 86, 2026-09-04) — 🔴 implemented, not closed

**Premise:** held, corrected above — `run-context/v9` is at `:1012`
not `:1011`, and two of the five keys are outside any schema-derived
population at all.

### The gap, measured

```text
$ git grep -l <key> -- 'docs/**/*.md' README.md ':!docs/backlog' ':!docs/audits'
   rc=1 for each of the five
$ PYTHONPATH=. python3 -m pytest tests/unit/test_the_documents_keep_up_with_the_contracts.py -q
8 passed
```

Five published keys, no document, and the guard that exists to catch
exactly this green — its population is contract **ids**. The census
that sized the alternative: the consumer surface is 199 keys, 84 named
in no document outside `docs/backlog/` and `docs/audits/`; `sweep/v1`
and `whatif/v1` are the only two of nine already complete.

### After

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_the_documents_keep_up_with_the_contracts.py -q
15 passed

# the Acceptance Test: a key added to a live schema with no prose
$ PYTHONPATH=. python3 -m pytest ... -k reddens
E  AssertionError: published key(s) no document names:
   ['regression_confidence_floor (compare/v2)']. Name it where a consumer
   looks - docs/guides/cli.md's contract section, or the row in
   docs/design/architecture.md's inventory (UX-628)
1 failed
```

The three prose rows name their keys, so the register is 80 not 84. A
key added after this row reddens **by name**.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | `regression_confidence_floor` added to `_COMPARE_OPTIONAL`, no prose | `..._reddens_naming_the_key`, 1 failed 13 passed |
| A2 | the checked population forced empty | `..._large_enough_to_mean_something`, 1 failed 13 passed |
| A3 | `blended` removed from `store-aggregate/v1`, leaving a dead register entry | `test_the_register_is_all_live_keys`, 1 failed 13 passed |
| A4 | the guide's three input-contract ids replaced by "input contracts" | `..._states_the_coverage_it_actually_has`, 1 failed 13 passed |
| A5 | `compare/v2` added to `bga.ingest.READS` | `..._outside_the_population_on_purpose`, 1 failed 13 passed |
| A6 | `code_spanned` loosened to a bare word scan | `test_prose_about_a_key_is_not_the_key`, 1 failed 14 passed |

**Two guards of mine did not discriminate.** A4 first read the whole
of `docs/guides/cli.md` and came back **green**: line 345 already names
`run-context/v9`, `graph/v9` and `trace/v9` while describing what `bga
analyze` reads, so the clause could not fail whatever the coverage
section said. It reads only the `### Which keys the prose names`
section now — the `falsify` skill's *subject, not the argument*. A6 was
worse because it was invisible: loosening the match to a bare word scan
left **all six** clauses green, since a looser instrument only
*shrinks* the undocumented set and every clause was a claim about that
set. `code_spanned` is pure now and asserted on five keys that are also
English words. A first cut of `test_the_register_only_shrinks` restated
the naming clause, so A1 reddened two; it asserts the size cap alone.

### Deviation from the Required Fix

Both halves, bounded — not the either/or as filed. Full key coverage
was measured at 84 undocumented keys before it was chosen, and a guard
red on arrival by 84 gets silenced; so the register is frozen and only
shrinks, and the declined half is stated where `UX-295` established a
payload's reader looks — `docs/guides/cli.md`.

**Blocked, reported not worked around:** the fuller statement belonged
in spec 32.5; adding lines inside Part 32 moves its end line, which
`test_the_spec_outside_part_32_is_read_only.py` requires
`docs/contributing/fixing-guide.md` to quote — a file this track was
told not to touch. The spec is unmodified.

`make test-touching`: 41 files selected, 907 passed, 4 skipped.
