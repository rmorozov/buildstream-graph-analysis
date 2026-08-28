# UX-345: the chain's length is a duration wearing a count's declaration

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-341 (one unit per dimension), UX-201 (the schema says what things are) | **Serves:** anyone reading the signals block, and every consumer of `analyze/v3` | **Topic:** contracts

## Motivation

The page prints this, on the `macro_micro` fixture, in the signals
block:

```text
Critical path length   43200000   How many elements the chain runs
                                  through. A count of elements, not a
                                  duration - `floors.t_infinity_observed`
                                  is the time.
```

The chain runs through **ten** elements. `43200000` is microseconds —
43.2 seconds — and it is the same number as
`floors.t_infinity_observed`, which the sentence beside it points at as
*the other thing*:

```text
signals.critical_path_length             43200000
floors.t_infinity_observed               43200000
signals.critical_path_detail rows              10
structural.metrics.critical_path_length        10
```

`bga/floors/observed.py` is explicit about where it comes from:

```python
return graph_analysis['critical_path_length']
```

So one name carries two quantities in one document: `structural.
metrics.critical_path_length` is the count the description describes,
and `signals.critical_path_length` is a duration. Both declare
`bga:quantity: count`. The reader is shown a number 4.3 million times
too large, under a sentence that specifically denies it is a duration.

**Why `UX-341`'s guard did not catch it.** That guard asserts no *two*
vocabulary members measure one dimension, and no leaf name carries two
different *declared* quantities. Here both sites declare the same
member — `count` — and one of them is simply wrong about its own value.
A vocabulary check cannot see that; only a check against the value can.

## Required Fix

`signals.critical_path_length` is renamed for what it holds and
declared as what it is — `duration_us` — or removed, since
`floors.t_infinity_observed` already publishes the identical number
under a name that is not a lie. Removing it is the better answer if
nothing reads it: `UX-288`'s rule is that a population is published
once.

A guard reads the emitted payload and fails when a value contradicts
its declaration by shape: a leaf declared `count` whose value is not a
whole small number beside a `duration_us` of the same magnitude is the
case this item is filed on, and the general form is that a declared
`count` on both fixtures is an integer under some stated ceiling
relative to the population it counts.

## Out of Scope

- Renaming `structural.metrics.critical_path_length`. That site is
  already right: it holds the count of elements its description
  describes, and only the `signals` copy was ever a duration.
- A general value-versus-declaration checker for every quantity.
  `share` outside 0..1 and `count` that is not integral are the two
  cheap ones; the rest is a separate item if the two find anything.

## Acceptance Test

On both committed fixtures, no leaf declared `count` holds a
non-integral value, and no two leaves sharing a name hold values whose
magnitudes differ by more than the population they describe.
`signals.critical_path_length` either reads 10 or does not exist, and
the sentence beside whatever remains is true of the number printed.

## Outcome (round 52, 2026-08-28) — 🟢 Done

### The gap, measured

One duration, published three times, once under a name and a `count`
declaration that both denied it was a duration. On the two committed
fixtures, before:

```text
                                          golden   macro_micro
signals.critical_path_length               14000      43200000
floors.t_infinity_observed                 14000      43200000
structural.sensitivity.critical_path_us    14000      43200000
structural.metrics.critical_path_length        3            10
len(signals.critical_path_detail)              3            10
```

The page printed the first row beside the sentence *"How many elements
the chain runs through. A count of elements, not a duration —
`floors.t_infinity_observed` is the time"*, over a number that **is**
`floors.t_infinity_observed`.

### After

```text
                                          golden   macro_micro
signals.critical_path_length                None          None
floors.t_infinity_observed                 14000      43200000
structural.sensitivity.critical_path_us    14000      43200000
structural.metrics.critical_path_length        3            10
len(signals.critical_path_detail)              3            10
confidence.duration_coverage                 1.0           1.0
```

The declared-value census the guard walks, after:

```text
golden       200 declared numeric leaves   duration_us  90  count  49  share  44  ratio 17
macro_micro  609 declared numeric leaves   duration_us 248  count 207  share 110  ratio 32  bytes 12
```

### Removed rather than renamed

`UX-288`'s rule is that a population is published once. The number is
`compute_critical_path`'s weighted result, and
`structural.sensitivity.critical_path_us` publishes it under a name
that says so, in the section (`graph`) a reader looking for the
chain's cost is already in. A rename would have left the same
microseconds in two places under two names; the count the removed
key's own description described is `structural.metrics.critical_path_length`,
which was already correct. This is a **deviation from the Required
Fix**, which offered rename *or* removal and preferred removal "if
nothing reads it": `bga/report/_shared.py`'s `GRAPH_SIGNAL_KEYS`,
`bga/provenance.py`'s two chains and `tools/bga_snapshot.py` read it,
and all three now read `floors.t_infinity_observed` or
`structural.sensitivity.critical_path_us` instead.

The removal folds into `analyze/v3` rather than cutting a `v4`:
`UX-341` bumped the id in this same unreleased round, and no release
has ever written `v3`.

### The two the guard found on its first two runs

* **`signals.wall_clock_share`** declared `share` and held
  `20433333.33` — microseconds. `format.js`'s share branch printed it
  as `2043333333.0%`. The producer's own field is
  `wall_clock_share_us`, and that is the published name now; both its
  descriptions say time rather than fraction.
* **`confidence.duration_coverage`** published `1.0001793150166365`.
  Quantization (Part 3.2) rounds a span's start and its finish onto the
  50 ms grid independently, so a normalized task can come out up to one
  epsilon longer than the span it was made from; across `macro_micro`'s
  eleven spans that lifts the accounted sum 9 ms above the 50.191 s
  declared:

  ```text
  spans 11   declared 50191000 us   accounted 50200000 us   ratio 1.0001793150166365
  per-span delta   max +27000 us   min -8000 us   sum +9000 us
  ```

  Coverage is complete at 1.0 when the grid explains the excess, and
  `compute_confidence` reads it that way. An excess the grid **cannot**
  explain stays visible — a duplicated task stream would double the
  numerator, and clamping that would hide it (mutation A5).
  `SHARE_SLACK` stayed at `1e-6`: widening it to admit 1.8e-4 would
  have bought nothing this fix does not, and every other share on both
  fixtures lands inside 0..1 exactly.

### The third check, tried and rejected

The Acceptance Test also asked that *no two leaves sharing a name hold
values whose magnitudes differ by more than the population they
describe*. Measured on the fixtures before writing it, legitimate
spread inside one `(name, quantity)` reaches **4,739x**
(`total_duration_us`, six sites) and **1,023x** (`elapsed_us`). Any
bound admitting those also admits the 4.3-million-fold error this item
is named for, so the clause is **not** in the guard and this is the
second deviation. What replaced it is the pair that is decidable from
a value alone — a `count` is integral, a `share` is in 0..1 — and they
found the two defects above on their first two runs.

### Mutations verified red and reverted (7)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `378fada`.

| # | mutation | reddened |
|---|---|---|
| A1 | `signals.critical_path_length` published again, declared `count` | `test_the_chains_length_is_not_published_as_a_count` — *"golden: signals.critical_path_length is back, holding 14000"* |
| A2 | `structural.summary.critical_path_length` + 0.5 | `test_every_count_is_a_whole_number` on both — `('structural.summary.critical_path_length', 10.5)` |
| A3 | `wall_clock_share_us` declared `share` again on node and `additionalProperties` | `test_every_share_is_between_zero_and_one` on both |
| A4 | the grid clamp in `compute_confidence` removed | `test_every_share_is_between_zero_and_one[macro_micro]` — `1.0001793150166365` |
| A5 | clamp widened to the whole declared duration, with a doubled task stream | `test_every_share_is_between_zero_and_one[macro_micro]` — `2.000358630033273`: a doubling is not hidden by a slack of one declared duration |
| A6 | `format.js::hintsOf` returns `{}` | `test_the_walk_reached_the_document` — *"only 11 declared values found"* (golden), *"only 26"* (macro_micro) |
| A7 | `StructuralMetrics.critical_path_length = cp_length + 1` | `test_the_count_of_elements_on_the_chain_still_reads_as_one` — `('golden', 4, 3)` |

### The mutation that survived, and the clause it bought

A7 was first aimed at the *summary's* own copy
(`'critical_path_length': metrics.critical_path_length + 1`) and
**nothing reddened**: `structural.summary` quotes three numbers from
`structural.metrics`, both sites declare `count` truthfully, and an
integral count that disagrees with the integral count it copies is
invisible to a value-versus-declaration check. Rather than count a
mutation that discriminated nothing,
`test_the_summary_repeats_the_metrics_it_quotes` was added — the cheap
half of `UX-288`'s rule for the three quoted keys — and the same
mutation then reddened on both fixtures.

### Verification

```text
make lint                     pymarkdown + ruff, all checks passed
make test                     4365 passed, 21 skipped
guard                         10 passed
golden fixture regenerated    2 lines: the removed key, and the rename
```

Two failures on this branch that predated the item were repaired in the
same commit, because they were the same round's debt: `UX-341` rewrote
`docs/design/architecture.md`'s contracts table without re-grounding
its Verification Log, and four Out of Scope entries round 52 filed
stated their reason in a shape `test_every_out_of_scope_entry_names_a_task_or_states_a_decline`
does not read.
