"""UX-335: the store shape a field capture hit, built once.

A `store/v1` document says every entry of `snapshots` is an object.
A store written by a half-finished prune, an interrupted `bga
snapshot`, or a hand-edit can carry a `null` there anyway - and the
viewer read the row before checking it, so **one bad row collapsed the
entire report**:

```text
served, golden run, one null row prepended to store.json
  refused : "Could not load this run
             TypeError: Cannot read properties of null (reading 'elements')"
  sections: 0
```

Twenty-nine sections of correct analysis discarded because one row of
one *optional* payload was malformed.

The damage is applied to a **real** store rather than to a
hand-written blob: the healthy half has to stay real, or the fixture
proves the page survives a document no `bga` would ever produce. Both
readers use this - the shim guards feed `damaged()` straight to the
renderers, and the browser walk serves it - so neither can drift into
testing a different degeneracy from the other.
"""
import copy

#: Why each shape is here. The names are what the guards parametrize
#: over, so a failure says which degeneracy rather than which index.
SHAPES = ("null_row", "string_row", "row_without_snapshots_key")


def damaged(store, shape="null_row"):
    """`store`, with one row replaced by something that is not a row.

    Returns a deep copy: a guard that damaged the caller's store would
    make every later assertion in the same test a measurement of this
    function instead of of the page.
    """
    if shape not in SHAPES:                              # pragma: no cover
        raise ValueError(f"{shape}: not one of {SHAPES}")
    copied = copy.deepcopy(store)
    rows = list(copied.get("snapshots") or [])
    if shape == "null_row":
        rows.insert(0, None)
    elif shape == "string_row":
        # A `json.dumps` of a row instead of the row - the shape a
        # double-encoding bug produces, and one `typeof` away from the
        # null case.
        rows.insert(0, "{\"stamp\": \"20260101T000000Z\"}")
    else:
        # The whole document with its rows missing: `snapshots` absent
        # rather than empty. `[]` means "a store with no snapshots";
        # absent means "not a store listing at all".
        copied.pop("snapshots", None)
        return copied
    copied["snapshots"] = rows
    return copied


def unreadable_rows(shape):
    """How many rows `damaged(..., shape)` makes unreadable."""
    return 0 if shape == "row_without_snapshots_key" else 1
