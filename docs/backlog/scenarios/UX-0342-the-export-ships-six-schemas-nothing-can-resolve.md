# UX-342: the export ships six schemas nothing can resolve

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-195 (the export), UX-307 (which removed the source commentary for the same reason), UX-201 (why the schema travels at all) | **Serves:** anyone who attaches a report to a ticket | **Topic:** viewer | **Area:** tools

## Motivation

An exported report embeds three JSON blocks. Measured on both committed
fixtures:

```text                          golden        macro_micro
page                          330,398 B      369,840 B
  bga-report                   17,891 B       57,246 B
  bga-run                         378 B          465 B
  bga-schemas                  83,669 B       83,669 B   <- identical
  module blob                 203,073 B      203,073 B
```

**On the golden export the schemas are 4.7× the data.** They are also
byte-identical between the two, because they are every schema the tool
publishes rather than the ones this page holds a document for.

The page resolves a schema in exactly two places:

```text
bga/viewer/app.js:814   render(payload, schemas[payload.schema], …)
bga/viewer/app.js:916   { store, schema: schemas[store?.schema] }
```

`payload.schema` is `analyze/v2`; `store.schema` is `store/v1`. The
other six are unreachable in an export — `blast/v1`, `compare/v1`,
`whatif/v1` and `sweep/v1` are answers the *server* computes on demand,
and there is no server:

```text
keep  analyze/v2 + store/v1        45,424 B
drop  store-aggregate/v1  13,293   correlate/v1  8,355
      compare/v1           5,342   blast/v1      3,047
      whatif/v1            2,631   sweep/v1      2,522
      ---------------------------------------------------
      total                       35,185 B   (44% of the block)
```

**Where the bytes are.** Broken down over the whole block:

```text
description prose      49,412 B   64.8%
bga: view-hints        16,241 B   21.3%
structure (keys)        8,862 B   11.6%
type, title, …          1,692 B    2.2%
```

So two thirds of the schemas block is English prose. That prose is not
dead — it is `UX-220`'s `?` marker beside a term, and in `analyze/v2`
**145 of 207 described keys are present in the golden report** and 196
of 207 in `macro_micro`. Description strings the page can attach to a
value it is drawing are earning their bytes. Descriptions belonging to
documents the page does not hold are not.

**And the prose repeats.** 358 description strings, 284 distinct;
duplicates cost **12,747 B beyond one copy each**. The worst is one
670-byte paragraph written ten times, twice over five sibling fields:

```text
store-aggregate/v1.host_classes.[].{duration_us,cache_hit_rate,cores_busy,
                                     peak_rss_mb,snapshot_bytes}
store-aggregate/v1.blended.{the same five}
```

## Required Fix

The export embeds the schemas its documents declare, and no others —
derived from the payloads being embedded, not from a list, so a page
that later embeds a `correlate/v1` document gets that schema with no
edit here. `bga view`'s **served** `schemas.json` keeps answering with
all of them: it is a published API and a byte there costs nothing.

Repeated description prose is written once and referenced, in the
document that carries it. `store-aggregate/v1`'s two five-field blocks
are the case that proves it is worth doing.

## Out of Scope

- Dropping descriptions from the schema the page *does* render. They
  are the sentences `UX-220` exists to put beside a number, and the
  reachability count above says most of them land.
- Minifying the module blob. It is 55% of the page and `UX-307` already
  strips its comments; a further pass is a different item with a
  different risk (`UX-199`).

## Acceptance Test

An exported page embeds exactly the schemas its own embedded documents
declare — asserted by reading the ids out of the payload blocks and
comparing with the keys of `bga-schemas`, on both committed fixtures, so
the clause fails if the set is hardcoded. `bga view`'s `schemas.json`
still answers with every published id. Both fixtures still render the
same section list they did before, and the golden export's page size
drops by at least 30,000 B — pasted, before and after.

## Outcome (round 52, 2026-08-27) — 🟢 Done

### The gap, measured

```text                          golden        macro_micro
page                          330,517 B      369,959 B
  bga-report                   17,891 B       57,246 B
  bga-run                         378 B          465 B
  bga-schemas                  83,669 B       83,669 B   <- identical
  module blob                 203,073 B      203,073 B
```

### After

```text
golden        330,517 -> 290,829 B   -12.0%   39,688 B saved
macro_micro   369,959 -> 330,271 B   -10.7%   39,688 B saved

embedded schemas, both fixtures: ['analyze/v2']
sections 28 -> 28 identical=True     failed=[] pageFailed=False
sections 40 -> 40 identical=True     booted in real Chrome
```

Well past the 30,000 B the Acceptance Test asked for.

### Derived, and at any depth

`schemas_payload(documents)` walks the documents being embedded and
collects every `schema` id they name. **At any depth**, because a
document can carry another's id inside it — `UX-253`'s aggregate says
which contract sets it mixes — and a page drawing the inner one needs
its schema as much as the outer. An id this build does not publish is
**dropped rather than raised**: a payload written by a newer build
should render generically, not refuse to export.

`schemas_payload()` with no argument still answers with everything, so
the served `schemas.json` is byte-for-byte unchanged. One function, two
answers, told apart by its argument — two functions would drift, and
drift is how the export came to carry all eight.

### A guard the round had to correct rather than relax

`test_the_data_dwarfs_the_page_on_a_report_worth_measuring` went red,
and it was right to: it counted the embedded schemas as **data**. They
are not. They were byte-identical across two different runs — which is
how this item was found — so they belong on the fixed side, beside the
modules and the stylesheet. Measured on the 1000-element fixture:

```text
                     before      after
page (modules, css)  228,291    228,291
embedded schemas      83,669     43,981
fixed cost           311,960    272,272
run's own data       684,801    684,801   <- unchanged
run data / fixed       2.195      2.515
old data/page          3.366      3.192
```

The numerator is identical because this round removed no data. Under
the old metric that reads as a **regression**, which is the tell that
the metric was measuring the wrong thing. The bound is 2.4x: the
pre-`UX-342` export fails it at 2.195.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| C1 | the export embeds every published schema again | `test_the_embedded_set_is_the_declared_set` (both fixtures), `test_it_stops_carrying_the_ones_nothing_declares` (both), and the corrected ratio clause — 5 failed, 28 passed |
| C2 | the derivation reads only each document's top level | `test_the_page_can_resolve_the_schema_its_report_declares` (both), `test_a_nested_schema_id_is_found`, and `test_it_renders_the_runs_findings_and_sections` — 6 failed, 27 passed |
| C3 | the served endpoint starts trimming too | `test_schemas_json_still_answers_for_every_published_id` and `test_it_renders_what_the_served_page_renders` — 2 failed, 31 passed |
| C4 | an unknown schema id is kept rather than dropped | `test_an_id_this_build_does_not_publish_is_dropped_not_raised` — 1 failed, 3 passed, 6 errors |

C2 is the one worth reading: reading only the top level does not merely
lose a nested id, it loses the *report's own* — because the walk that
finds it is the same walk.

### Deviation from the Required Fix

- **The prose deduplication was not built, and the measurement is why.**
  The Required Fix asks for repeated description prose to be written
  once and referenced, naming `store-aggregate/v1`'s two five-field
  blocks (one 670-byte paragraph, ten copies, 6,030 B) as the case that
  proves it worthwhile. Those copies are gone — not deduplicated, but
  no longer embedded at all, because no export carries
  `store-aggregate/v1`. What is left inside `analyze/v2` is **4,046 B**
  of repeated prose, 9.6% of that schema and 1.4% of the page, and all
  of it is the provenance block written three times
  (`findings[].provenance`, `headline.provenance`,
  `headline.top_actions[].provenance`).

  That is the shape `UX-344` normalizes — provenance published once,
  keyed by claim. Adding a `$ref`-style indirection the viewer must
  resolve, for 4 KB, immediately before the round that removes the
  cause, would be apparatus with a shorter life than the thing it
  works around. Recorded on `UX-344` so the saving is claimed where it
  is real.

  The source is already deduplicated: `bga/schemas.py:2173` writes that
  paragraph **once** and reuses the constant ten times. The repetition
  exists only in the serialized JSON.
