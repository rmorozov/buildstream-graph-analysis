# UX-651: the spec's Part 32 block is two ids behind the registry

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** — | **Found by:** architecture review 16 | **Serves:** anyone reading the spec to find out what contracts `bga` has | **Topic:** docs

## Motivation

Part 32 opens with a fenced block listing every contract by name,
grouped by what it is. It is the first thing a reader of the spec
meets, and it is two ids behind:

```console
$ python3 - <<'PY'
import re, pathlib
from bga import contracts
block = pathlib.Path("docs/spec/specification.md").read_text(
    encoding="utf-8").split("# Part 32 — Data Contracts", 1)[1].split("```")[1]
named = set(re.findall(r"[a-z0-9-]+/v\d+", block))
print("ids missing from Part 32's opening block:",
      sorted(set(contracts.ids()) - named))
PY
ids missing from Part 32's opening block: ['analyze/v5', 'capacity-model/v1']
```

`capacity-model/v1` is `UX-613`, `closed.md` row 619; `analyze/v5` is
`UX-641`, which bumped the live id to `analyze/v6` and left the
superseded one unlisted. Both rows are in the same window, so the block
missed two ids in one review period. Its own annotation, at
`specification.md:1530`, still reads

```text
analyze/v4          analyze/v3    analyze/v2                  (read, never written - UX-535)
```

when the retired set now begins at `analyze/v5` and the item that
retired it is `UX-641`.

`test_the_documents_keep_up_with_the_contracts.py` is green throughout,
and correctly: `UX-565` made
`test_every_published_schema_is_in_the_spec_contract_section` read
**Part 32.5's registry table**, precisely because "every id is also
mentioned in Part 32's opening block" had let a deleted 32.5 row pass.
Nothing reads the block itself. `test_a_counted_figure_is_derived.py`
is the other guard over this Part, and its
`_spec_contract_block()` anchors at

```python
start = text.index("| output | schema | printed by |")
```

which is 32.5's table header at line 1650, 117 lines below the block's
closing fence at 1533. And no guard
names the Part at all by the heading the block sits under:

```console
$ git grep -n "Part 32 — Data Contracts" -- tests/unit/ tools/
$
```

So the registry has two copies, one guarded and one not, and the
unguarded one is where a reader starts.

## Required Fix

The block is derived from `bga.contracts` rather than hand-listed, or a
guard reads it the way `UX-565` made 32.5's table read — every emitted
id present, nothing present that nothing emits, and the retired group
naming the item that retired it. Part 32 is inside the region a round
may edit (fixing guide item 12), so the correction lands with the
guard.

`test_a_counted_figure_is_derived.py::TestTheSpecCountsItsOwnTable`
already reads 32.5's table for its counts and its position; the block
is the same shape one Part up.

## Out of Scope

- Part 32.5's table and the architecture inventory — both guarded, both
  correct at this commit.
- Anything outside Part 32. The rest of the spec stays read-only.

## Acceptance Test

`analyze/v5` and `capacity-model/v1` appear in Part 32's opening block
with the rest, the retired line cites `UX-641`, and a guard reddens
when an id is added to `bga.contracts` without reaching the block —
shown by adding one and watching it fail.

## Outcome

A guard reads the block, and the block is right. Two lines of Part 32
moved: `capacity-model/v1` joins `sweep/v1` on the *what capacity buys*
line, and the retired line becomes `analyze/v5 analyze/v4 analyze/v3
analyze/v2 (read, never written - UX-641)`.

### Before

The Motivation's script, and the file that should have been red,
both at `933de24`:

```console
$ python3 - <<PY   ...the Motivation's script, verbatim...
ids missing from Part 32's opening block: ['analyze/v5', 'capacity-model/v1']

$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_the_documents_keep_up_with_the_contracts.py -q
15 passed in 0.25s
```

### After

```console
$ python3 - <<PY   ...the same script, and the other direction...
ids missing from Part 32's opening block: []
block names, not emitted or read: ['analysis/v9']

$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_the_documents_keep_up_with_the_contracts.py -q
20 passed in 0.28s
```

`analysis/v9` is the one id the block names that `ids()` and `reads()`
both refuse, and 32.5 already says why - it is the analyzer's in-memory
result shape, *not a fourth input*. So the "nothing present that
nothing emits" clause reads three sets: `ids()`, `reads()`, and the ids
Part 32 gives a numbered subsection to. A naive clause reddens on all
four of `analysis/v9`, `graph/v9`, `run-context/v9`, `trace/v9`.

### Mutations verified red and reverted (5)

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `OWNED = ("phantom/v1",)` on `bga.bundle`, block untouched | `..._every_id_the_package_has_reaches_the_block`, and the 32.5 and architecture clauses | 3 failed 17 passed |
| M2 | `phantom/v1` added to the block's `sweep/v1` line | `..._names_nothing_the_package_does_not_have` | 1 failed 19 passed |
| M3 | `analyze/v6` appended to the retired line | `..._retired_line_holds_retired_ids_only` | 1 failed 19 passed |
| M4 | the retired line's citation back to `UX-535` (its state as filed) | `..._cites_the_item_that_retired_it` | 1 failed 19 passed |
| M5 | `_part_32_opening_block()` forced to return `[]` | `..._is_what_part_32_opens_with` and the reach clause | 2 failed 18 passed |

**A guard of mine did not discriminate, and M4 is why it is what it
is.** The first cut asserted only that the cited item's task file names
the newest id on the line. `UX-535` names `analyze/v5` twice - it is
the bump that *created* it - so the exact defect this item was filed
for passed. It now also asks for the live id of the same family, which
only the retiring item carries: `UX-641` names `analyze/v6`, `UX-535`
names no live `analyze/*` at all.

M5 is the reason the fifth clause exists: with the parse empty, the
three set-difference clauses were **green**, because a set difference
against nothing is empty.

### Deviation from the Required Fix

The second of the two offered routes - the guard, not derivation. A
derived block would have had to generate the annotation column too, and
the annotations are prose (*the measuring machine*, *a capture you can
carry*) that no registry holds.

**Not fixed, reported:** `plane2/v2` and `plane2/v1` are in
`superseded()` and sit on the live *Plane 2 report* line, so the
retired-line clauses do not reach them. Grouping them is a block
decision this item did not ask to re-take.
