# UX-381: the capture directory is a contract nothing writes down

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-134 (the store names the run but not its Plane 2 report), UX-328 (--schema answers for everything that emits one) | **Serves:** anyone reading a snapshot with something other than bga | **Topic:** contracts

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

## Outcome

Done. `capture-layout/v1` is the twentieth contract in
`bga.contracts.ids()`, declared in `bga/run_store.py` beside the
constants it names, rendered into the specification as **32.6**, and
held equal in both directions by a guard that walks a real capture.

**Presence has three values, not two.** The filing asked for
"required or conditional"; the directory has three states and
collapsing them loses the one a reader most needs. `required` means
the capture is unusable; `conditional` means an option was off or a
stage did not run; `derived` means nothing at all - it is a cache and
is rebuilt. A `.size` that is missing and a `graph.json` that is
missing are not the same event, and a two-valued column would have
said they were.

**Twenty-one paths, not fourteen.** The filing counted fourteen from a
directory listing. Reading the writers found seven more, including two
the round itself added: `host-samples.jsonl` (`UX-378`) and the
snapshot directory `runs/<stamp>/` itself, which is the unit
`bga snapshot --list` enumerates and `@last` names - the guard caught
that one, not the reading.

**Two findings the layout table surfaced**, neither of which the
filing anticipated:

1. **`host-samples/v1` was written to every sampled capture and
   inventoried nowhere.** `bga.contracts` derives its inventory by
   walking the `bga` package, and `UX-378`'s sampler lives in
   `tools/bst_native_build_tracer.py` - so a contract this tool stamps
   was invisible to the registry, the guards and every document. That
   is `UX-248`'s own defect, one directory over, five rounds later.
   `contracts.py` gained an `OWNED` declaration form (a module names a
   contract it owns without stamping a document of its own), and
   `run_store` - the module that knows the directory - names it. It is
   now in the registry, Part 32.5, the architecture inventory, the
   docs index and the release ledger.

2. **`graph/v9`, `trace/v9` and `run-context/v9` are not ours.** The
   source-scan guard's `NOT_OURS` set was empty with a comment
   describing exactly these three: the spec's own input shapes, which
   `bga` does not version. Nothing had cited one from source until the
   layout table named the contract each path carries. The comment
   described them before there was anything to exclude; now the set
   does too.

**A recorded deviation.** The filing's Required Fix says
`capture-workflow.md`'s table is "corrected or scoped". It is scoped,
not corrected: reconciling the two layouts under one set of names would
rename published files in a CI artefact with a separate producer, which
the item's own Out of Scope forbids. The sentence above the table now
says it is the CI field-capture bundle, names the two files a snapshot
spells differently, and points at 32.6.

## Verification Log

**What the directory holds, and what named it.** Read from the writers
rather than from one listing:

```text
paths a capture writes                            21
named in Part 32's registry, before                1   (plane2.json)
named in Part 32.6, after                         21
in `capture-workflow.md`'s table                   9   - a DIFFERENT
                                                       directory, and
                                                       two files under
                                                       other names
in no table anywhere, before                       7
```

**The registry, before and after:**

```text
bga.contracts.ids()          18  ->  20
bga.contracts.unprintable()  10  ->  12
```

Both new ids are on-disk shapes with no command to print them, which is
what `unprintable()` is for. `capture-layout/v1` is the only one whose
"file" is the tree.

**A real capture, walked.** `examples/06`'s store, with the run stamp
normalised so a fixed number of rows describes a store of any size:

```text
paths on disk that the contract does not name     0   (was 20 of 21)
required paths absent                             0
required paths absent with Plane 2 removed        0
```

The last line is the Falsification's other direction: a capture taken
with `--trace-spine=off` still satisfies the guard, because the four
Plane 2 paths are `conditional` and the contract says what their
absence means.

**Mutation sweep**, eleven mutations against the committed tree, run
against `test_the_capture_directory_is_a_contract.py` and
`test_the_contract_inventory_is_derived.py`:

```text
M1  the layout drops analyze.json                      CAUGHT
M2  plane2.json is marked required                     CAUGHT
M3  graph.json is marked derived                       CAUGHT
M4  a row cites a contract nothing owns                CAUGHT
M5  32.6 loses the build.log row                       CAUGHT
M6  32.6 names a path nothing writes                   CAUGHT
M7  32.6 and the module disagree on a presence         CAUGHT
M8  the layout declares no contract                    CAUGHT
M9  host-samples/v1 leaves the inventory again         CAUGHT
M10 a row's sentence is a label, not a statement       CAUGHT
M11 the field-capture table stops scoping itself       CAUGHT
```

M2 and M3 are the pair that matters most: a contract whose presence
column can drift is a contract that tells a reader the wrong thing
about an absence, which is the whole reason the column has three
values.
