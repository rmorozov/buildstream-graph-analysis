# UX-383: Plane 2's per-element blocks reach the terminal, not the page

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-370 (Plane 2's frequency and time reach the page), UX-379 (the third block) | **Serves:** anyone reading the report in a browser | **Topic:** viewer

## Motivation

`UX-370` moved `by_binary`, `binary_cost` and `configure_phase` into
`analyze/v4` so the page could render what Plane 2 measured. Three
per-element blocks were left where they were, and a fourth has just
joined them:

```text
plane2/v2 block        rendered in the terminal   in ANALYZE_PLANE2_KEYS
binary_cost                    yes                        yes
configure_phase                yes                        yes
cpu_time                       yes                         no
peak_memory                    yes                         no
resource_pressure              yes                         no   (UX-379)
```

Measured on a 10-element capture: `cpu_time` is 2,499 bytes of
`plane2.json` and `peak_memory` 1,093, and neither key appears anywhere
in `analyze --format json`. So "was this element CPU-bound", "how much
memory did its largest process need" and "did it read from disk or get
preempted" are answerable at a terminal and not in the report a reader
opens in a browser — which is the split `UX-329` closed for coverage
and `UX-370` for cost.

`resource_pressure` is filed here rather than widened into `UX-379`
because the gap is older than it and identical for all three.

## Required Fix

The three blocks join `ANALYZE_PLANE2_KEYS` and the page renders them
on the terms the existing Plane 2 sections already use — a population
with a share is `UX-303`'s strip and `UX-289`'s preset table, and each
block's own `note` is `UX-346`'s door.

Two of them carry a rule the rendering must not lose: `peak_memory` is
a per-process maximum that must never be summed, and
`resource_pressure` is the opposite — sums that may be. A single
"Plane 2 per element" table that mixed them would state the wrong thing
about one column.

## Falsification

`UX-356`'s clause, pointed at these three: every scalar under
`cpu_time`, `peak_memory` and `resource_pressure` reaches a rendered
node or is named in a redirect sentence that says why not. It fails
today on all of them.

## Out of Scope

- Producing a finding from any of it. Rendering a measurement and
  concluding something from it are different items, and this repository
  has been bitten before by a finding that shipped ahead of the number
  it rests on.
- `plane2/v2`'s own shape. The blocks are published correctly; what is
  missing is the copy into `analyze/v4` and the section that draws them.

## Outcome (round 62, 2026-08-29) — 🟢 Done

### The gap, measured

The three blocks are in `ANALYZE_PLANE2_KEYS` and reach the page. The
per-element halves land on the `element_join` row, not in tables of
their own — which is where the shape of this fix was decided for it.

### After

The join row gained five fields; the run-level totals and each block's
own `note` are published beside it:

```text
element_join row     cores_busy  cpu_coverage  peak_rss_bytes   (before)
                   + cpu_us  read_bytes  written_bytes
                   + major_faults  involuntary_switches         (after)

analyze/v4         + cpu_time          total, measured, spine-sourced
                   + peak_memory       the note, and no total on purpose
                   + resource_pressure coverage, and the note
```

**The first draft wrote three per-element tables and was wrong.**
`test_one_table_many_views.py` caught it: `element_cpu_time`,
`element_peak_memory` and `binary_cost` drew the same nine elements —
`UX-288`'s one-population rule. The right shape was already written
down as `UX-382`'s placement rule, which round 61 landed: *an attribute
that needs Plane 2 to exist is a field on an `element_join` row*. Three
tables became five fields, and the rule that caught it is the rule that
says where they go.

**The summing rule survives the rendering**, which is the item's one
hard constraint. `peak_rss_bytes` is a per-process maximum and the four
pressure counters beside it are sums; each says which it is in its own
schema sentence, and three clauses hold that the two prose forms are a
distinction rather than a rename.

The export bound moved, split as the convention requires — the **page
half is 269,212 B either side**, so nothing was added to the source:

```text
             data before   data after   delta
golden            92,359       95,607   +3,248   all contract
macro_micro      143,131      148,438   +5,307   3,248 contract
                                                 2,059 this run's own
```

### Falsification

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | the three keys leave `ANALYZE_PLANE2_KEYS` — the defect | 3 of 32 |
| M2 | the run-level blocks are not copied into `analyze` | 1 of 32 |
| M3 | `cpu_us` never reaches the join row | 1 of 32 |
| M4 | the four pressure counters never reach the join row | 4 of 32 |
| M5 | the peak's sentence loses its never-sum warning | 1 of 32 |
| M6 | a sum's sentence stops saying it is one | 1 of 32 |
| M7 | `per_element` is projected too, doubling the population | 1 of 32 |
| M8 | a counter the capture lacks is written as zero | 1 of 32 |

Baseline: 32 passed. `make lint` clean; `make test-fast` 4,592 passed.

**M4 reddened nothing on its first run and M8 reddened nothing on its
first two.** The committed fixture predates `UX-379`, so it has no
`resource_pressure` at all and every clause touching those four fields
passed whether the code carried them or not. The join is now driven
directly with a report that has the block — including one element
measured only partly, which is what makes M8 discriminate. Until a
fixture is recaptured that is the only thing checking this path.

### Deviation from the Required Fix

- **"The three blocks join `ANALYZE_PLANE2_KEYS`" is done; "the page
  renders them" is done differently.** The Required Fix asked for
  `UX-303`'s strip and `UX-289`'s preset table per block. That would
  have drawn one population four times. The per-element data is on the
  join row instead, which the one element table already presets over.
- **`peak_memory` was already half-published.** The filing's table says
  it reaches no reader; `element_join` has carried `peak_rss_bytes`
  since `UX-356`, and `cores_busy`/`cpu_coverage` carried two of
  `cpu_time`'s fields. What was genuinely absent is the CPU *quantity*
  and all four pressure counters — so the fix is smaller than the
  filing describes, and the measured gap is restated here rather than
  repeated from it.
