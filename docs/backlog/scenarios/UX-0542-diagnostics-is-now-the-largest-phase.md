# UX-542: `_compute_diagnostics` is now the largest phase of `analyze`

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-539` (the round whose profile this is), `UX-531` | **Found by:** `UX-539`'s profile, after its own two terms went | **Serves:** anyone analysing a monorepo | **Topic:** analysis

## Motivation

`UX-531` and `UX-539` between them took `bga analyze` at 4,002
elements from 44.01s to 26.41s and the two terms they named are gone.
The profile's new leaders are somewhere neither round looked:

```text
cProfile, 4,002 elements, after UX-539
bga/diagnostics/analyzer.py:707  compute_criticality_probability   14.5s cum
bga/diagnostics/analyzer.py:807  _compute_perturbed_critical_path  12.2s cum · 200 calls
```

`_compute_diagnostics` is now the **single largest phase**, and 200
perturbed critical-path computations is a shape — a fixed sample size
over a graph that grows — rather than a lookup that was missed.

Filed rather than taken: it was outside `UX-539`'s declared surfaces,
and a round that widens its own scope on a profile is the thing
`decompose` §2 exists to stop.

## Required Fix

- Say what the 200 is: a confidence target, a constant nobody chose,
  or a budget. If it is a sample size, it has a stated precision and
  the precision decides the count — measured, not assumed.
- Then the same substitution the last two rounds used, if it applies:
  one pass over the run rather than 200 perturbations of it.
- The guard is the bound, not the seconds, as in `UX-539`.

## Out of Scope

- Removing diagnostics or making it optional — `UX-229` decided that
  the tool publishes why it believes what it believes.

## Acceptance Test

The exponent and the phase share re-measured interleaved A/B, min of
five, at 1,202 / 2,402 / 4,002, output byte-identical.
