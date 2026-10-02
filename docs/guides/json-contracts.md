# The JSON contracts

What `bga` writes and what it reads, by schema id. The command that
prints each one is in [`cli.md`](cli.md); what must be true of each is
the [specification](../spec/specification.md).

## What it emits

Every JSON document `bga` writes carries its schema id, and
`bga <command> --schema` prints that command's contract — types, units,
and the view-hints the browser report renders from (`UX-201`). Where a
command emits two documents, the flag selects: `bga snapshot --list
--schema` and `bga snapshot --aggregate --schema` print different
contracts. Twenty-eight ids, and what writes each:

| document | written by |
|---|---|
| `analyze/v7` | `bga analyze --format json` — the analysis, its findings, and why each one is believed (`UX-229`) |
| `compare/v2` | `bga compare --format json` — the verdict, the noise band, the culprit elements |
| `blast/v2` | `bga blast --format json` — what a change to one resource rebuilds |
| `correlate/v2` | `bga correlate --format json` — Plane 1 and Plane 2 joined on element uid |
| `whatif/v1` | `bga whatif --format json` — what the build drops to if a chosen set is fixed, and whether the savings add (`UX-230`) |
| `junction-cost/v1` | `bga junction-cost RUN RUN --format json` — N builds of one type under different variants priced against one junctioned invocation: the elements shared by cache key, the pipeline paid N times, the union floor, each figure citing its assumption (`UX-904`) |
| `store/v1` | `bga snapshot --list --format json` — the runs in this project's `.bga/runs` |
| `store-aggregate/v1` | `bga snapshot --aggregate --format json` — the store as a distribution, per host class (`UX-234`) |
| `capacity-model/v1` | `bga snapshot --capacity N,RATE --format json` — a builder count and an arrival rate as a queue: utilization, the wait before a build starts and the number waiting, per host class, each figure carrying the assumptions its own arithmetic used (`UX-613`) |
| `sweep/v1` | `bga sweep --format json` — what more capacity would buy, the knee past which it buys little, and where the model contradicted itself (`UX-339`) |
| `tail/v1` | `bga snapshot`, at `tail.json` beside each snapshot — what the tool itself cost after the build: each phase's wall and peak RSS, and the build's own wall (`UX-1078`) |
| `host/v2` | `bga.hostinfo`, inside every `run-context.json` — which machine measured this run, and what makes two runs comparable |
| `sources/v1` | `bga extract`, at `sources.json` in a run directory — every element's sources, and how each one is keyed |
| `plane2/v3` | `bga capture`, at `plane2.json` beside a run — what Plane 2 measured about one build: run-level measurements, with the per-element reductions among them. Measured on the committed fixture, 21 of 24 top-level blocks are run-level and 3 are keyed by element uid, so a reader after the host's peak memory, the build's process count or whether the spine ran is in the right file (`UX-386`). The per-process record list `UX-297` retired is gone |
| `host-samples/v1` | `bga capture`, at `host-samples.jsonl` beside a run — the host's memory, swap and CPU while the build ran, one object per line (`UX-378`, `UX-675`) |
| `capture-layout/v1` | the capture directory `.bga/` itself — every path it holds, what writes it, what reads it, and what an absence means. Specification 32.6 (`UX-381`) |
| `bundle-manifest/v1` | `bga bundle --export`, inside `bundle.json` in the archive — each member's path, presence and contract version, plus the `bga` that packed it, so the receiving side refuses a bundle it cannot read in full rather than half-loading it (`UX-520`) |
| `plane2/v2` | the same file as a capture before `UX-384` wrote it, with the element names of every redundancy finding embedded. Still read, never written |
| `plane2/v1` | the same file as a capture before `UX-297` wrote it, with every per-process record embedded. Still read, never written |
| `analyze/v6` | what `bga analyze` wrote before `UX-1247` made `by_binary` ranked rows of CPU, wall, calls and elements rather than a calls map. Still read, never written |
| `analyze/v5` | what `bga analyze` wrote before `UX-641` gave `parallelism.levels` its members rather than the row number. Still read, never written |
| `analyze/v4` | what `bga analyze` wrote before `UX-535` published the graph's shape once. Still read, never written |
| `analyze/v3` | what `bga analyze` wrote before `UX-344` lifted the `signals` and `structural` namespaces. Still read, never written |
| `analyze/v2` | what it wrote before `UX-341` unified the units — `measured_seconds`, `peak_rss_kb`, `useful_pct`. Still read, never written |
| `compare/v1` | the same, for a comparison. Still read, never written |
| `blast/v1` | the same, for a blast answer. Still read, never written |
| `correlate/v1` | the same, for the two-plane join. Still read, never written |
| `host/v1` | the host manifest with `memory_mb` where `host/v2` has `memory_bytes`. Read and converted on the way in, so an old baseline still compares — never written |

The last eighteen are written into a run directory — or, for
`bundle-manifest/v1`, into the bundle that carries one — rather than
printed by a command, so no `--schema` invocation prints them, and eleven of those
are only ever *read* - they are the shapes an older store's artifacts
are in (`plane2/v1` from `UX-297`, `plane2/v2` from `UX-384`, five from
`UX-341`, `analyze/v3` from `UX-344`, `analyze/v4` from `UX-535`,
`analyze/v5` from `UX-641` and `analyze/v6` from `UX-1247`). The other ten
each have a command that prints their contract, and
`tests/unit/test_every_emitted_contract_is_answerable.py` holds that
split by running both sides rather than by reading this table
(`UX-328`). Every command that prints a document now answers for it:
`bga sweep` was the last that did not, and `UX-339` gave it one. A key
may be added to
any of these without a version bump; a rename or a removal bumps. The full contract table is
[spec Part 32.5](../spec/specification.md); what each command does with it
is [`cli.md`](cli.md).

## What it reads

Three shapes `bga` never writes and cannot run without — the capture's
own input, stamped by whatever produced it (`UX-540`):

| document | read by |
|---|---|
| `run-context/v9` | `bga.ingest.load_run_context`, at `run-context.json` — what the run was: identity, the `host/v2` manifest inside it, scheduler configuration |
| `graph/v9` | `bga.ingest.load_graph`, at `graph.json` — the declared element graph, from `bst show` |
| `trace/v9` | `bga.ingest.load_trace`, at `trace.json` — the scheduler's own spans and phases, Plane 1 |

`bga.contracts.reads()` names these; `bga.contracts.ids()` names the
table above; `superseded()` names what the tool reads but no longer
writes. What a release *accepts* and what it *emits* are separate
questions, so they have separate answers. No `--schema` prints an
input: the shapes are specified in [spec Parts 32.1-32.3](../spec/specification.md).
