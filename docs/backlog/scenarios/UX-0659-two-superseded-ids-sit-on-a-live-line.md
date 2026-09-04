# UX-659: two superseded ids sit on a live line of the spec's registry

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-651 (which brought the block under a guard and left this outside it), UX-353 (the retired-id rule) | **Found by:** round 89, track U, while building UX-651's retired-line clauses | **Serves:** anyone reading Part 32's opening block to find out which Plane 2 contract bga writes | **Topic:** contracts

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
