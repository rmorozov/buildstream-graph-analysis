# UX-544: the hand-built *node* census has a hole the document census does not

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-537` (the document half, closed), `UX-264` (the shared shim), `UX-235` and `UX-262` (two defects this shape produced) | **Found by:** `UX-537`, whose scope was the document | **Serves:** the round that trusts a shim | **Topic:** guards

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

## Outcome (round 81, 2026-09-02) — 🟢 Done

### The gap, measured — the census was not narrow, it was dead

The item says a harness that assigns before returning is invisible.
True, and it understates it. The pattern was `return \{[^}]*setAttribute`,
and `[^}]*` stops at the first `}` — which is the nested `attrs: {}`
inside every node literal. Run over the tree as it stood at `ca825c3`:

```text
files the old pattern matched: 1 ['tests/unit/test_the_dom_shim_is_one_instrument.py']
```

The one file it matched is the census itself, which it skips by name.
So it scanned 300-odd files and matched **nothing**, in either form.
A guard that has gone completely quiet still passes, every time.

### The close, measured

Brace-matched out of the Python rather than regexed, `UX-537`'s way.
It then named five sites in four files — one more than the item knew:

```text
test_copy_a_finding.py               189
test_focus_is_an_investigation.py    194
test_one_click_from_investigation.py 262, 323, 498   <- :498 was unlisted
test_the_arrows_say_why_now.py       576
```

All five now build with `shim.makeNode`. `_node` in
`test_one_click_from_investigation.py` gained `BGA_DOM_SHIM` in its
env, which is the runner `test_the_arrows_say_why_now.py` imports.

Two files define `setAttribute` on a real `document.createElement`
node and are correctly *not* named:
`test_a_command_renders_as_a_command.py:107`,
`test_two_row_selectors_became_one.py:43`.

### What the second instrument was buying: nothing

`test_focus_is_an_investigation.py` carried the interesting one — its
own `prepend`, `removeChild`, and a `querySelectorAll` that matched
`data-role=` and nothing else. The shim has all three, generally. All
**9 clauses pass unchanged** on the shim's implementations, so the
narrowed matcher and the hand-written `prepend` were never load-bearing.

That file also already imported the shim's `installDocument` and
carried a comment saying `make` was "this file's own node, not the
shim's" — `UX-537` moved the document and left the node standing.

```text
tests/unit/test_focus_is_an_investigation.py         9 passed
tests/unit/test_one_click_from_investigation.py  }  52 passed
tests/unit/test_the_arrows_say_why_now.py        }
tests/unit/test_copy_a_finding.py                   15 passed
tests/unit/test_the_dom_shim_is_one_instrument.py    7 passed
```

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| M1 | a harness planted in the `return {…}` form | named at `test_zz_mutation_return_form.py:3` — 1 failed, 6 passed |
| M2 | a harness planted in the assign-then-return form | named at `test_zz_mutation_assign_form.py:4` in the same run |

Both planted at once, so the run also shows the census reports *all*
offenders rather than stopping at the first.

### Deviation from the Required Fix

**One, on step 3.** The fix asks to check the focus harness's
`prepend`/`querySelectorAll` "against a real browser". No browser was
driven: the evidence here is that all 9 of that file's clauses pass
unchanged against the shim's implementations, which is weaker than a
browser check and is stated as such. The shim's `prepend` is itself
the one `UX-235` measured against a browser, which is why substituting
it is not a step backwards.
