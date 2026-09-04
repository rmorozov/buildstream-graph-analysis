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
