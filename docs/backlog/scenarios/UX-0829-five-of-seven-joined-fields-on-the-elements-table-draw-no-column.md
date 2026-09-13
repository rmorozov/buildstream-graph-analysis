# UX-829: five of seven joined fields on the elements table draw no column

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-681 (fan-in joined), UX-382 (the join), UX-808 (§1b's last instance) | **Found by:** round 115, the design review | **Serves:** R2 and R3 reading one element's row | **Topic:** viewer | **Area:** bga-viewer | **Shape:** judgement

## Motivation

`structured.js:1457` marks the `elements` table `data-joined` with what
it merged; the rendered headers are what it drew:

```text
data-joined   element_durations, slack, downstream_count, unweighted_depth, blast_radius, fan_in, criticality_probability
th            element · Element durations · Downstream count · Is leaf · Element kind · Observed critical
no column     fan_in · slack · blast_radius · unweighted_depth · criticality_probability   (5 of 7)
```

§1b: every published field reaches a reader or the page names the
ones that do not. `UX-681` joined `fan_in` for this table and the
reader still meets fan-in only as "Top fan in: storm.bst" in a `dt`.
The owner's ask for a per-element incoming-dependency list is the same
gap one level down: `fan_in[uid]` carries counts and the dominator,
never the names.

## Required Fix

Every `data-joined` field gets a header, the five beyond the width
budget behind a "more columns" disclosure (§3a's depth budget, one
level); `fan_in[uid]` gains `direct` — the incoming names, capped at
the row cap — drawn in the element card, not the table (§3c: forty
names is a cell no row survives). The section's lead sentence names
any field drawn elsewhere.

## Decomposition

Input classes: an element with 0, 4 and 1,004 direct dependencies
(scale), a leaf, and the golden fixture's eleven; the journey is R2's
"what does my element wait on" in the answer key.

## Out of Scope

- Transitive fan-in as a list — the closure of 1,004 names is the JSON door's.
- The bottleneck's own ranking — `UX-719`.

## Acceptance Test

On the scale export `th[data-column]` covers every `data-joined` field
or the lead sentence names the rest; the element card lists direct
fan-in; mutation: drop a header — `test_the_merge_carries_every_field.py`
extended to this table reds.
