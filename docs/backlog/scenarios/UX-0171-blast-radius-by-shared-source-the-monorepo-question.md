# UX-171: blast radius by shared source — the monorepo question

**Priority:** High | **Status:** 🟢 Done | **Depends on:** Direction 6 (the argument), UX-168 (`read_element_yaml`, the reader this reuses) | **Topic:** analysis

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

## What was built

**`bga/sources.py`** — the whole of the semantics, as pure functions
over data somebody else parsed. A `KEYING_BY_KIND` map that says which
kinds key on a **ref** (`git`, `tar`, `pip`, …) and which on **content**
(`local`, `patch`), with anything absent reported as `unknown` rather
than assumed either way; `normalize_url`, so
`git@host:org/repo.git` and `https://host/org/repo/` are one identity
and a blast is not halved by two spellings of one repository;
`resource_blast`, which unions the direct elements' downstream closures
and counts the result by element kind; and `monorepo_headline`.

**The inventory is written at extract time.** `bga extract` now writes
`sources.json` (`sources/v1`) beside `graph.json`, read from the `.bst`
files with the census's own memoised YAML reader. Written there because
that is the one moment the project and the run are both in hand:
`bga analyze` reads a run directory and nothing else, which is what
makes a published capture analyzable anywhere, and adding a
`--project` flag to analyze would have traded that away.

**The table and the headline.** A `Shared Sources` section in the text
report and a `resource_blast` key in the JSON, both from the same rows;
the headline is a finding (`shared-source-blast`) so it appears in Key
Findings and in `findings[]` together, and cannot say different things
in the two renderers.

Silence is the default in three cases, all of them real: a run captured
before this existed, a project whose sources are per-element `local`
paths, and a resource only one element uses. An empty table would
suggest the question had been asked and answered.

### Measured on a real capture

`examples/01-resource-contention`, captured with `bga snapshot -- bst
--builders 4 build all.bst` on this machine, then re-run with its eight
`work-*.bst` elements rewritten to source one url with eight different
`directory:` values:

```text
resource: gitlab.example.com/org/monorepo | direct 8 | blast 9 | kinds {'manual': 8, 'stack': 1}
staged at: ['src/work-a', 'src/work-b', ..., 'src/work-h']
keying: keys on ref: any commit to this rebuilds all of them, whatever each one stages
reported cost: 22.544 s
sum of those elements' real trace durations: 22.544 s
MATCH
headline: One repository decides most of this build: any commit to
gitlab.example.com/org/monorepo rebuilds 9 of 10 elements (90%, 23s of
measured build work), because its 8 direct elements key on its ref
rather than on the files they stage.
```

The unmodified project produced `sources.json` with one element and one
`local` source, and no table - which is the acceptance's "silent when
there is nothing to say", from the real path rather than a fixture.

Two things that first live run corrected:

- The headline said **"0.0h of measured build time"** about a 22-second
  build. Units are chosen from the number now (`format_work`), and the
  cost is called *work* rather than time, because summing per-element
  durations across a blast set is serial work and any parallelism
  completes it in less. The report says so under the table.
- The kind breakdown came back `8 manual, 1 stack`, which is `UX-173`'s
  point arriving on its own: a blast of 9 where one is a stack is not a
  blast of 9 things that build.

### Guards

`tests/unit/test_shared_source_blast.py`, 20 of them. Six mutations,
each red: `git` keyed as content; url spellings left unnormalised;
unreadable stanzas dropped silently; the report never reading the
inventory; `extract` not writing it; and `unmeasured` rendered as `0s`.

The fifth is worth its own note. The first version of that mutation
**passed** - every other test built the inventory directly and handed
it to the report, so the producer could have been deleted entirely and
nothing would have noticed. The `bst`-marked end-to-end test exists
because the mutation found that hole, not because the plan called for
it.
