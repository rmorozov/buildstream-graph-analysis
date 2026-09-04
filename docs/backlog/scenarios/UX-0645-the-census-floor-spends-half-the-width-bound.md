# UX-645: the census floor spends half the width bound

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-644 (the row that declined it), UX-606 (the selector's measured shape) | **Found by:** round 87, measuring why one module crossed the bound | **Serves:** anyone reading a width figure as if it were about their module | **Topic:** guards

## Motivation

Eleven of every module's selection comes from **census** guards —
clauses that sweep the whole tree and therefore select for every
module in the map, whatever it is. Measured while diagnosing
`UX-644`:

```text
bga/report/rate.py selects 36 files      (HANDFUL bound: 25)
   23  from the coverage map
   11  census guards            the same 11 for every module
    4  named directly
```

The floor changes no module's *relative* width, which is why the
selector still works and why `UX-644` declined to touch it. But it
consumes **44% of the 25-file bound** before a module's own tests are
counted, so a module with 15 genuinely related tests reads as 26 and
crosses. The bound's stated meaning — "a one-module change selects a
handful, not the suite" — is measured against a number that is
partly a constant.

## Required Fix

Decide, with the measurement, whether the census floor belongs inside
the width figure:

- If it does, the bound's docstring says so and names the floor, so a
  reader knows 25 means "11 census plus 14 of yours".
- If it does not, the selection reports the two populations separately
  and the bound applies to the module's own.

Either way the number stops meaning two things at once. No behaviour
change is required to close this row — the guard may already be
correct — but its sentence has to match what it counts.

## Out of Scope

- Changing which guards are census guards. They sweep the tree because
  that is what they check.
- The bound's value — declined because `UX-606` measured 25 against a
  real distribution, and this row disputes what the figure counts, not
  where it sits. Moving it would hide the question rather than answer
  it.

## Acceptance Test

The width figure and its docstring agree about whether the census
floor is inside it, and a reader of either can predict the other.
