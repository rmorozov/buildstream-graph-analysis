# UX-659: two superseded ids sit on a live line of the spec's registry

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-651 (which brought the block under a guard and left this outside it), UX-353 (the retired-id rule) | **Found by:** round 89, track U, while building UX-651's retired-line clauses | **Serves:** anyone reading Part 32's opening block to find out which Plane 2 contract bga writes | **Topic:** contracts

## Motivation

`UX-651` put Part 32's opening block under a guard: every id the
package has reaches it, nothing in it is an id the package does not
have, and the **retired lines** hold retired ids only and cite the
item that retired them. The block is grouped by what a thing is, and
those clauses read the two lines whose note says so.

Two superseded ids are not on either of them:

```console
$ python3 - <<'PY'
import re, pathlib
from bga import contracts
block = pathlib.Path("docs/spec/specification.md").read_text(
    encoding="utf-8").split("# Part 32 — Data Contracts", 1)[1].split("```")[1]
superseded = set(contracts.superseded())
for line in block.splitlines():
    ids = re.findall(r"[a-z0-9-]+/v\d+", line)
    note = line.split("(", 1)[1].rstrip(")") if "(" in line else ""
    retired = [i for i in ids if i in superseded]
    if retired and not ("never written" in note or "normalised in" in note):
        print(f"{retired} on a line whose note reads: ({note})")
PY
['plane2/v2', 'plane2/v1'] on a line whose note reads: (the Plane 2 report - UX-384)
```

`contracts.superseded()` is ten ids; eight sit on the two `read, never
written` lines and on `host/v1`'s `read, normalised in`. These two sit
beside the live `plane2/v3` under a note that reads as a description of
what the family is, not of which member is written. A reader looking up
"which Plane 2 contract does `bga` write" is given three names and a
label that distinguishes none of them.

`UX-651`'s guard cannot say so, and correctly: its retired clauses are
keyed on the lines that claim to be retired. A retired id on a line
that claims nothing is outside the population by construction — the
same shape `UX-655` found one level down in the key surface, in the
same round.

## Required Fix

The block's grouping states liveness for every id, not only for the
ids on the two lines that already say so, and `UX-651`'s guard reads
the property that way: **every id in `contracts.superseded()` sits on
a line whose note says it is retired**, whichever line that is.

Whether `plane2/v1` and `plane2/v2` move to a `read, never written`
line or the Plane 2 line's note gains the distinction is a
presentation choice for whoever takes it — the guard should pass on
either, because the property is about what the block claims, not about
where a name sits.

## Out of Scope

- Part 32.5's registry table, which carries a superseded column and is
  correct at this commit. Declined because this row is about the
  opening block, which is the copy `UX-651` found unguarded.
- `UX-353`'s marker set and the paragraphs it reads — that guard is
  about prose around a retired id in a live document, and this is a
  fenced block it does not scan.
- The other eight superseded ids — declined because they already sit
  on lines whose note says they are retired, so they are what the fix
  makes the property general over rather than work it creates.

## Acceptance Test

Moving any id of `contracts.superseded()` onto a line whose note does
not say it is retired reddens a clause naming that id, and the block at
this commit — with `plane2/v1` and `plane2/v2` placed — is green.

## Outcome

The gap, reproduced at `b298a2b` with the Motivation's script:

```console
$ python3 repro.py
['plane2/v2', 'plane2/v1'] on a line whose note reads: (the Plane 2 report - UX-384)
$ python3 -c "from bga import contracts; print(len(contracts.superseded()),
  set(contracts.superseded()) <= set(contracts.ids()))"
10 True
```

`superseded()` ⊆ `ids()`, so the four ids the block names outside
`ids()` are not in this population and `UX-651`'s three-set allowance
does not interact. The clause takes no intersection with the block's
own names — an id missing from it is also unclaimed, which is M7.

**Placement: the ids moved.** `plane2/v2 plane2/v1` now sit on a
`read, never written - UX-384` line beside the other three retired
lines; `plane2/v3` keeps `the Plane 2 report - UX-384` alone. The block
already had one grammar for "still opened, no longer written" and eight
ids using it; a second grammar in the note is what produced this
defect, and a reader scanning for what `bga` writes reads a column of
names, not a sentence. `UX-384` is the right citation — it bumped
`plane2/v2` → `plane2/v3`, so `test_a_retired_line_cites_the_item_that_retired_it`,
which now runs over this line, passes on it.

**Presentation-agnostic, demonstrated.** `_claimed_retired` reads a note
wholly a retirement note as claiming every id on its line, and a note
naming ids beside the marker as claiming exactly those. Rewriting the
block to the *other* shape — one Plane 2 line, note `(the Plane 2
report; plane2/v2 and plane2/v1 read, never written - UX-384)` — leaves
the whole class green: `6 passed in 0.24s`.

### Mutation table

On the subject, reverted from a scratchpad copy. Clause:
`test_every_superseded_id_sits_on_a_line_that_says_it_is_retired`.

| mutation | expected | got |
|---|---|---|
| M1 `plane2/v1` back on the live line | red, names it | `1 failed`, `['plane2/v1']` |
| M2 the pre-fix block, both back | red, names both | `1 failed`, `['plane2/v1', 'plane2/v2']` |
| M3 retired note loses the marker | red, names both | `1 failed`, `['plane2/v1', 'plane2/v2']` |
| M4 shape B naming `plane2/v2` only | red, names `plane2/v1` | `1 failed`, `['plane2/v1']` |
| M5 shape B in full (control) | green | `1 passed` |
| M6 `analyze/v2` onto the live outputs line | red, names it | `1 failed`, `['analyze/v2']` |
| M7 `analyze/v2` deleted from the block | red, names it | `1 failed`, `['analyze/v2']` |

M6 and M7 are the trap check: keyed neither on the Plane 2 line nor on
the block's contents, so no gate narrows the population.

### The close

```console
$ python3 -m pytest tests/unit/test_the_documents_keep_up_with_the_contracts.py \
    tests/unit/test_a_counted_figure_is_derived.py \
    tests/unit/test_no_document_serves_a_retired_contract.py \
    tests/unit/test_docs_links_and_commands.py tests/unit/test_the_register_is_terse.py \
    tests/unit/test_the_spec_outside_part_32_is_read_only.py -q
306 passed in 19.88s
$ make test-touching
38 file(s) selected (8 census + 30 naming the change) · 923 passed, 4 skipped in 25.40s
$ make lint
All checks passed!
```

### Deviation

The added line moved two figures the fixing guide's item 12 quotes.
`test_the_spec_outside_part_32_is_read_only.py::test_the_guide_quotes_the_range_the_headings_give`
reddened on `Part 32 spans 1515-1940` → `1515-1941`. Beside it, `the
sentence is at line 1671` was already stale at `b298a2b` — 1672 there,
1673 now. Both are corrected here as figures this commit moves; the
pre-existing off-by-one deserves a row, since nothing asserts it.

`test_a_retired_line_holds_retired_ids_only`, the converse, is still
keyed on `annotation.startswith("read")` and would stop reading the
Plane 2 line under the shape not taken. Left alone: this row asks the
superseded→line direction, and the shipped shape keeps both on it.
