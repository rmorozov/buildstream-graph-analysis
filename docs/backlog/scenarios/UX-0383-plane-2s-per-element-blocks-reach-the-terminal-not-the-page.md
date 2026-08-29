# UX-383: Plane 2's per-element blocks reach the terminal, not the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-370 (Plane 2's frequency and time reach the page), UX-379 (the third block) | **Serves:** anyone reading the report in a browser | **Topic:** viewer

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
