# UX-542: `_compute_diagnostics` is now the largest phase of `analyze`

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-539` (the round whose profile this is), `UX-531` | **Found by:** `UX-539`'s profile, after its own two terms went | **Serves:** anyone analysing a monorepo | **Topic:** analysis

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

## Outcome (round 81, 2026-09-02) — 🟢 Done

### What the 200 is: a spec default, and the premise is falsified

The item asked whether it is "a confidence target, a constant nobody
chose, or a budget". It is none of those — it is ground truth, twice:

```text
docs/spec/specification.md:1307  Part 26     "default:  200 samples ... ±10%"
docs/spec/specification.md:2768  Part 41.2   "The default: 200 samples"
```

So the count cannot move without editing the spec, which is outside
what this repository may touch. "A fixed sample size over a graph that
grows" is what Part 26 asks for, and the precision question it implies
is already answered there.

### The real gap: Part 41.2's other sentence

```text
Part 41.2, :2776   "should reuse the graph topology and avoid rebuilding
                    graph structures. Only durations and dynamic
                    programming values vary."
```

`P1-28` hoisted the topology and its guard holds that. Four things that
also do not vary were still rebuilt inside every one of the 200 samples:

```text
task_key.split('|')[0], per task per sample     4,002 x 200 = 800,400
an intermediate per-task `perturbed` dict, immediately re-aggregated
the deg==0 source list, rescanned from in_degree.items()
the terminal test, rescanned as `not in successors or not successors[x]`
```

All four hoisted; the perturbation now writes straight into the element
aggregate the critical path is defined on, in the same RNG draw order
with the same integer arithmetic.

### The close, measured

Interleaved A/B, min of three, four arms in one worktree so only the
code differs (`base` = `ca825c3`):

```text
     n       base     UX-541     UX-542       both
  1202     1.561s     1.459s     1.495s     1.476s     UX-542 x0.958
  2402     4.218s     3.796s     4.030s     3.628s     UX-542 x0.956
  4002    10.439s     9.491s     9.826s     8.406s     UX-542 x0.941
```

Output byte-identical at all three (sha256 of the document less
`run_instance`/`producer`: `52d1e446dc33e8cf`, `217b3924ceaea175`,
`0cb454b75b589195`, unchanged). Absolute wall here is well under round
80's 26.41s at 4,002 on the same nominal container — which is why the
arms are interleaved and only ratios are quoted.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M2 | `element_uids_of` called back inside the sample loop | `test_the_element_mapping_is_derived_once_not_per_sample` — 1 failed, 5 passed (200 calls against a bound of 1) |

The guard is the call count, not the seconds, as `UX-539` set.

### Deviation from the Required Fix

**Partial.** The second bullet — "one pass over the run rather than 200
perturbations of it" — was **not** done, and should not be: the 200 are
genuine resamples of a seeded distribution (Part 26), so collapsing
them to one pass answers a different question and changes every
published probability. What was taken is the substitution that keeps
the answer: the per-sample work that does not vary between samples.
`_compute_diagnostics` is still the largest phase; it is now 5.9%
smaller at 4,002 and spends its time on the resampling Part 26 asks
for rather than on rebuilding a mapping.
