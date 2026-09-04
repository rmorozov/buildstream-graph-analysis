# UX-636: eighty published keys no document names

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-628 (which measured this and froze it) | **Found by:** round 86, closing UX-628 | **Serves:** anyone reading a payload against the prose that describes it | **Topic:** docs

## Motivation

`UX-628` named the five keys review 15 found and, in doing so, measured
the whole surface for the first time:

```text
consumer surface, printable contracts   199 keys
named in no document outside docs/backlog and docs/audits
  by code-span match                     84  ->  80 after UX-628
  by bare substring                      61
sweep/v1 and whatif/v1                   already complete
```

`UX-628` did not close that. It could not: a clause asserting full
coverage would have been red on arrival by eighty keys, and a guard
that is red on arrival gets silenced rather than satisfied. What it
shipped instead is a **ratchet** — the eighty are a frozen register
that may only shrink and cannot be padded, and a key added after the
row reddens by name.

So the debt is bounded and cannot grow. It is still eighty keys a
reader cannot look up, and the register is the list of them.

## Required Fix

The register empties, contract by contract, and each emptying deletes
its own entries. Order by what a reader reaches for: `analyze/v5` and
`compare/v2` first (`docs/guides/cli.md`'s contract section), the rest
in `docs/design/architecture.md`'s inventory.

Two constraints a track will hit and should be told about rather than
discover:

- `docs/design/architecture.md`'s inventory chapter is at **71 lines
  against a 72-line budget** (`3 × 24`), so prose for a contract goes
  in the guide, not there.
- `run-context/v9` has no JSON Schema in this tool — it is an input
  contract — so `requested_at_us` and `requested_at_source` are outside
  any schema-derived population and reach the register only by hand.

The register is the acceptance criterion: it shrinks to zero, and the
clause that reads it stops being a ratchet and becomes a statement.

## Out of Scope

- Widening the population beyond the printable contracts — declined:
  `UX-628` measured its boundary and stated it, and moving the boundary
  is a different claim from paying the debt inside it.
- The prose *style* of a key's description — the guide's existing rows
  are the pattern; matching them is enough.

## Acceptance Test

The register at zero, and `test_the_documents_keep_up_with_the_contracts.py`
still reddening by name when a key is added to a live schema.

## Outcome (round 87, 2026-09-04) — 🟢 Done

**Premise:** held exactly. Re-measured against this tree, after round
87 bumped the contract to `analyze/v6`:

```text
$ python3 -c "…_consumer_surface(), _undocumented_keys()…"
consumer surface keys: 199    undocumented now: 80    register: 80
undocumented not in register: []    register naming non-keys: []
```

The `analyze/v6` bump moved no key. 80, by contract: `analyze/v6` 29,
`blast/v2` 14, `compare/v2` 11, `store-aggregate/v1` 7, `correlate/v2`
6 plus 6 shared with `analyze/v6`, `capacity-model/v1` 2, `store/v1` 1,
and 3 spanning the two store contracts.

### Where the prose went

One new section in `docs/guides/cli.md`, `### Every published key, by
contract (UX-636)`, immediately under the coverage statement it makes
true — seven tables, one line per key. Not `docs/design/architecture.md`:
its inventory chapter is held to `3 × len(contracts.ids())` lines by
`test_the_inventory_points_at_schema_rather_than_copying_it`, and 80
rows there would trip a guard about *copying* by growing the table it
describes.

Each row says what the key is, not what its schema says it is, and the
section points at `--schema` as the complete list. Written against real
payloads (`tests/fixtures/macro_micro`) rather than the schema alone,
which is how `resolved_as`, `also_matched`, `attribution_partial` and
`attribution_unreliable` — four keys with **no** `description` — got
true sentences rather than guesses.

### After

```text
$ python3 -c "…_undocumented_keys()…"       undocumented now: 0   []
$ python3 -m pytest tests/unit/test_the_documents_keep_up_with_the_contracts.py -q
15 passed in 0.33s
```

The register is `frozenset()`, and `test_the_register_only_shrinks` is
`test_the_register_is_empty` — the ratchet became the statement the
Required Fix asked for. The constant keeps its name, so an entry
reappearing is a debt somebody argues for, not a number that drifts.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| B1 | `regression_confidence_floor` added to `_COMPARE_OPTIONAL` | `…_reddens_naming_the_key`: `['regression_confidence_floor (compare/v2)']`; 1 failed 14 passed |
| B2 | the guide's `keying` row deleted | the same clause, `['keying (blast/v2)']`; 1 failed 14 passed |
| B3 | `keying` put back in the register | `test_the_register_is_empty` + `…_states_the_coverage…`; 2 failed 13 passed |
| B4 | guide's `**0 undocumented keys**` → `**no undocumented keys**` | `…_states_the_coverage_it_actually_has`; 1 failed 14 passed |

B1 is the Acceptance Test: a key added to a live schema still reddens
**by name**. B2 is its converse — the prose is load-bearing, so
deleting one row reddens.

**A known coupling, not a guard that fails to discriminate.** B3
reddens two clauses because the guide states the register's size, so
the size is an input to both. B4 separates them: it moves the guide
alone and reddens only the guide's clause. The pairing predates this
row and is left as it is rather than papered over.

### Deviation from the Required Fix

None in substance. `run-context/v9`'s `requested_at_us` and
`requested_at_source` were already prose-only and stay outside the
schema-derived population, which the coverage section still states.
`test_the_documents_keep_up_with_the_contracts.py` was not on this
track's declared file list — the register lives in it by construction,
and no other track owns it. `bga/schemas.py` was mutated for B1 and
restored byte-for-byte; the tree shows it unchanged.

**Not closed here:** `README.md` is shared this round (`UX-501`), and
both status markers move together —
`dev_close_task.py UX-636 --move` after the merge is the close.
`make test-touching`: 33 files, 808 passed, 4 skipped.
