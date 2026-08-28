# UX-345: the chain's length is a duration wearing a count's declaration

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-341 (one unit per dimension), UX-201 (the schema says what things are) | **Serves:** anyone reading the signals block, and every consumer of `analyze/v3` | **Topic:** contracts

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
