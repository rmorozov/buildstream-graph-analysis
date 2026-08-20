# UX-171: blast radius by shared source — the monorepo question

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** Direction 6 (the argument), UX-168 (`read_element_yaml`, the reader this reuses)

## Motivation

Filed from the real user's request, round 18: in a monorepo consumed
through BuildStream, one repository populates the sources of many
elements — and no analysis answers *"this repo was touched: how many
recipes rebuild, and at what cost?"* Every blast question today starts
at an element (`compute_downstream_count`, `bga/graph/edg.py:281`);
the user's question starts at a **resource**.

The mechanism (Direction 6 argues it in full): a `git` source keys on
its **ref** — N elements sourcing one url with different `directory:`
values all rebuild on any commit to that repository, regardless of
which paths changed. A `local` source keys on **content** — only the
elements whose staged directories contain the touched files rebuild.
The same monorepo consumed two ways has order-of-magnitude different
blast, the `.bst` files encode which way, and everything needed to
compute it is already on disk: `read_element_yaml` parses `sources`
stanzas (census), `graph.json` carries the typed dependency edges and
`element_kind`, and the run directory carries measured durations.

## Required Fix

1. **A source inventory**: per element, its resources as
   `(kind, identity)` — `git`/`git_repo`-family → url (normalized),
   `local` → project-relative path, `tar`/`remote` → url, junctions →
   junction name. Offline, from element YAML, same reader as the
   census. Unparseable stanzas are counted and named, not skipped
   silently (the UX-160 lesson).
2. **The resource blast table** in the analyze report (and its JSON):
   for each resource shared by ≥2 elements — sorted by measured blast
   cost — the direct elements, the union of their downstream closures,
   the counts **by element kind**, the measured rebuild time when a
   run is present (sum of blast elements' durations from `trace.json`;
   "unmeasured" honestly otherwise), and one clause naming the keying
   semantics: "keys on ref: any commit rebuilds all of this" vs "keys
   on content: per-directory".
3. **The monorepo headline**: when one git url's blast covers ≥X% of
   the graph (threshold with provenance, like every gate), the Key
   Findings block says so in one sentence with the measured hours.

## Out of Scope

- The query command (`UX-172`), the kind-weighting of the *existing*
  element blast (`UX-173`), the patterns docs (`UX-174`).
- Tracking-time analysis (what `bst track` would bump — this reads
  declared sources, not remote state).

## Acceptance Test

On a copy of `examples/06` where lib-a..lib-f's sources are rewritten
to one shared `git` url with per-element `directory:` (fixture, no
network — the inventory reads YAML, not the remote): the report's
resource table shows that url with 6 direct elements, the closure
count, the kind breakdown, and "keys on ref"; the same copy with
`local` per-directory sources shows per-element blast and "keys on
content". On the unmodified example (no shared resource) the section
says nothing (silent when there is nothing to say). Measured cost
matches the sum of the named elements' trace durations on a real run.
