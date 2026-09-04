# UX-606: the selector's bound is measured on one module

**Priority:** Medium | **Status:** 🟢 Done Open | **Depends on:** UX-605 (which measured it), UX-336 (which set the bound) | **Serves:** the session whose one-module edit runs a third of the suite | **Topic:** guards

## Motivation

`UX-605` capped the touching map and, measuring what remained, found
the bound it was restoring is a claim about one module:

```text
mapped modules whose selection exceeds 25, map ignored entirely   18 of 85
worst   bga/cli.py   112 files, from the grep half alone
```

`test_a_one_module_change_selects_a_handful_not_the_suite` calls
`select(["bga/store_aggregate.py"])` — a distinctive two-word name that
appears in 13 files because those 13 are about it. `cli`, `models`,
`loader` and `analyzer` are not that kind of name, and the guard has
never asked about them.

So the sentence "a one-module diff selects a handful" is true of the
sample and unmeasured for half the tree. Not a defect in the selector:
a defect in what is known about it.

## Required Fix

The bound is measured across every module the map names, not one, and
whatever the measurement says becomes the guard — a per-module ceiling
with the modules that exceed it named and argued, or a distribution
with a stated percentile. `store_aggregate` stays as the worked
example; it stops being the whole evidence.

## Out of Scope

- Narrowing `tokens_for`'s stem rule — declined: `UX-522` measured
  that rule and it is the reason `findings` is excluded already;
  changing it needs its own measurement, not this one's.
- The map's cap (`UX-605`) — done there.

## Acceptance Test

The guard reports a figure over the whole mapped population, and a
module added to that population with a selection over the ceiling
turns it red.

## Outcome

**Round 84**, 2026-09-03. The bound measured over its population, and
the finding that the population disagrees with it.

### The gap, measured

`test_a_one_module_change_selects_a_handful_not_the_suite` called
`select(["bga/store_aggregate.py"])` and nothing else. Over every
module the map names — 85 of them, against 456 test files:

```text
min 11 · median 16 · p90 38 · max 116
over the old ≤25 bound: 21 of 85

  116  bga/cli.py                     71  bga/ingest/models.py
   97  tools/bga_view.py              55  bga/report/text.py
   71  tools/bst_native_build_tracer.py   49  bga/analyzer.py
```

So the sentence "a one-module diff selects a handful" was true of the
sample and false for a quarter of the population.

### The finding

**The wide selections are honest, and the bound was the wrong shape.**
116 files name `bga.cli` because 116 files run the CLI — that is the
selector telling the truth about what a change to `cli.py` can break,
not a defect to tune away. `store_aggregate` is narrow because it is a
distinctive two-word name, which is why it was picked and why it could
never have stood for the rest.

### The close, measured

Two clauses replace the one sample:

- `test_the_selection_is_a_fraction_of_the_suite` reads the whole
  mapped population against `{median: 20, p90: 45, max: 130}` — above
  the measured 16/38/116 with room, so ordinary drift is quiet and a
  shape change is loud. Each failure prints the figures it read.
- `test_the_wide_modules_are_named_and_not_merely_tolerated` declares
  the 21 by name. A module joining or leaving has to be argued here.

```text
$ python3 -m pytest tests/unit/test_the_loop_stays_fast.py -q
35 passed in 8.62s
```

### Mutations

| mutation | result |
|---|---|
| every module contributes its bare stem (the `_`-in-stem gate dropped) | 3 red — `median 24, p90 105, max 418` |
| `MAP_ENTRY_CAP` removed (`UX-605`'s defect restored) | 4 red |
| the census dropped from every selection | 1 red — the wide set moved |
| one module deleted from the declared wide set | 1 red, naming it |

**A fifth mutation did not land and is worth the line**: widening the
token filter from `len > 3` to `len > 2` left all 35 green. It is not
the length filter that excludes `cli` — it is the `"_" in stem` rule
beside it, and `UX-522` put that there deliberately. The mutation was
wrong, not the guard; the corrected one is the first row above.

### Deviation from the Required Fix

**None.** The Required Fix offered a per-module ceiling *or* a stated
distribution; both are here, because the distribution is the contract
and the named set is what makes a new outlier loud.

### Tier and suite

`test_the_loop_stays_fast.py` small; 35 tests in 8.62s.
