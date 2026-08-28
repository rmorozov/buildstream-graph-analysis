# UX-341: one unit per dimension

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-201 (the schema says what things are), UX-215 (which added `kilobytes` deliberately) | **Serves:** every payload consumer, and the reader comparing two numbers | **Topic:** contracts

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

## Outcome (round 52, 2026-08-28) — 🟢 Done

### The gap, measured

Counted over all eight published schemas, reading both declaration
channels. The left column is the tree this item was filed on; the right
is after (`UX-343` grew the declaration count in between, which is why
the totals differ):

```text
before                          after
count          153              count        153
duration_us    122              duration_us  145
share           61              share         69
ratio           22              ratio         22
seconds         20
kilobytes        6
bytes            6              bytes         17
megabytes        5
percent          5
```

Three leaf names carried two different quantities — `cores_busy`
(`count` on the capacity recommendation, `ratio` on the four
element-level copies of the same measurement), `efficiency_score`
(`ratio` on the floor, `share` in the finding that quotes it) and
`change` (a signed count of builders in one place, a share of a
baseline in another). Seven keys ended `_ratio` and were declared
`share`. All of it is empty now:

```text
=== leaf names carrying more than one quantity ===
<nothing, other than the generic distribution statistics the guard
 excludes by name: `min`, `max`, `p95`, a decile - whose dimension is
 the parent's>
```

### The conversions live at the boundary, not in the readers

Every retired spelling was derived from its own head, usually by a
lossy division of a value the tool already held as an integer:

```text
bga/blast.py:289    micros / 1e6        an int, made a float, to be printed
bga/correlate.py    peak_rss_kb / 1024  KiB, exact, made a float of MB
bga/cli.py:111      micros / 1e6        again, for the resource blast
```

So `bga/units.py` is new, and it is the only place a conversion
happens: `run-context.json` records the host's RAM in MB and Plane 2's
record reports `ru_maxrss` in KiB. Neither is one of this tool's
documents — both are inputs with their own conventions — and neither is
rewritten by this item. Everything downstream of those two functions is
in the payload's units, and the terminal still prints GB and seconds
because presentation is not the contract.

### The version moved, and the old ids stay readable

A rename is a removal, so `analyze/v3`, `compare/v2`, `blast/v2`,
`correlate/v2` and `host/v2`. The five predecessors are declared
`SUPERSEDED` — read, never written — which is `UX-297`'s existing state
for `plane2/v1`, applied five more times. `host/v1`'s `memory_mb` is
converted where it is *read*, in `hostinfo.normalised`, for the reason
`classify`'s own docstring gives: a tool that refused every capture
older than itself would be telling users to throw away the baselines
they came with. Measured: the committed `macro_micro` run carries a
`host/v1` manifest, and without that normalisation it put a megabyte
figure into a document that says everywhere else it is bytes — found by
`UX-343`'s census, not by review.

### After

```text
golden       paths  170   declared  167 (98%)   guessed   0 ( 0%)   neither   3 ( 1%)
macro_micro  paths  351   declared  348 (99%)   guessed   0 ( 0%)   neither   3 ( 0%)
```

`UX-343`'s census is unchanged by the rename, which is the point: the
declarations moved with their keys rather than being left behind.

Full unit suite: **4,325 passed, 19 skipped** in 154s. `tests/test_golden.py`
regenerated and green. `make lint` clean.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| F1 | `seconds` returns to `QUANTITIES` and `DIMENSIONS` | `these dimensions have more than one spelling: {'time': ['duration_us', 'seconds']}` |
| F2 | a schema declares `measured_us` as `seconds` | `analyze/v3.findings[].evidence.measured_us: bga:quantity='seconds' is not one of duration_us, bytes, share, count, ratio` — `UX-201`'s own check, which is where this belongs |
| F3 | `capacity_recommendation.cores_busy` goes back to `count` | the two-units clause, naming all five sites |
| F4 | `occupancy_share` goes back to `occupancy_ratio` | `{'occupancy_ratio': ('ratio', ['share'])}` — the name promises one unit and the declaration says another |
| F5 | `s_to_us` returns the float of seconds it was given | `a µs figure converted from seconds is an integer count, not a float of seconds under a new name` |
| F6 | `kb_to_bytes` rounds through whole megabytes | `AssertionError: core.bst` — the published byte figure is no longer the record's own number times 1024 |

**F6 was rejected twice before it discriminated**, and the repair is
the more useful half. The first attempt (`value / 1024 * MIB`) is
`value * 1024` exactly — not a mutation at all. The second
(`int(int(value) / 1024 * MIB)`) is also exact for an integer input.
Both passed, and so did a third that genuinely *was* lossy, because the
clause asserted the published figure was a whole number of KiB — which
every wrong conversion it was meant to catch also is. The clause now
reads the Plane 2 record beside the fixture and asserts the published
figure is that record's own number times 1024, and fails if it found
nothing to compare.

### Deviation from the Required Fix

- **The Acceptance Test's "no leaf name carries two different
  quantities" needed a scope.** `UX-343` published two distributions in
  the interval between filing and fixing — `element_duration_distribution`
  (durations) and `blast_radius_distribution` (counts) — so `min`,
  `max`, `p95` and the nine deciles each legitimately carry two
  quantities, qualified by the block above them rather than by their
  own name. The guard excludes generic statistic names by pattern and
  says why; the clause is otherwise as filed.
- **`attribution_deltas` was widened into scope.** It is the block
  `compare` publishes per attribution category, it was declared
  *nothing at all*, and three of its six members were 0..100 while
  every other bounded fraction in the payload is 0..1. Leaving it would
  have meant `compare/v2` still mixed conventions, so it is declared,
  and `baseline_pct`/`candidate_pct`/`delta_pct_points` are
  `baseline_share`/`candidate_share`/`delta_share`.
- **`0.3.0`'s changelog row records the movement rather than a new
  release row.** The release-state guard requires the newest row to be
  a true claim about this tree, and cutting `0.4.0` would need a
  documentation review at or after `0.3.0`'s closed-row marker (332);
  the review log's highest is 318, so a new row would assert a review
  that has not happened. `0.3.0` is untagged and unreleased, so its
  state block and contract delta are corrected in place and its kind
  moves from `extending` to `breaking`.
- **The renderer keeps the four retired spellings.** `QUANTITIES` is
  the vocabulary a schema may *declare*; `bga/viewer/format.js` still
  renders `percent`, `megabytes`, `kilobytes` and `seconds` correctly
  if a value arrives carrying one. Deleting five lines to make a point
  would only make an external consumer's payload render worse.
- Nothing else. `guessQuantity` is untouched, as the Out of Scope
  section asks, and the page shows the same figures — the µs and bytes
  are formatted by the same functions that formatted the seconds and
  megabytes.
