# UX-342: the export ships six schemas nothing can resolve

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-195 (the export), UX-307 (which removed the source commentary for the same reason), UX-201 (why the schema travels at all) | **Serves:** anyone who attaches a report to a ticket | **Topic:** viewer

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
