# UX-645: the census floor spends half the width bound

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-644 (the row that declined it), UX-606 (the selector's measured shape) | **Found by:** round 87, measuring why one module crossed the bound | **Serves:** anyone reading a width figure as if it were about their module | **Topic:** guards | **Area:** tools

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

## Outcome

**The decision: the floor is inside the figure.** The figure is what
pytest is handed, and those 11 files run. Measured over all 87 mapped
modules, not the one `UX-644` looked at:

```text
                        min   median   p90   max    over 25
whole selection          11     17      40   126      23
the module's own          0      6      29   115      14
census floor             11     11      11    11      -
```

The floor is the same 11 under **every** one of the 87, so it changes
no module's relative width and the selector is not wrong. It is 44% of
the bound, and the bound now says so: `HANDFUL = 25` is annotated
**11 census + 14 of your own**, and `CENSUS_FLOOR = 11` is asserted
against `len(census_set())`, so a census that grows reddens the
sentence instead of quietly re-pricing it. `spread()`'s docstring
carries the same statement at the other end.

**What the sentence was hiding.** Keyed on the whole selection,
`make test-touching` could never report "no test file names your
change" - the floor is never empty. One of the 87 modules is in exactly
that position and read as `11 file(s) selected · ... passed`. So the
finding is now read off the naming half:

```text
before   11 file(s) selected · 11 passed in 3.2s
after    No test file names any of 1 changed file(s): ...
         That is a finding, not a pass: run `make test-small` ...
```

and every green run prints the split rather than one number that meant
two things: `17 file(s) selected (10 census + 7 naming the change)`.
The bound's value, the census membership and `spread()`'s arithmetic
are untouched - the published figure is `11-126 of 469 test files,
median 17` before and after.

```text
tests/unit/test_the_loop_stays_fast.py  TestTheSelectorStillSelects
                                        15 passed in 9.79s
make test-touching                      685 passed, 3 skipped in 48.34s
make lint                               All checks passed!
```

**Mutations.**

| mutation | expected | got |
|---|---|---|
| `CENSUS_FLOOR = 12` | red | red: "the census is 11 files, not 12" |
| `census_set()[1:]` in `select` | red | red: "missing [...] of the census floor" |
| the finding keyed on `selected` again | red | red: "11 selected (11 census + 0 naming)" |
| an unexplained file counts as the floor | red | red: the named half loses a file |
| revert all four | green | 15 passed |

**Deviation.** The first draft named the zero-own module in the new
clause. This file is one the selector greps, so naming it made a test
name it: the published figure moved `11-126` -> `12-126` and the module
stopped being an example of itself. The name is out; the fact is here,
and the clause parametrises over the widest and the median instead.

`make test-touching` also reports three failures in this file that are
not this row's: `UX-649` and `UX-645` are 🟢 in their task files and
still 🔴 in the index, which is the orchestrator's row move after the
merge (`UX-501`: a track that edits the index collides on the counts).
This commit therefore ran with `BGA_SKIP_SELECTOR=1`; every other
clause of the selected 685 is green.
