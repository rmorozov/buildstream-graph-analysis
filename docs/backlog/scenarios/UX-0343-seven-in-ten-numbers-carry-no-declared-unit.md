# UX-343: half the numbers carry no unit at all

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-201 (the rule this is the gap in), UX-341 (which reduces the vocabulary those declarations use) | **Serves:** every payload consumer, and the viewer's own fallback | **Topic:** contracts

## Motivation

`UX-201`'s rule is *declared beats guessed*, and `quantityFor` still
guesses whenever the schema says nothing — name-sniffing `guessQuantity(key)`
and, under `BGA_STRICT_HINTS`, complaining to the console.

**The figure this item was filed with was wrong, and the correction is
the more interesting number.** It was measured by re-implementing the
page's resolution in Python, which got it wrong twice — first by
missing the `bga:columns` channel entirely (81%), then by
mis-inheriting it (71%). Measured through the page's *own* resolution,
in Node, and separating a **declaration** from `guessQuantity`'s
**guess** — which `quantityFor` conflates, because it returns
`declared ?? guessed`:

```text
counting leaf occurrences      declared   guessed   neither
golden                           29%        20%       51%
macro_micro                      32%        21%       48%

counting distinct paths        declared   guessed   neither
golden           (169 paths)      26%        24%       49%
macro_micro      (350 paths)      24%        20%       55%
```

Both countings are in the Outcome's terms below, which uses distinct
paths: a leaf that appears once per element counts once, so the figure
does not move with the size of the build.

So the sharper finding is not that seven in ten are undeclared. It is
that roughly **half of every number in the report reached the reader
with no unit at all** — not even a guessed one — while a fifth rendered
correctly only because a suffix happened to be recognised.

The gaps are not scattered. They are three shapes:

**1. Bare number arrays, and arrays of tuples.**

```text
10x  structural.parallelism.levels.[]
10x  structural.parallelism.width_at_level.[]
10x  structural.sensitivity.top_opportunities.[].[]
```

`top_opportunities` is a list of *lists* — positional pairs with no
field names at all, which is the one shape a schema-driven renderer
cannot say anything about and a consumer has to read the source to
decode.

**2. Fields nobody declared.**

```text
11x  element_join.[].redundancy_count
 9x  element_join.[].dominant_binary.count
 9x  element_join.[].dominant_binary.cpu_share
 9x  structural.bottleneck.choke_points.[].downstream_count
```

Each has an obvious quantity — `count`, `count`, `share`, `count` — and
each currently renders because `guessQuantity` recognises the suffix.
That is the schema gap `UX-201` says the guess exists to *reveal*.

**3. A genuinely polymorphic value.**

```text
24x  findings.[].provenance.evidence.[].value
```

`UX-229`'s provenance rows carry *whatever field the rule read*, so one
static declaration cannot be right. The value's unit is knowable —
`path` names the field it came from — but it has to travel with the row
rather than with the schema node.

**The second declaration channel is part of why this went unnoticed.**
A quantity is declared either as `bga:quantity` on a schema node **or**
as `quantity` inside a `bga:columns` v2 entry — 165 and 36 of the 201
declarations respectively, under two different key names. The first cut
of the census above read only `bga:quantity` and reported 81%; the
correction is in the numbers above, and a reviewer eyeballing
`schemas.py` for coverage has the same trap in front of them.

## Required Fix

Every numeric leaf a published document can emit carries a declared
quantity, by one of three routes: on the node, in the column spec, or —
for `provenance.evidence[].value` — as a `quantity` field on the row
itself, resolved from the `path` it names.

`structural.sensitivity.top_opportunities` becomes a list of objects
with named fields, like every other table in the document.

A guard walks the committed fixtures' real payloads (not the schema
alone, which cannot see which keys a run actually emits) and fails on
any numeric leaf with no declaration, with a declared allowlist for the
handful that are genuinely dimensionless.

## Out of Scope

- Removing `guessQuantity`. It is the fallback that makes an
  undeclared field render *something*, and `UX-201` argues for keeping
  it as a complaint rather than a crutch. This item empties its input;
  it does not delete it.
- The two-channel declaration itself. Columns declaring their own
  quantity is `UX-201`'s v2 column spec working as designed; what this
  item asks for is that a census can read both, which the guard does by
  construction.

## Acceptance Test

On both committed fixtures, every numeric leaf of the emitted
`analyze/v2` document resolves to a declared quantity through either
channel, or appears in an allowlist whose every entry carries a reason.
`top_opportunities` rows are objects with named keys, and the viewer
renders the same section list as before. Running with
`BGA_STRICT_HINTS` set produces **no** `has no bga:quantity` console
warning on either fixture — asserted through the console reader
`UX-334` built, not by eye.

## Outcome (round 52, 2026-08-28) — 🟢 Done

### The gap, measured

The census below resolves each numeric leaf of the emitted `analyze/v2`
document the way the page will — in Node, against `tests/viewer.mjs`,
reading a **declaration** apart from `guessQuantity`'s **guess**. Run
against `8f81f7f`, the tree this item was filed on, and counting
distinct paths rather than leaf occurrences:

```text
golden       paths  169   declared   44 (26%)   guessed  41 (24%)   neither  84 (49%)
macro_micro  paths  350   declared   84 (24%)   guessed  71 (20%)   neither 195 (55%)
```

Half of every number the report published reached the reader with **no
unit at all** — not even a guessed one — while a fifth rendered
correctly only because a suffix happened to be recognised.

### After

```text
golden       paths  170   declared  167 (98%)   guessed   0 ( 0%)   neither   3 ( 1%)
macro_micro  paths  351   declared  348 (99%)   guessed   0 ( 0%)   neither   3 ( 0%)
```

The three remaining are one path each — `rule.threshold` in its plain
and banded forms, and the diagnosis chain's own — allowlisted in
`UNDECLARABLE` with the reason they cannot resolve: a rule whose
`observed_path` is null compares against a quantity the finding
computes rather than publishes, so no path names its unit.

The contract now carries 356 `bga:quantity` declarations on nodes and
44 in v2 column specs, in 107,657 bytes across the eight schemas.

### Why the census had to run in the page, not beside it

Two earlier passes re-implemented the resolution in Python and were
wrong twice — once by missing the `bga:columns` channel entirely (81%
undeclared), once by mis-inheriting it (71%). **The figure this item
was filed with was one of those**, and it is corrected above. A
declaration arrives by one of two key names, `bga:quantity` on a node
or a plain `quantity` inside a column spec, and `quantityFor` returns
`declared ?? guessed`, so a guess counted as a declaration until the
two were read apart. Nothing short of the page's own `hintsOf` and
`childNode` gets this right.

Three shapes had to change for the numbers above:

* **Maps keyed by data.** An element uid or a resource name cannot be
  named in `properties`, so seven maps in `signals` alone had nowhere
  to say what their values were. `childNode` now descends
  `additionalProperties`, and each map declares its value's schema once.
* **Positional tuples.** `structural.sensitivity.top_opportunities` and
  the two `bottleneck` fan lists published arrays of arrays, which is
  the one shape a schema-driven renderer can say nothing about. They
  are rows with named keys now — and `top_opportunities` gained the
  `saving_us` its declared third column had been promising since
  `UX-290`.
* **A polymorphic value.** `provenance.evidence[].value` carries
  whatever field the rule read, so the unit travels with the row:
  `quantity_for_path` resolves it from the `path` the row already
  names, and the row carries the answer. The resolver **scans** the
  path rather than splitting it on `.`, because an element uid inside a
  subscript contains one.

### The guard found ten more that the payload could not see

The acceptance test asked for the `BGA_STRICT_HINTS` reading to come
from `UX-334`'s console reader. The first cut asserted it inside the
Node census instead — against a variable nothing there could ever
write to, because the census reads `hintsOf`/`guessQuantity` directly
and never calls `quantityFor`. A clause that cannot fail.

Moved to where it belongs (`tests/cdp.mjs` sets the flag before the
document exists; the console guard fails on any `has no bga:quantity`
warning across its four boots) it reddened immediately, on ten keys the
payload census called declared:

* Three columns of the **merged element table** resolved their unit
  against the `signals` node while the declaration lives where the
  field came *from* — `weighted_duration_us` on `signals.blast_radius`'s
  value schema, `slack_us` on `element_join`'s item. The report's
  central table was rendering them from a name-sniff. It remembers each
  merged field's origin node now.
* Eight `attribution_hints` members are *sentences* keyed by the metric
  they explain, and `renderPairs` asked `quantityFor` about every
  member regardless of type — eight complaints per boot about units no
  number needs. It asks only of a number now.

### Mutations verified red and reverted (8)

Counts are what the run printed, not what was expected of it. All eight
ran against the committed tree.

| # | mutation | reddened |
|---|---|---|
| D1 | `childNode` forgets `additionalProperties` — the map shape this item was filed for | guessed 18 (golden) / 33 (macro_micro); neither 35 / 78 — `signals.blast_radius.*`, `element_durations`, `slack`, `downstream_count`, `unweighted_depth`, `criticality_probability`, `wall_clock_share`, `occupancy.*` |
| D2 | both channels drop `element_join.peak_rss_kb`'s unit | 2 clauses: `neither: ['element_join.[].peak_rss_kb']` and the resolver case `element_join[0].peak_rss_kb`. Removing **only** the column spec's `quantity` left 21 passed — the node channel carries it, which is the two-channel reading working |
| D3 | `_path_segments` splits on `.` before reading subscripts | 3 cases, exactly the bracketed element uids: `signals.element_durations[app.bst]`, `signals.blast_radius[app.bst].risk_score`, `signals.criticality_probability[lib.bst].probability` |
| D4 | provenance rows stop carrying their resolved `quantity` | `neither: ['findings.[].provenance.evidence.[].value', 'headline.provenance.evidence.[].value']`, both fixtures |
| D5 | `top_opportunities` back to positional tuples | 4 clauses: `neither: ['structural.sensitivity.top_opportunities.[].[]']` on both fixtures, the producer clause (`still publishes a positional tuple: ['core.bst', 0.278...]`), and the declared-columns clause |
| E1 | the merged element table resolves columns against `signals` again | console guard, on the two it was found by: `slack_us`, `weighted_duration_us` |
| E2 | `renderPairs` asks `quantityFor` about every member, not only numbers | console guard, on the eight `attribution_hints` keys |
| E5 | `signals.blast_radius` drops `weighted_duration_us`'s unit | **both** instruments: console guard on `weighted_duration_us`, census on 4 (golden) / 11 (macro_micro) leaves |

One mutation was **rejected rather than counted**: removing
`signals.blast_radius`'s `downstream_count` unit left the console guard
green, because `downstream_count` is *also* a top-level element-keyed
signal and the merged table takes its origin from whichever contributes
the field first — a legitimately declared sibling masked it. The census
caught it (`1 failed`); the console clause did not, and saying so is
the point of running it. The same asymmetry runs the other way, which
is why both instruments stay: dropping the unit on the **findings
evidence** copy of `blast_radius.weighted_duration_us` reddens the
census on three leaves and leaves the console green, because no boot
renders that copy through the merged table.

Full unit suite after the fix: **4,320 passed, 19 skipped** in 165s.
`make lint` (pymarkdown + ruff) clean.

### Deviation from the Required Fix

- The Acceptance Test's strict-hints clause was written into the wrong
  instrument first, as described above. It is now where the item asked
  for it, and the correction found two real defects — so the deviation
  is recorded as a defect in the guard, not a change of plan.
- `rule.threshold` on a rule with a null `observed_path` stays
  undeclarable. The Required Fix's "every numeric leaf" is met by the
  allowlist clause it also asked for: three entries, each with its
  reason, and `TestTheAllowlistIsNotAGraveyard` fails if one of them
  ever starts resolving.
- Nothing else. `top_opportunities` became named rows, the viewer
  renders the same section list, and `BGA_STRICT_HINTS` produces no
  `has no bga:quantity` warning on either fixture in either shape.
