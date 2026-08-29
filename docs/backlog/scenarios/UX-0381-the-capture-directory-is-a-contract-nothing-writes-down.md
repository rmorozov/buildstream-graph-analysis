# UX-381: the capture directory is a contract nothing writes down

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-134 (the store names the run but not its Plane 2 report), UX-328 (--schema answers for everything that emits one) | **Serves:** anyone reading a snapshot with something other than bga | **Topic:** contracts

## Motivation

Every published `bga` command line names a path inside `.bga/`. The tool
prints them itself, at the end of every capture:

```text
bga blast storm.bst .../.bga/runs/20260829T083056Z/run
bga correlate .../.bga/runs/20260829T083056Z/run
bga compare @prev @last
```

`@last` and `@prev` resolve by listing `runs/`; `bga view` reads `run/`;
`bga correlate` finds `plane2.json` as a sibling; `bga timeline` reads
`plane2.log.gz`; the store aggregator walks the lot. The layout is
load-bearing in a dozen places. Here is what a capture actually writes,
measured:

```text
.bga/
  .gitignore
  config
  tmp/
  runs/<stamp>/
    run/
      graph.json
      trace.json
      run-context.json
      chrome_trace.json
      sources.json
    plane2.json
    plane2.log.gz
    plane2-resource.json
    analyze.json
    build.log
    element-slice.json
    capture-context.txt
    .size
```

Fourteen paths. Part 32's contract registry names **one** of them:

```text
| the Plane 2 report at `plane2.json` beside a run | `plane2/v2` | `bga.plane2` |
```

The only file-layout table in the documentation is in
`docs/design/capture-workflow.md`, and **it describes a different
directory** — the CI field-capture bundle, with different names for the
same two files:

```text
| `native-report.json` | the Plane 2 report |
| `native-trace.log`   | the raw LD_PRELOAD trace |
| `graph-declared.json`| the declared graph |
| `rebuild-set.txt`    | the exact elements deleted |
```

A reader who finds that table and goes looking for `native-report.json`
in a snapshot will not find it; it is `plane2.json`. And six of the
fourteen real paths — `element-slice.json`, `plane2-resource.json`,
`sources.json`, `chrome_trace.json`, `.size`, `config` — appear in no
table anywhere.

The nearest thing to an authority is `bga/run_store.py`, where the names
are module constants (`STORE_DIRNAME`, `RUNS_DIRNAME`, `RUN_SUBDIR`,
`RESOURCE_NAME`, `ANALYSIS_NAME`, `RAW_LOG_NAME`, `SIZE_CACHE_NAME`).
That is a good place for the values and not a statement of the contract:
nothing says which are required, which are optional, what an absent one
means, or what a consumer may assume.

This is `UX-328`'s rule one level up. Every *document* bga emits answers
for its own schema; the *directory* those documents live in — which is
the thing users paste into issues, tar up, and hand to CI — answers for
nothing.

## Required Fix

The capture directory becomes a stated contract, in the place the other
contracts are stated.

- **A layout section in the specification**, one row per path: what
  writes it, what reads it, which contract it carries where it has one,
  whether it is required or conditional, and what its absence means. The
  conditional ones matter most — `plane2.log.gz` is absent from a
  capture taken with tracing off, `run/` is absent from a build that
  failed before any element completed (`UX-156`), and a reader currently
  learns both by getting an error.
- **`run_store.py` names the contract it implements**, so the constants
  and the specification are one statement rather than two.
- **`capture-workflow.md`'s table is corrected or scoped.** It describes
  the field-capture bundle; either it says so in the sentence above it,
  or the two layouts are reconciled under one set of names.

## Falsification

A guard that walks a real capture and asserts every path it finds is
named in the specification's layout table, and that every path the table
marks required is present. Today the first fails on thirteen of
fourteen paths.

The other direction: a capture taken with `--trace-spine=off` and no
Plane 2 log still satisfies the guard, because the table marks that path
conditional and says what its absence means.

## Out of Scope

- Changing any filename. The names are published — old snapshots carry
  them and users have pasted them into issues — and this is about
  writing down what they are.
- The field-capture bundle's own contents. Its layout is a separate
  artefact with a separate producer, and all this item needs from it is
  that its table stops reading as a description of a snapshot.
