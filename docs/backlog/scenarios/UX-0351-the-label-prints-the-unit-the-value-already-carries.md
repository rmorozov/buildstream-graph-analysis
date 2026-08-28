# UX-351: the label prints the unit the value already carries

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-341 (one unit per dimension) | **Serves:** anyone reading a field name on the page | **Topic:** viewer

## Motivation

`title(key)` turns a payload key into a label by replacing underscores
with spaces. Since `UX-341` every key that holds a duration ends `_us`
and every key that holds memory ends `_bytes`, so the reader now meets
this:

```text
Execution on chain us    43.2 s   Time the chain's own elements spent...
Dependency wait us        0 ms    Time a chain element spent ready but...
Untracked head us         2.7 s   Wall-clock before the first tracked...
Idle us                   0 ms    Time with nothing running at all.
Category us               2.7 s   Wall-clock in the attribution category...
```

"Execution on chain us" is not English, and the `us` is answering a
question the value has already answered in the same line: the number
beside it reads `43.2 s`. The suffix exists so the *contract* says what
the number is; the label is for the reader, and the renderer has
already used the declaration to format the value.

This got worse rather than better with `UX-341`: before it, some of
these keys ended `_s` or carried no suffix at all, and the ones that
did were fewer. Unifying the payload's units is right; letting the
payload's spelling reach the reader's eye is the cost that came with
it, and it is one function.

## Required Fix

`title()` drops a trailing unit token when the key's declared quantity
already accounts for it — `_us` on a `duration_us`, `_bytes` on a
`bytes`, `_share` on a `share`. Derived from the declaration rather
than from a list of suffixes, so a key whose name ends `_us` and is
*not* a duration keeps its suffix and looks as odd as it is.

## Out of Scope

- Renaming the payload keys. The suffix is `UX-341`'s rule and the
  contract is where it belongs.
- Prettier labels in general (`Cpu` → `CPU`, and the rest). A separate
  and larger question about a label table.

## Acceptance Test

On both committed fixtures, no rendered label ends in a unit token that
its column's or term's declared quantity already carries, asserted by
walking every rendered term against the schema. `Execution on chain us`
reads `Execution on chain`, and its value still reads `43.2 s`.
