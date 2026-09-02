# UX-544: the hand-built *node* census has a hole the document census does not

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-537` (the document half, closed), `UX-264` (the shared shim), `UX-235` and `UX-262` (two defects this shape produced) | **Found by:** `UX-537`, whose scope was the document | **Serves:** the round that trusts a shim | **Topic:** guards

## Motivation

`UX-537` moved all 54 hand-built `document` objects onto the shared
shim and left a census guard so a fifty-fifth cannot appear. Its
sibling — `test_no_harness_builds_its_own_node` — matches a `return {`
carrying `setAttribute`, and four harnesses build a full node
instrument the other way round:

```text
const node = {...};   // ... then
return node;          // -> not matched
```

`test_focus_is_an_investigation.py` and the three handoff harnesses do
this. The focus one has a `prepend` that never unparents and a
`querySelectorAll` that only understands `data-role` — which is
`UX-235`'s defect and `UX-262`'s, the two this whole family exists to
stop, still set as a trap.

`UX-537`'s scope was the *document*; the node half is this row.

## Required Fix

- Widen the census to the assignment form, measured the way `UX-537`
  measured the document one: brace-match the literals out of the
  Python and bucket what they actually differ in, before converting.
- Then the same treatment: what the shim already does is deleted, what
  differs becomes an override, and the trap the focus harness carries
  is checked against a real browser rather than assumed.

## Out of Scope

- The document census — `UX-537` closed it.

## Acceptance Test

A harness that builds its own node instrument in either form is named
by the census, with a mutation that plants one in each form.
