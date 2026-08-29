# Audit round 63: the outsider walk, twice

Run on 2026-08-29, immediately after round 62's slate. The user asked
for the outside-walker experiment again — capture all planes, read the
report in a browser, take the Perfetto handoff, and **repeat the
`snapshot` → `view` cycle** looking for view elements nobody has
noticed. Everything below was reproduced on this machine before it was
filed.

## What was walked

A real all-planes capture of `examples/06-macro-micro-optimization`:

```text
bga snapshot --project examples/06-macro-micro-optimization \
    --trace-opens --trace-spine=on -- bst build all.bst
```

That is the store's second run, so the cycle ran twice. Both reports
were exported and driven in a real Chromium over CDP.

## The report, measured

```text
                        run 1 (full)   run 2 (incremental)
page height                  9,316 px            3,347 px
sections                           71                  36
payload keys                       51                  30
tables                             31
buttons                           423
folds (<details>)          45, none open
search boxes                        2
```

**Seven screens of scrolling, 77 rail entries, 423 buttons.**

## The findings

### 1. An empty population disappears without a word (`UX-388`)

The reason to run the cycle twice. `renderSection` returns `null` for
an empty array, so a population the analysis computed and found empty
renders *nothing at all* — no heading, no sentence, no rail entry.
Between the two runs six sections vanish:

```text
optimization_horizon   5 rows -> []       section gone
latent_heavies         1 row  -> []       section gone
joint_saving           object -> null     section gone
violations             []     -> []       never present
consolidation_candidates  []  -> absent   never present
```

The report shrinks from 9,316 px to 3,347 px and says nothing about
why. A reader cannot tell "this run has no optimization horizon" from
"this version of bga does not compute one" — which is `UX-107`'s rule
(*"nobody could look" must not read as "looked and found nothing"*)
applied to coverage blocks but never to populations.

### 2. Fourteen of twenty-five Plane 2 blocks reach no browser (`UX-389`)

The direct answer to "is all the captured data really accessible
through `bga view` or Perfetto". It is not:

```text
plane2 blocks in the capture            25
  a key in analyze/v4                    6
  reaching the page through the join     6
  terminal only                         14
```

The fourteen include `static_census` (which elements could be hiding a
static binary), `spine_policy` (whether the spine ran at all),
`max_concurrency`, `process_count`, `wall_span_s` and
`stream_coverage` — the "did the instrument see everything" questions,
answerable at a terminal and not in a browser. `UX-385` added
`commands_not_observed` one round ago and it is already the fifteenth.

### 3. Attribution and its hints are one population in two sections (`UX-390`)

The user asked whether these could merge. Measured: the key sets are
**identical**.

```text
attribution        execution_on_chain_us dependency_wait_us resource_wait_us
                   scheduler_wait_us idle_us retry_wait_us
                   untracked_head_us untracked_tail_us
attribution_hints  (the same eight)
SAME KEY SET       True
```

Two `<h2>` sections over one population, each carrying a different
sentence about the same field — which is `UX-288`'s one-population rule
at section level. The hints section also renders its keys raw, with the
unit suffix left on: **"Execution on chain us"**.

### 4. `wall_clock_share_us` shows the reader a composite key (`UX-391`)

```text
codegen.bst|BUILD|BUILD|0    2.3 s
```

The pipe-delimited task uid, verbatim, as a row label — `UX-374`'s
defect one section over.

### 5. Thirty-one tables, one search box (`UX-392`)

The user asked whether the search controls help, naming the main one
and a blast-radius one. There is no blast-radius search: the page has
**two** search-shaped inputs in total — the global `Jump to…` box and
one table filter on `binary_cost`.

```text
tables                        31
  with a filter box            1
  with a preset menu          22
  with a threshold input       1
  >10 rows and no filter       4
```

### 6. Nothing moves to the next section, or back to the top (`UX-393`)

Over 7.4 screens, one control matches *next / previous / top* and it is
an ordinary link to `#next_steps`. The rail is sticky and lists 77
entries; there is no "next section", no "back to top", and no
indication of where in the report you are.

### 7. Nothing moves between runs (`UX-394`)

The user's instinct was right. The store held two runs while this was
measured and no control in the page reaches the other one — `bga view`
is a single-run window, and `@prev`/`@last` exist only as CLI
arguments.

### 8. `--format chrome` silently drops the flows and counters (`UX-395`)

Two of the fourteen canned questions read tables the chrome trace does
not carry:

```text
                    slices   flows   counters
trackevent             826     836        538
chrome                 663       0          0
```

`waited-on-flow` reads `flow`; `concurrency-curve` reads
`counter`/`counter_track`. Against a chrome trace both return zero rows
and the reader concludes the build had no concurrency and nothing
waited on anything. The chrome path's own summary omits the two counts
rather than reporting them as zero. **The page's embedded handoff is
the trackevent protobuf, so the shipped path is sound** — this is the
documented `bga timeline --format chrome` invocation.

The other twelve queries were checked against the trace's real arg keys
and tables: all resolve.

### 9. Sixteen of forty-four sections draw something (`UX-396`)

```text
sections with a drawing                       16 of 44
sections with rows or numbers and no drawing        10
```

The ten include `findings` (22 numeric spans, no shape),
`batch_opportunities` (10 rows), `next_steps` (14 rows) and
`serialization_point_risks`.

### 10. The Perfetto handoff, and a library (`UX-397`, and a decision)

The handoff button sits in the header at y=137 while the rail beside it
is already sticky — the user's suggestion to pin it into the rail costs
nothing structurally, and is filed.

On **Tabulator**: the honest position is that the page has 31 tables,
22 preset menus, one filter and one threshold input, all hand-rolled
across 21 viewer modules, and `UX-349` already found the tools not
scaling with the table. A library would answer findings 5 and 9 at
once. It is also 400 KB against a page whose whole export is 477 KB and
whose CSP admits four CDNs — and `UX-296`'s "the view that parses
nothing" and `UX-307`'s no-source-commentary rule both exist because
this page is deliberately dependency-free. The round files the question
rather than the answer: it is a product decision, with the volume
budget (`UX-360`, `UX-367`) as the arbiter.

## Verified, and not a defect

- **No unbound view element in the top-level payload.** Every one of the
  44 anchors renders real content; a first pass suggested five blocks
  rendered nothing and that was the crude string matcher, not the page —
  `43200000` reaches the reader as "43.2 s". Stated because the negative
  result is what the round was asked to look for.
- **Twelve of fourteen canned queries** name only tables and arg keys the
  emitted trace actually carries.
- **`bga timeline` refuses a run directory with the fix in the message**,
  naming the snapshot directory to use instead.

## Filed

`UX-388` .. `UX-397`.
