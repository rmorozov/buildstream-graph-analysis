# UX-341: one unit per dimension

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-201 (the schema says what things are), UX-215 (which added `kilobytes` deliberately) | **Serves:** every payload consumer, and the reader comparing two numbers | **Topic:** contracts

## Motivation

`QUANTITIES` has nine members and three of the dimensions it covers are
spelled more than one way. Counted over all eight published schemas,
reading **both** declaration channels (`bga:quantity` on a node, and
`quantity` inside a `bga:columns` entry — 165 and 36 respectively):

```text
count          68        share          35        percent         5
duration_us    62        ratio          11        megabytes       4
                         kilobytes       6        seconds         4
                         bytes           6
```

Three dimensions, each with a dominant spelling and a small tail:

**Time — 62 `duration_us` against 3 `seconds`,** and all three seconds
are a *lossy downgrade of a value the tool already holds as an
integer*:

```text
bga/blast.py:289   durations = {uid: micros / 1e6 for uid, micros
                                in compute_element_durations(...).items()}

analyze/v2   findings.[].evidence.measured_seconds
blast/v1     measured_seconds
blast/v1     blast_tree.[].measured_seconds
```

**Fraction — 35 `share` (0..1) against 5 `percent` (0..100):**

```text
analyze/v2   utilisation.idle_pct, useful_pct, wasted_pct,
             reconciliation_error_pct
compare/v1   deltas.efficiency_pct
```

`percent` exists because `UX-201` found the viewer multiplying an
already-percentage value by 100 and printing `4200.0%`. That is an
argument for *declaring* the unit, not for keeping two of them: a
consumer that wants to compare `useful_pct` with `cpu_coverage` has to
know which of the two conventions each was written under.

**Memory — 6 `bytes` against 4 `megabytes` and 3 `kilobytes`,** and
here too the tail is derived from the head:

```text
bga/correlate.py:953   profile["peak_rss_mb"] = max(peaks) / 1024
```

`peak_rss_kb` arrives from Plane 2 as `ru_maxrss`, which is KiB, so
`× 1024` to bytes is exact and integral; `peak_rss_mb` is a float that
exists only to be printed.

**Two leaf names carry two different quantities:**

```text
cores_busy        count  analyze/v2  capacity_recommendation.cores_busy
                  ratio  analyze/v2  element_join.[].cores_busy
                  ratio  analyze/v2  findings.[].evidence.cores_busy
                  ratio  correlate/v1 elements.[].cores_busy, actionable.[]…

efficiency_score  ratio  analyze/v2  floors.efficiency_score
                  share  analyze/v2  findings.[].evidence.efficiency_score
```

The first is defensible — a recommended core count *is* a count — but
it means the same name means two things in one document. The second is
a straight disagreement: one number, two declared units.

**And five keys named `_ratio` are declared `share`:**

```text
headline.chain_ratio, headline.chain_bound_ratio, floors.occupancy_ratio,
findings.[].evidence.hit_ratio, findings.[].evidence.target_closure_hit_ratio
```

while `compare/v1 deltas.inefficiency_ratio` really is a `ratio`. The
name and the vocabulary disagree, and the name is what a consumer
grepping the payload sees first.

## Required Fix

One unit per dimension in the payload: **µs for time, bytes for memory,
0..1 for a bounded fraction.** The remaining `ratio` keeps its meaning —
unbounded multiplier — and the keys that are really shares are renamed
so the suffix and the declaration agree.

This is a contract change, so it is versioned, not edited: the new
spellings land as `analyze/v3`, `blast/v2`, `compare/v2`, `correlate/v2`
with the old ids still readable, and the affected keys are renamed with
their unit (`measured_us`, `useful_share`, `peak_rss_bytes`,
`envelope_bytes`, `chain_share`, …) rather than keeping a name that says
one thing and a declaration that says another.

`QUANTITIES` then drops `seconds`, `percent`, `megabytes` and
`kilobytes`, and a guard asserts the vocabulary has no two members
measuring one dimension — which is the property, rather than a list of
four names a later round would re-add.

## Out of Scope

- The **rendering**. `duration_us` already prints as `400 ms` / `4.2 h`
  and `share` as a percentage; a reader sees no change. This is about
  what the document says, not what the page shows.
- The trace and the Plane 2 record, which are not `bga:`-hinted
  documents and have their own conventions (`UX-343` covers what that
  costs).

## Acceptance Test

Every declared quantity in every published schema is one of the reduced
vocabulary, asserted by walking both declaration channels. No leaf name
in the inventory carries two different quantities. No key whose name
ends `_us`/`_bytes`/`_share`/`_ratio` is declared as something else.
The golden snapshot's numbers are the same values in the new units —
`measured_us == round(measured_seconds * 1e6)` on the committed fixture,
asserted rather than assumed.
