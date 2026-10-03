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
| `junction-cost/v1` | `bga variant-cost RUN RUN --format json` — N builds of one type under different variants priced against one junctioned invocation: the elements shared by cache key, the pipeline paid N times, the union floor, each figure citing its assumption (`UX-904`) |
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

## The JSON outputs, and their schemas (`UX-190`)

Every machine-readable output declares its own shape as its **first
key**:

```bash
bga analyze RUN/ --format json | head -2      # "schema": "analyze/v7"
bga compare A B --format json                 # "schema": "compare/v2"
bga blast TARGET --format json                # "schema": "blast/v2"
bga correlate RUN/ --format json              # "schema": "correlate/v2"
bga whatif RUN/ --element E --format json     # "schema": "whatif/v1"
```

`--schema` prints the JSON Schema of an output and exits 0. It needs no
run directory — it answers about a shape, not about a run:

```bash
bga analyze --schema
bga compare --schema | jq '.required'
```

**The versioning rule**: a field rename or removal bumps the version —
and so does a key entering `required` under a live id (`UX-629`),
because the document you wrote last week stops validating against the
id you pinned. A *permitted* addition does not, so pin `analyze/v7` and
your consumer keeps working while the tool grows.

A key the tool writes on **every** document is therefore declared
permitted rather than required, and named in the schema's own
`bga:always_written` — so `--schema` tells you the difference between
*may be here* and *is always here*, and the guarantee is held against
the real payload instead of by validation:

```bash
bga compare --schema | jq '."bga:always_written"'
# ["verdict_provenance", "build_class_comparison", "baseline_band_sources", "baseline_band_origin",
#  "baseline_band_skipped_for_host", "total_duration_delta_share", "findings_diff"]
```

`compare/v2`'s `verdict_provenance` is the worked example. `UX-610`
made it required under an unmoved id, taking the required set from 14
to 15, and every `compare/v2` document written before it stopped
validating; it is permitted-and-always-written now, so those documents
validate again and the id did not have to move. The newest,
`total_duration_delta_share` (`UX-1257`), is the wall-clock delta as a
share of the baseline's — negative is faster, `null` with no baseline
total — and is what `bga view`'s compare chapter leads with.
`findings_diff` (`UX-1277`) splits the candidate's findings by id into
`new`, `persisting` — each with its `age`, the consecutive snapshots that
hold it, read off the earlier runs' published analyses, and `age_exact`,
false when that walk stopped on a run it could not read — and `resolved`;
`null` on a refusal. When only one run recorded Plane 2, a finding on one
side only is listed in `not_compared` with its `not_compared_reason`
instead. `bga view` marks each finding card from it.

### Which keys the prose names, and which it does not (`UX-628`)

`--schema` is the complete key list. The *documents* are not, and this
says how far they go, because five keys once shipped in one window with
nothing outside the backlog naming any of them — `verdict_provenance`
on `compare/v2`, `queue_wait_us` and `queue_wait_absent_reason` on
`store/v1`, `requested_at_us` and `requested_at_source` on
`run-context/v9`.

The guard that was supposed to stop that had contract **ids** for a
population, so it could not see a key. It has keys now: the printable
contracts' *consumer surface* — each schema's top-level properties, the
keys **one level below** one of them, and every **row** the document
hands you, since a row of `store/v1`'s `snapshots` is what you actually
read. That surface was 199 keys when this was written, 84 of them named
in no document outside `docs/backlog/` and `docs/audits/`; naming the
five above left 80, and `UX-636` paid those 80 off in the section below.
The register in the guard is empty, so the figure it holds and this
sentence is checked against is **0 undocumented keys**.

A row is found **at any depth**, and by any of the three things that
declare one: an array's `items`, the `bga:columns` an array node
carries, and a dict's `additionalProperties.properties`. The first two
are needed, and `UX-655` measured why — `analyze/v7`'s
`parallelism.levels` has no `type` and no `items` at all, so its
columns are the whole statement of what one of its rows holds, and
`level` and `width` are in no `items` anywhere. Depth is the same
finding one level up: `parallelism` is a top-level *object*, its
`levels` rows are below that, and a population reaching only under a
top-level array published the whole of a major bump outside itself.
The third is `UX-838`: `elements.fan_in` and five other rows are keyed
by something that is not an array index at all, so neither `items` nor
`bga:columns` sees them. The fourth is `UX-866`: `run_instance` is
typed as a bare `object`, not a row at all - its keys (`seed` among
them, `UX-858`) are declared only by its own view-hint's `properties`,
read at any depth the same way.

Each of those four is a **shape** bought back after it escaped, and
buying shapes back one at a time is what produced the next one. `UX-909`
stopped that with a **depth** instead: every key declared one level
below a top-level property is in the population, whatever shape it is.
That is where the report's own blocks declare their scalars — `floors`,
`attribution` and `cache` are not internal shapes of a block, they *are*
the blocks a reader meets first, and `certified_headroom`, the number
Key Findings leads with, had never been in the population at all. It was
302 such keys when that was filed and 305 when it landed. One level and
no further: `blast_radius_distribution.deciles` is in the population and
its own nine buckets are not. The surface is **639 keys** today, and
that figure is derived from the walk rather than typed here.

So the statement of coverage, which is now a statement and not a
promise:

- **every key of every printable contract you are handed is named in a
  document** — its top-level keys, the keys one level below one of
  them, and the columns and `items` of every row inside it at any
  depth — and a key added to one of those schemas has prose or the
  guard reddens naming it;
- what is *not* in it is anything more than one level below a
  top-level key that is not also a row: the reader has `--schema`,
  the complete list, for the shape beneath that, and a document
  reproducing it would be the second copy of the schemas `UX-384`
  banned (`UX-628` declined it, `UX-655`
  re-measured it, and `UX-909` moved the line down one level rather
  than removing it);
- a document that **argues for** a key is not a document that
  describes it: `docs/backlog/` and `docs/audits/` never counted, and
  since `UX-909` neither does a `docs/design/*.md` whose header says
  `**Status:** proposed`. Four keys rested on one of those alone the
  moment the walk widened — `mean`, `skipped_inputs`,
  `t_infinity_cold` and `unmeasured_processes`;
- the register the debt was held in may only shrink and is at zero, so
  a key going undocumented is a decision somebody argues, not a number
  that drifts;
- `run-context/v9`, `graph/v9` and `trace/v9` are **not covered at
  all**. They are stamped by whatever produced the capture, `bga` only
  reads them, and there is no JSON Schema here to enumerate — so
  `requested_at_us` and `requested_at_source` are held by prose alone.

A section subcommand (`bga floors`, `bga graph`, …) emits the same
`analyze/v7` document restricted to its own keys, with a `section` key
naming the restriction — so a missing key can be told from a removed
one.

### Every published key, by contract (`UX-636`)

The rest of the consumer surface, one line each — what the key is, not
what its schema says it is. `--schema` stays the complete list and the
source of truth for types; these rows are so a reader holding a payload
can look one up.

`analyze/v7` — the run-level blocks:

| key | what it is |
|---|---|
| `bottleneck` | Where work funnels through one element, and how much waits behind it. `choke_points` ranks by `downstream_count`. |
| `cpu_time` | The run-level CPU totals beside `element_cpu_time`, with the sentence saying what a CPU figure here is and is not. |
| `resource_pressure` | The run-level coverage beside `element_resource_pressure`, and what each counter counts. |
| `configure_phase` | The share of CPU spent configuring rather than building. A floor, for the reason its own `note` gives. |
| `element_duration_distribution` | How this run's element durations are spread — the answer to "is 40s slow *here*?". Nearest-rank percentiles. |
| `blast_radius_distribution` | How many elements sit downstream of each, across this graph. "753 downstream" is p99.9 in 1,202 elements and unremarkable in 40,000. |
| `fan_in_distribution` | Its mirror: how many elements each *pulls in*, across this graph. "8 upstream" is unremarkable in a 40,000-element run and p99 in a graph of forty. |
| `element_join_coverage` | How far the two-plane join reaches: `joined_elements`, each plane's count, and the elements only one plane saw. |
| `attribution_hints` | One sentence per wait category saying what reduces it — the advice that belongs with `attribution`, not a second copy of it. |
| `latent_heavies` | Heavy elements not on the path today. They cost nothing now and become the constraint once what is above them is fixed. |
| `task_durations_us` | `UX-1194`: each task's own duration, start to finish, keyed by task uid like `wall_clock_share_us` beside it - a duration, where the share is the window that task alone held. |
| `consolidation_candidates` | Elements always consumed together that could be one element. Structural: from the graph's edges, never a timing estimate. |
| `batch_opportunities` | What could be built together, with `serialized_pairs` naming the pairs that share a chain and therefore cannot. |
| `joint_saving` | What fixing the top candidates *together* is worth, simulated, beside `sum_of_individual_us` — they differ when savings overlap or compound. `relation` says which (`add`, `overlap`, `compound`); `worth_more_after` names the candidates worth more once the ones above them are fixed. |
| `serialization_point_risks` | Where the run is forced to serialize. Each entry carries `pinned_elements` (what was pinned, and to what), `governing_cores` (the cores they competed for) and `typical_max_jobs` (the `-j` their own builds used). |
| `resource_blast` | What one shared resource rebuilds. `null` where no source inventory was captured. |
| `by_junction` | `UX-1327`: the run rolled up by junction prefix (everything before an element's last `:`), Plane 1 only. One row per prefix, the top project first: each element counts under its deepest prefix, and every ancestor prefix is a row. Absent when no element is junctioned. |
| `fingerprint` | `UX-1073`: what this analysis was computed from - the producer stamp, a sha256 of each run-directory input and of the Plane 2 report attached, and every result-affecting option. `bga compare` reads a published `analyze.json` instead of analyzing again only when this equals its own; `--reanalyse` never reads it. |
| `run_instance.jobserver` | `UX-851`: the jobserver `bga capture` ran with, inside `run_instance` (`UX-404`'s capture identity, which also carries `started_at_us` - when the capture began - and `host_manifest.cpu_count`/`.memory_bytes` - what the host reported, the ceilings are computed against). `mode` (`off`/`auto`/`n`), `ceiling` (the token count given or derived, `null` when off), `seed` (tokens the FIFO opened holding, `UX-858`: `max(0, ceiling - builders)` under `auto`, `ceiling - 1` otherwise, `null` when off), `auth` (`fd`/`fifo`, `null` when off), `project_max_jobs` (the target element's own declared `max-jobs`, `null` when `bst` was unavailable). Absent, not defaulted, on a capture older than the field - `bga compare`'s header reads that absence as `jobserver off`. |
| `jobserver` | `UX-847`: the pool's own record - `mode` (`fixed`/`dynamic`), `pool_ceiling`, `tokens_idle_share` (controller ticks with cores idle and tokens still in the pool) and `tokens_starved_share` (cores idle with the pool empty) - and `per_element`, keyed by uid: `joined` (`yes`/`pinned`/`held`/`unknown_kind`), `UX-1012`'s `peak_work_concurrency` against the element's own `max_jobs` and the `verdict` read from the two (`drew` when joined and the peak exceeded `max_jobs`; `offered, not drawn` when joined at a peak no wider; `outside the pool` when `pinned`/`unknown_kind` and the peak exceeded `max_jobs` + 1, `UX-1008`; else `pinned`/`held`/`unknown_kind` repeat `joined`), `admission_wait_us` (time the shim blocked the element on its admission token, `UX-1005` - its slot, not a draw), `tokens_held_p50`/`tokens_held_max` (UX-846's own acquire rows joined to this element by the pid that acquired them, `null` when the element ran no wrapped tool), and `UX-892`'s width over time: `tokens_held_series` (`[t_us, tokens]` steps, an acquire opening an interval and a release closing one - absent, not empty, when the element ran no wrapped tool), `tokens_series_coverage` (the share of the element's token-holding tools that wrote those rows - a real `make` reads the pipe itself and logs nothing), `tokens_series_open` (intervals no release closed, UX-852's leak) and `tokens_series_truncated` (whether the series hit its per-element cap). Present only when `--plane2`'s report carries a mode. |
| `trace_queries` | Every timeline query that shows a finding or deepens a claim, best first; `trace_query` is its first entry. Absent where there is a single grain. |
| `unused_dependencies`, `redundancy_count`, `worst_redundancy`, `native_findings` | The Plane 2 half of an `element_join` row: declared-and-never-read dependencies, how often this element repeated work it had already done, the repetition it paid most for, and the producer's own per-element tags. |
| `edges`, `projection` | Inside a `restructuring` finding: the declared build edges Plane 2 measured never-read, and the replay with those edges removed (`replayed_baseline_us`, `projected_us`, `saving_us`). Evidence, not a verdict. |

`analyze/v7` — inside a `findings`, `next_steps`, `readers`,
`provenance` or `binary_cost` row:

| key | what it is |
|---|---|
| `title` | The finding as one sentence, with its figure. |
| `detail` | The lines beneath it, or `null` where the title is the whole finding. |
| `copy_text` | The finding as plain text — title, evidence in declared units, elements, published next step, run identity. What the page's copy button yields. |
| `reason` | Why this next step, in terms of the values that chose it. |
| `follows_from` | The finding or published field the step was chosen by, so the advice can be checked against the number behind it. |
| `label` | What a reader would say about themselves, in the first person; the selector's option text. |
| `leads_with` | The id of the finding that is that reader's biggest lever here: highest severity, then published order. |
| `claim` | Which claim a `provenance` entry explains — a finding id, or `diagnosis` for the headline. |
| `calls`, `cpu_time`, `cpu_share`, `wall_us` | Per binary, in `binary_cost`: how many times this element ran it, the CPU it took, that CPU as a share of the element's measured CPU, and the wall-clock those calls spanned. |

`analyze/v7` — inside a row of a block below the top level (`UX-655`):

| key | what it is |
|---|---|
| `level`, `width`, `elements` | A row of `parallelism.levels`, one per level of the graph from the roots down: its longest path in edges from a source (roots are `level` 0), how many elements sit there, and which ones — what could run at once, once everything above it is built. |
| `fan_in`, `fan_out` | A row of `bottleneck.high_fanin_elements` and `high_fanout_elements`: dependencies this element names, and elements naming this one as a dependency. Degrees of the graph, never a transitive count — `blast_radius` is that. |
| `rank`, `best_split`, `weighted_duration_us`, `wall_share`, `members` | A row of `bottleneck.serial_chains` (`UX-830`): every maximal non-branching run, ranked by summed duration, not the single `longest_serial_chain` exhibit above it. `best_split` is the member whose own duration is largest — splitting it shortens the chain most; `wall_share` is `weighted_duration_us` over the run's longest weighted path; `length` (shared with the fan-degree rows above) is the member count. |
| `direct`, `direct_count`, `dependents`, `dependent_count`, `transitive_count`, `immediate_dominator` | A row of `elements.fan_in` (`UX-681`): the dependencies this element names, everything those pull in behind them, and the nearest element every path from a root passes through — the rebuild it waits on, which is not the same as a dependency. `direct` is every one of those dependencies by name, the 40 earliest in graph order first (`UX-829`, uncapped since `UX-1214`); excluded from the elements table by construction (arrays don't flatten into a row) and drawn on the element card instead, its first 40. `direct_count` is that list's length, and the degree `bottleneck.high_fanin_elements` ranks the top five of; whether those edges were read is `element_join.dependency_read_share`. `dependents` and `dependent_count` are the mirror (`UX-1187`): the elements that name this one, capped at 40 the same way, and their count — the card's Blocks list. |
| `risk_score`, `is_foundation` | A row of `elements.blast_radius`, beside `downstream_count` and `weighted_duration_us` above: `risk_score` is downstream work weighted by duration, a ranking comparable within a run and not across; `is_foundation` (shared with the `fan_in` row above) is whether the project declared this element foundation — excluded from the ranking on that declaration, not a kind guess. |
| `probability`, `slack_us` | A row of `elements.criticality_probability`: how often this element lands on the critical path under the run's own perturbation — 1.0 is always — and how long it could have been delayed before it would, zero meaning it is already on the chain. |
| `median_us`, `p75_us`, `p95_us`, `coefficient_of_variation`, `high_variability` | A row of `elements.duration_variability`, beside `mean_us`, `samples` and `host_class`: how steady this element's duration is across the store's earlier runs on the same host class — the middle of the series, the slow side at three runs in four and at the slow end, the spread over the mean (Part 29), and whether that spread crosses the threshold the ranking warning applies at. |
| `assessed_dependencies`, `dependency_read_share` | A row of `element_join`: how many of this element's dependencies Plane 2 could judge — the ones it saw opened plus the ones it saw nothing from — and how many of those were read. What `unused_dependencies` is a list *of*. A dependency with no observed opens at all is uncovered and in neither, so the share is absent rather than 1.0. |
| `phase`, `elapsed_us` | A row of `pipeline_overhead`: the named stage of the run, and the wall-clock it spanned. |
| `finding_id` | In a `headline.top_actions` row, the finding the action's reasoning is in — so the headline's advice can be read back to the evidence that chose it. |
| `replayed_delta_us` | `UX-1276`: in the builders row of `headline.top_actions`, the replayed wall at this run's builders minus at the count the step quotes (`capacity_recommendation.sweep`) — a replay with no contention, not a measured saving. |
| `first` | In a `batch_opportunities.serialized_pairs` row, the element that ran first of a pair that shares a dependency chain; `then` is the other. The pair is why they cannot be batched. |
| `shared_consumers` | In a `consolidation_candidates` row, the elements that always consume the candidate group together — the reason it is a group. |
| `utilization_envelope`, `capacity_cores`, `busy_cores`, `busy_share` | Cores busy over the build against the smaller of `builders x max-jobs` and the host's cores (`UX-676`). The capacity is the smaller because a four-core host can never deliver sixteen, and a share against a number nothing can reach is not a verdict. `busy_cores` is the interval's own reading; `busy_share` is it over `capacity_cores`. |
| `underutilized_intervals`, `overcommitted_intervals`, `lost_core_seconds` | The windows that violate the envelope, ranked and capped at forty. Under-utilized is one whole core idle while Plane 1 says there was work; overcommitted is load above the core count or a page written to swap. `lost_core_seconds` is the idle capacity times the window, which is what the ranking is by. |
| `duration_resolution` | The elements this capture's epsilon grid published as zero (`UX-740`). Quantization rounds a span lying wholly inside one rounding bucket to a single grid point, so its duration and every share computed from it are zero - unmeasurable at this resolution, not instantaneous. Carries `epsilon_us`, the element names and the task keys. Absent when the run had none, so "nothing was erased" and "the tool does not check" stay distinguishable. |
| `building`, `ready_not_dispatched`, `just_finished`, `successors_waiting` | In an interval row, what Plane 1 says was going on: the elements overlapping the window each with its own `max_jobs`, those dependency-ready and not dispatched for the whole of it, those that finished inside it, and the successors those unblocked that had not started. Which of the first two explains the idle core is `UX-677`'s question, not this table's. |
| `start_offset_us` | In an interval row, how long after the run started the window opens (`UX-823`) - the figure the From column draws; `start_us` stays the wall-clock base the Perfetto link needs. |
| `start_us`, `load1` | In an interval row, where the window starts on the build's own wall clock, and the host's one-minute load average through it — runnable *and* uninterruptible tasks, which is what separates a busy machine from a blocked one. |
| `allows` | In a `capacity_recommendation.constraints` row, how many builders that one ceiling permits, beside the `name` of the ceiling and the `reason` it was measured. A ceiling with no measurement behind it is absent rather than infinite. |
| `clamped_from` | In the CPU row of `capacity_recommendation.constraints`, the raw builder count before it was capped to `host_cpu_count` (`UX-861`) - present only when `allows` was clamped down to the host's own cores. |
| `realizable_saving_us` | What removing this element entirely takes off the **makespan** — not off the path. In a `critical_path_detail` row and in a finding's `evidence.rows`, where the two differ whenever something else is ready to take the freed time. |
| `elided`, `resolved` | In a `provenance` (or `compare/v2` `verdict_provenance`) evidence row: the shape a path held where the value was a container — `object[1202]`, `array[15]` — published instead of copying that population in twice, and `false` where the path did not resolve at all, so a broken reference is visible rather than missing. |
| `groups`, `omitted_zero_savings_groups` | In `batch_opportunities`, beside `serialized_pairs`: candidate groups the same capped pool simulated a real combined saving for, and those it simulated at zero, kept visible rather than dropped (`UX-1031`). |
| `phases` | In `pipeline_overhead`, BuildStream's own named stages (query cache, resolving elements, …) — a closed vocabulary BuildStream declares, not run-scaled. |
| `cpu_disagreements` | In `plane2_coverage`, elements where the two planes' own CPU readings disagreed past the tolerance — capped at eight. |
| `critical_path_cached` | In `confidence`, the critical-path elements BuildStream itself reported cached — a subset of the path, no run-scaled cap. |
| `shorter_than_bst` | In `timestamp_agreement`, tasks Plane 2 measured shorter than BuildStream's own span for the same task — a subset, no cap. |
| `plane1_only_with_impact`, `undeclared_plane2_elements` | In `element_join_coverage`, elements only one plane saw that still carry a published finding, and elements Plane 2 measured that BuildStream's own manifest never declared. |
| `aggregating_dependencies` | The Plane 2 half of an `element_join` row (`correlate/v2`'s `ElementJoin`): dependencies this element's own redundancy folded together. |
| `recommended_deferrals` | In `deferrability`, elements a later build could safely postpone — a subset of elements, no cap. |
| `graph_elements`, `build_us`, `assembling`, `bump_blast_elements` | In `by_junction` (`UX-1327`): the graph's element count, and in a row the BUILD tasks' summed time (work, not wall clock), the elements of a kind that assembles beside `building`, and what bumping that junction rebuilds - every element behind the prefix, nested ones too, plus their downstream closure; `null` for the top project. `built` is an element with a BUILD task in this run, `cached` one without. |
| `staged_at` | In a `resource_blast.rows` entry, the elements the shared resource was staged at, beside `direct_elements` and `blast_elements` — no run-scaled cap. |

`compare/v2`:

| key | what it is |
|---|---|
| `baseline_run_id`, `candidate_run_id` | The run id of each side, so a verdict can be traced to the two captures behind it. |
| `verdict` | One of `improved`, `regressed`, `no significant change`, `within the baseline set's own observed range`, `different work` or a `not comparable (...)` refusal. `different work` (`UX-1323`): the runs built different element sets and no element in both moved past the threshold, so the total moved only through work one run did; a gate switching on the string must handle it. |
| `deltas` | The run-level signed changes — makespan, contention, serialization and the rest, each `candidate - baseline`. |
| `attribution_deltas` | The same, per wait category: `baseline_us`, `candidate_us`, `delta_us`, and each as a share of its own run's total — `baseline_share`, `candidate_share`, `delta_share` — since a category can grow in absolute time and shrink there, which is why both are published. |
| `element_deltas` | Every element in either run with its duration on each side and the signed change, ranked by what moved most. Deliberately **not** banded. |
| `cache_churn` | How many cache keys moved: `comparable_elements` as the population, then `unchanged_keys` and `changed_keys` out of it. |
| `baseline_confidence`, `candidate_confidence` | How much of each run the comparison could see — the share of its elements carrying what the verdict is computed from. |
| `low_confidence` | True when either share is below the floor: the verdict stands, over a partly-read run. |
| `presence` | In an `element_deltas` row, whether both runs had this element. One that is in a single run has no delta at all — reading it as a change from zero would make a removed element the run's biggest improvement. |
| `mismatches` | Fields where the two captures' conditions differ, one row of `field`, `baseline`, `candidate` — a comparison across machines says so rather than hiding it. |
| `failed_runs` | Runs in the pair that did not finish, named rather than silently compared. |

`blast/v2`:

| key | what it is |
|---|---|
| `resolved_as` | Which reading of the target the command used — `junction`, `url`, `path` or `element`. Published because the order is a heuristic. |
| `junction` | The junction the target is (`name`, `source_kind`, `url`, `checkout`, `behind_count`), or whose local checkout a path is inside (`name`, `checkout`, `identity`, `resolved`); `null` otherwise. |
| `read_from` | `run`, or `project` when `--no-cost` found no snapshot and read `bst show` instead (`UX-1326`). |
| `project_targets` | The targets that `bst show` read — `[]` is every element, BuildStream's default; `null` from a run. |
| `also_matched` | The other readings that would also have matched, so a deterministic pick is not a silent one. |
| `keying` | How the matched resource is keyed (`url`, `ref`, …) when the target resolved as a repository. |
| `direct_elements`, `direct_count` | The elements that depend on the target directly. The first hop only. |
| `blast_elements`, `blast_count` | Everything a change here rebuilds, transitively — the number that makes a small element expensive to touch. |
| `building_count`, `assembling_count` | That closure split: the ones doing real build work, and the ones that only gather what is below them. |
| `by_element_kind` | The same closure counted by BuildStream element kind. |
| `measured_elements` | How many of the affected elements have a recorded duration. The rest are counted, never estimated. |
| `element_count` | Elements in the project, as the denominator for the reach above. |
| `has_inventory` | Whether the run carried a source inventory; without one, a url or path target cannot be resolved. |
| `element_exists` | Whether an element-named target is in the graph at all — so "rebuilds nothing" can be told from "is not there". |
| `did_you_mean` | When an element-named target is not in the graph: the junction-qualified elements whose last `:` component is the name given (`UX-1330`); empty otherwise. Permitted rather than required, and written on every answer (`UX-629`). |

`correlate/v2`:

| key | what it is |
|---|---|
| `note` | What the join is and what it refuses: the key it joined on, why an element may appear in one plane only, and that the two timelines are not merged. |
| `attribution_unreliable` | The producer's own note, when it says its element names are fiction. Set, the join is refused rather than rendered (`UX-56`). |
| `attribution_partial` | The same note when the names are real but do not cover every process. The join is rendered with its coverage stated (`UX-66`). |
| `granularity` | Elements paying more sandbox tax than they spend building. |
| `cached_shape` | The cached-build verdict (`UX-684`): the share of `--cache-logs`'s recorded changes whose element's weighted blast is at or under the graph's own median, and which elements dominate the expected cost. Each dominant element carries `height`/`weight_us` and an `advice` naming which one leads its own dominant peers - "split the tall chain" when height leads, "isolate the heavy element" when weight leads or the two tie (`advice` is never absent). The `sentence` states height and weight as two figures every time, and adds that the named element is "also the tallest" when it leads both. Absent, not a hedged verdict, without a change history or below `MIN_CO_REBUILDS` recorded changes. |
| `process_count_distribution` | How many processes each element ran, across this capture. Heavy-tailed: one element with 40,000 processes is the finding. |
| `envelope_bytes` | In a `memory_envelope.projections` row, the memory that many concurrent builders would need — bounded by the elements whose peak was actually measured, so it is a floor over what was seen and not a model. |
| `sandbox_tax_distribution` | How this capture's sandbox tax is spread, over every payer — "is this element's tax unusual" has no answer without the population. |

`store/v1` and `store-aggregate/v1`:

| key | what it is |
|---|---|
| `shown` | Rows in `snapshots` here. Below `count` when the reader asked for a window — `bga view` does, a listing does not. |
| `total_bytes` | What the snapshots weigh on disk, together; per class inside `host_classes`. |
| `store_bytes` | What `.bga/runs` weighs, published at the document level rather than inside `blended` (`UX-300`). |
| `snapshot_bytes` | The per-run size as a distribution over finished runs, not a single number. |
| `cache_hit_rate` | Cache hits as a share of lookups — per run in `snapshots`, as a distribution in `host_classes`. |
| `host_class` | CPU model, core count and memory joined into the one label two runs must share to be aggregated (`UX-186`). |
| `host_classes` | One entry per class. Durations are never scaled across classes. |
| `blended` | One distribution across every class. `null` unless the store holds a single class, or `--blend` was passed and the mixed claim taken deliberately. |
| `stamps`, `stamps_total` | Which snapshots a figure came from — the most recent `STAMPS_MAX` of them — and how many there are in all (`UX-528`). |
| `excluded` | What was left out and why, counted by reason: "we had nine runs" and "we had nine and threw two away" are different claims. |
| `resource_shortfall` | Present instead of `cores_busy` and `peak_rss_bytes` where no run in the class carries them (`UX-296`). |
| `bga_tail_us` | What the tool itself spent after the build, summed from that snapshot's `tail.json` — per run in `snapshots`, as a distribution in `host_classes` and `blended` (`UX-1078`). Absent before the file existed. |
| `build_wall_us` | The build subprocess's own wall, from the same `tail.json`: the figure `bga_tail_us` sits beside (`UX-1078`). |
| `build_rate`, `per_day` | `UX-1276`: builds of this project a day, as `.bga/config`'s hand-edited `builds_per_day` declares it, with `source` saying so — never counted from snapshot stamps, which count captures. Absent when undeclared; the decision panel prices a saving in agent-hours a day only beside it. |

`capacity-model/v1`:

| key | what it is |
|---|---|
| `service` | The service-time moments this class's queue is modelled from: `samples`, `mean_us` and `stdev_us`. The mean, not the median — waiting is a function of the mean and the spread around it. |
| `excluded_runs` | Captures left out of every service time — failed, interrupted, suspended or unfinished. Counted, so a thin model says why it is thin. |

`tail/v1` — `tail.json` beside each snapshot, written by `bga snapshot` after every phase of its tail (`UX-1078`):

| key | what it is |
|---|---|
| `phases` | One row per phase the tool ran after the build, in order: `name`, `wall_us`, `peak_rss_bytes` (the process's high-water mark reset at the phase's start, `null` off Linux) and the `calls` it made. A phase that did not run has no row. |
| `complete` | Whether the tail ran to its end; `false` is one interrupted after the rows it holds. |

`sweep/v1`:

| key | what it is |
|---|---|
| `makespan_us` | In a `sweeps` row, the makespan the replay produced at that capacity, beside the `capacity` vector tried and the `normalized_improvement` that capacity bought over the point before it. |

### Inside a published block (`UX-909`)

The blocks above are objects, and a reader meets their scalars
directly — `floors.certified_headroom` is the number Key Findings
leads with. Those scalars were outside the guard's population until
`UX-909`: 305 of them, including every `floors` key `UX-891` added.
They are one line each here, on the same terms as the rows above.

`analyze/v7` — `floors`, the lower bounds this run certifies:

| key | what it is |
|---|---|
| `t_c` | The makespan a replay of this run's recorded work produces. A check on the model behind the floors, not a prediction. |
| `model_slack` | How far that replay sits above the lower bound — the model's own slack, published so it cannot be read as headroom. |
| `t_infinity_cold` | The critical path with cached elements costed at what building them would take. Advisory: it rests on other runs' durations, so it certifies nothing here. |
| `cold_partial` | Whether some elements had no duration to draw on, making the cold path partial rather than complete. |
| `cold_confidence` | How far the cold path can be trusted — it is only as good as the history its durations came from. |
| `cold_duration_sources`, `cold_critical_path_duration_sources` | Where each cold duration came from, by tier; the second narrowed to the elements on the cold path. |
| `capacity_model_note` | What these floors certify against, in words — and what they do not. |

`analyze/v7` — the run-level blocks' own scalars:

| key | what it is |
|---|---|
| `untracked_head_us`, `untracked_tail_us` | In `attribution`: wall-clock before the first tracked task started and after the last one finished — BuildStream's own startup and teardown, outside per-task tracking. |
| `horizon_start_us`, `horizon_end_us` | In `occupancy`: where the slot-time accounting starts and ends, offset from the run's own zero. Beyond the end nothing was scheduled, so nothing is counted. |
| `resource_occupancy`, `peak_resource_occupancy` | Occupancy per resource kind, and the most in flight at once per kind — so a saturated fetcher is not averaged away by idle builders. |
| `top_blast_radius`, `blast_radius_ranked_by` | In `elements`: the elements whose change rebuilds the most, in that order, and what the order was computed from (`measured-rebuild-time` weights each dependent by its duration here, `downstream-count` counts them). Not the order to fix things in — that is `optimization_horizon`, and the two legitimately disagree. |
| `average_depth`, `peak_depth`, `nonzero_fraction` | In `ready_queue`: elements ready with nowhere to run, averaged and at peak, and the share of the build spent with anything waiting. High means capacity bound, not graph bound. |
| `overlap_us`, `fetch_prefix_us`, `build_suffix_us`, `fraction` | In `fetch_build_overlap`: wall-clock where fetching and building ran together, the fetching prefix with nothing building, the building suffix with nothing left to fetch, and the overlap over the span the two phases covered. |
| `deferrable_count` | In `leaf_analysis`: leaf elements nothing else waits on, which could be built later or not at all. |
| `total_deferrable_work_us` | In `deferrability`: work that could be moved out of this build without anything waiting for it. |
| `serial_chain_length` | In `bottleneck`: the longest run of elements that must go one after another. |
| `total_us`, `fraction_of_horizon` | In `pipeline_overhead`: time BuildStream spent outside any element — loading, resolving, cache queries — and that time as a share of the run. No builder count reduces it. |
| `chain_bound_share`, `chain_share_of`, `certified_headroom_us`, `scheduling_gap_us` | In `headline`: the threshold `chain_share` is compared against, which span it is a share of (`task_horizon`, published rather than left to guess), the headroom repeated from `floors` so the decision needs no second lookup, and wall-clock beyond the critical path. |

`analyze/v7` — the graph's shape, in `graph_metrics`, `graph_summary`
and `parallelism`:

| key | what it is |
|---|---|
| `max_depth` | The longest chain of dependencies, counted in edges. |
| `avg_fanin`, `avg_fanout` | Direct dependencies and direct dependents per element, averaged — equal by construction, since every edge is one of each. |
| `avg_parallelism` | Elements that could run at once, averaged over the graph's levels. |
| `serialization_share` | How much of the graph has to run one thing after another. |
| `cyclomatic_complexity` | Edges minus elements plus one — how tangled the graph is. |
| `bottleneck_count`, `deferrable_leaves` | In `graph_summary`: elements everything funnels through, and leaf elements nothing downstream waits on. |
| `best_case_speedup` | How much faster an unlimited-capacity replay of this graph would be. A multiplier, and a ceiling rather than a plan. Published in `graph_summary` and in `sensitivity`. |
| `min_width`, `max_width`, `mean_width`, `width_uniformity` | In `parallelism`: the narrowest and widest levels, elements per level averaged, and how evenly that width is spread. Low uniformity means the graph pinches somewhere. |
| `critical_path_us`, `total_improvable_time_us` | In `sensitivity`: the chain's duration, which the savings are measured against, and how much of it sits in elements that could move. |
| `deepest_depth`, `deepest_path`, `deeper_than_three`, `deeper_than_three_share` | In `document_shape`, measured on the document as published: how far down its deepest leaf sits, one path that reaches it (`[]` for a list step), and the leaves more than three levels down as a count and a share. |

`analyze/v7` — `cache`, what this run built and what it restored:

| key | what it is |
|---|---|
| `built_elements`, `cached_elements`, `hit_share` | Elements built, elements restored, and restored over considered. |
| `transfer_us`, `transfer_share` | Wall-clock moving artifacts rather than making them, keyed by direction, and that sum over the run's wall-clock. Summed over task duration, so two concurrent pulls count twice — the question is how much pulling the build did, not how long the pull window was. |
| `transfer_window_us` | The wall-clock those transfers occupied, as a union of their spans rather than a sum — the denominator a throughput needs. |
| `transfer_bytes`, `transfer_rate_bytes_per_s` | What the host moved while the build ran, and `transfer_bytes.total` over `transfer_window_us`. BuildStream reports no byte count, so these are the host's own interface counters over the build's span: on a shared machine an upper bound, loopback excluded. The rate says whether more bandwidth would help or the object count would be slow on any link. |
| `target_closure` | The same question restricted to what the target actually needs. |

`analyze/v7` — `utilisation`, where the run's slot-time went:

| key | what it is |
|---|---|
| `cpu_accounting_available` | Whether the run recorded enough to account for its slot-time at all. When false every figure below is absent, not zero. |
| `effective_cpus`, `effective_cpus_source` | The capacity this accounting divides by — builder slots as recorded, not host cores — and how it was established. An assumed capacity makes every share below assumed. |
| `wall_clock_us`, `capacity_cpu_us` | The span this accounting covers, and the slot-time available across it: wall-clock times the capacity, the denominator of the shares. |
| `total_accounted_us`, `unaccounted_us`, `reconciliation_error_share` | The buckets summed, the slot-time no bucket claimed, and that gap as a share of capacity. The honesty check on the whole block: near zero means the buckets really do cover it. |
| `potential_oversubscription`, `oversubscription_evidence` | Whether this accounting hints the run asked for more than it could get, and what the hint rests on — including the case where there was not enough to say. A hint, not the capacity verdict. |
| `max_observed_concurrency` | The most tasks seen running together in this accounting's own view of the run. |
| `idle_share`, `wasted_share` | Slot-time with nothing to run — bounded below by the graph's shape, so never entirely recoverable — and slot-time spent on work then thrown away. The second is the recoverable share. |

`analyze/v7` — `utilization_envelope`, cores busy from the host's own
`/proc/stat` series:

| key | what it is |
|---|---|
| `absence` | Why there is no envelope, in the sentence the terminal and the page both print. `null` when there is one. |
| `configured_capacity_cores` | `builders` times `max-jobs` — what the scheduler was allowed to start. `null` when the capture recorded neither. |
| `busy_cores_p50`, `busy_cores_p95` | Median cores busy and the peak worth acting on, nearest-rank over the intervals rather than the single highest sample. |
| `busy_share_p50`, `busy_share_p95` | Both against the capacity that could actually be reached. |
| `underutilized_share`, `overcommitted_share` | Share of the sampled build holding at least one idle core while Plane 1 says there was work, and share with load above the core count or a page written to swap. |

`analyze/v7` — `confidence`, `capacity_verdict` and
`capacity_recommendation`:

| key | what it is |
|---|---|
| `primary` | How much of this run's own record supports the conclusions above — coverage, provenance and model fit combined. |
| `coverage_score`, `task_coverage` | How much of the run the record accounts for, and the share of tasks carrying the timings this analysis needs. A high score on a thin record still means the record was thin; tasks without timings are excluded, never assumed. |
| `model_score`, `provenance_score` | How closely the replay reproduced the run it models, and how much of what this report claims resolves back to a published field. |
| `task_count`, `failed_task_count`, `failed_task_us` | Tasks recorded at all, tasks that failed, and the wall-clock they took. A failed run is not a slow run, and the two must not be read together. |
| `explained_untracked_us` | How much of the untracked time this report can account for. |
| `undersubscribed`, `skipped_inputs` | In `capacity_verdict`: whether the host could have served more parallelism than the run asked for, and the missing inputs named — so a reader can supply them rather than guess why the check said nothing. A check that did not run is inert, not passing. |
| `binding_constraint`, `builders_change` | In `capacity_recommendation`: the name of the smallest of the four constraints, which is the one that changes what to do, and `recommended_builders` minus `builders`, signed. Negative means the run asked for more than something can serve. |
| `agent_sizing` | Builders, cores and memory for this host in one block, each value with the `source` section it was read off (`UX-1254`). Cores and memory are `null` without Plane 2, and `absence` says so. Memory is an upper bound: every builder peaking at once. |

`analyze/v7` — the two-plane blocks:

| key | what it is |
|---|---|
| `resolution_us`, `shortest_task_us` | In `timestamp_agreement`: the finest interval the two planes' clocks can tell apart, and the shortest task measured — the case that resolution matters most for. |
| `worst_excess_us`, `worst_shortfall_us` | The largest amounts by which one plane's duration exceeded and fell short of the other's. |
| `material_share`, `tasks_where_material` | The share of tasks, and the count, where the disagreement is large enough to change a reading. |
| `tasks_compared`, `tasks_measured`, `tasks_shorter_than_bst` | Tasks both planes recorded, tasks with a duration in both, and tasks the sandbox measured as shorter than BuildStream did. |
| `plane1_elements`, `plane2_elements`, `aggregating_dependency_pairs` | In `element_join_coverage` (and `correlate/v2`'s `coverage`): elements the scheduling record knows, elements the process capture saw inside — fewer whenever a capture was partial — and dependency pairs where one element's measurement includes another's. |
| `cpu_reconciled_processes`, `cpu_from_spine_only`, `cpu_disagreement_count` | In `plane2_coverage`: processes both planes agree the CPU of, processes only the ptrace spine saw, and processes the hook and the spine costed differently. Each disagreement is a place the two record streams differ, not an error. |
| `opens_covered_processes`, `opens_coverage` | Processes the open-file hook covered, and the share whose opened paths were recorded. Only the hook can see them. |
| `fork_only_exits`, `unmatched_ends` | Exits for a process that only ever forked, so there is no command to name, and process ends with no matching start. Non-zero in the second weakens every per-process figure. |
| `exec_chains_collapsed` | Exec chains billed to one process rather than counted repeatedly — a shell that execs a compiler is one process, not two. |
| `by_coverage` | How many processes each coverage class accounts for, keyed by the class. |
| `wall_span_us` | The window the hook was actually watching. Shorter than the build means part of it ran uninstrumented. |
| `spine_policy`, `static_census` | Whether the ptrace spine ran and over how many sandboxes — with `policy: off` every CPU figure is the hook's alone, which is a floor — and which elements could be hiding a statically-linked binary the hook can never see, read from the project's own sources before anything runs. |
| `open_records_note`, `static_binary_disclaimer` | Why a process may be missing from `max_concurrency`, and what `LD_PRELOAD` cannot see in the capture's own words. The census above bounds it; this says what is being bounded. |
| `configure_cpu_us`, `configure_share` | In `configure_phase`: CPU spent in configure work across the run, summed over processes so it exceeds wall-clock where they ran in parallel, and that as a share of all CPU Plane 2 saw. A floor, for the reason its `note` gives. |
| `unmeasured_processes`, `spine_sourced_processes` | In `cpu_time`: processes no CPU could be read from — a signal death or an exec replacement leaves no rusage behind — and how many of the measured came from the spine rather than the hook. |
| `per_element_series` | Each element's CPU rate over time, as `[t_us, cores]` points on the host sampler's tick. The totals beside it are unchanged: this says what shape a total had. A process shorter than one tick is in the total and absent from the curve, and a failed `/proc` read ends a series rather than reading zero. |

The distributions — `element_duration_distribution`,
`blast_radius_distribution`, `fan_in_distribution`, and `correlate/v2`'s
`sandbox_tax_distribution` and `process_count_distribution` — share
three:

| key | what it is |
|---|---|
| `p99` | The 99th percentile of that block's own population, nearest-rank. |
| `mean` | Its mean; on a heavy tail the mark that most needs the median beside it, which is why each block's sentence stays on the median. |
| `deciles` | The nine deciles, nearest-rank. Their own nine buckets are the internal shape of a block, and outside this coverage. |

`compare/v2` — inside a published block:

| key | what it is |
|---|---|
| `t_c` | In `baseline`, `candidate` and `deltas` (and `analyze/v7`'s `floors`): the makespan a replay of that run's recorded work produces, and its signed change. |
| `contention_us`, `serialization_us` | In `deltas`: change in time lost waiting for a busy resource, and change in time independent work spent running one after another. |
| `efficiency_share` | Change in makespan against the certified floor. Each run is measured against its own floor, so this compares two ratios and not two durations. |
| `inefficiency_ratio` | Change in the gate's ratio — the figure `--fail-on` thresholds are read against. |
| `ranked_by`, `banded`, `counts` | In `element_deltas`: what the ordering means, so a consumer does not re-sort by something else and call it the same ranking; `banded` is always `false` and published rather than left implicit, because no per-element noise band exists; and how many elements grew, shrank, stayed put, appeared and disappeared. |
| `baseline_element_count`, `candidate_element_count` | In `element_diff`: elements each run had, against which the appeared and removed lists balance. |
| `baseline_path_us`, `candidate_path_us` | Each run's critical path, so a path that moved reads beside the elements that moved it. |
| `rebuilt_in_both_count`, `rebuilt_in_both_us` | In `cache_churn`: elements that rebuilt in both runs, and what those rebuilds cost, summed over the candidate. |
| `churned_count`, `wasted_rebuild_us` | Of those, the ones whose key was unchanged — work the cache should have served — and what that churn cost. The number the block exists to put a figure on. |

`correlate/v2` and the store contracts — inside a published block:

| key | what it is |
|---|---|
| `tied_saving_us` | In `ranking`: the saving every tied element shares. When the ranking degenerates into a tie this is the one number it has left. |
| `largest_element_peak_bytes`, `at_observed_builders` | In `memory_envelope`: the heaviest single element measured, which one builder must fit no matter how few run, and the envelope's own `builders`, `envelope_bytes` and `share_of_host` at the builder count this run really used. |
| `classes` | In `capacity-model/v1`'s and `store-aggregate/v1`'s `refusal`: how many host classes the store holds. More than one is why no fleet-wide or blended figure is published. |
| `by_reason` | In `excluded`: how many runs were left out for each distinct reason. "We had nine runs" and "we had nine and threw two away" are different claims. |
| `sets`, `unstamped_runs`, `mixed` | In `contract_composition`: each distinct contract set found with how many runs carry it, runs whose producer recorded no contracts — an explicit unknown, never read as agreement — and whether more than one set is present. |
| `measured_total` | In `store_bytes`: the subset of runs that did finish, which the distributions are computed over. |
| `mixes` | In `blended`: how many host classes were mixed. 1 means nothing was. |

### What a build here costs (`UX-234`)

A store of captures is a measured distribution, and `--aggregate`
reads it as one:

```bash
bga snapshot --aggregate                 # text
bga snapshot --aggregate --format json   # a `store-aggregate/v1` document
bga snapshot --aggregate --bundles ci    # the same, over a tree of bundles (UX-900)
```

```text
Store: /home/you/project
  5 measured run(s) of 6 snapshot(s)
  1 excluded:
    1 x interrupted

  Ryzen 9 7950X · 32 cores · 64000 MB - 5 run(s)
    Duration: min 10.0s, median 12.0s, p95 30.0s, max 30.0s (MAD 2.0s, n=5)
```

Three rules decide what it will and will not say:

- **An unfinished capture is not a sample.** A failed, interrupted or
  suspended run is excluded from every distribution and *counted* where
  it was excluded — "we had nine runs" and "we had nine and threw two
  away" are different claims.
- **A mix of machines is not a distribution.** Runs are grouped by the
  host class `UX-186`'s compared fields distinguish (CPU model, core
  count, memory), and a blended figure across classes is refused: exit
  6, the same code a cross-host `bga compare` refuses with. `--blend`
  prints it anyway, which is you taking the claim rather than the tool
  making it. A capture with no host manifest is its own class.
- **Fewer than three finished runs define no distribution.** The class
  publishes a shortfall naming what is missing instead of a p95 of two
  samples.
- **A mix of contract sets is named, not refused** (`UX-253`).
  `contract_composition` lists each set of contracts the aggregated
  runs were written under, commonest first, with runs carrying no
  producer stamp counted separately as an explicit unknown. Unlike a
  host class, two contract sets are not two populations: what decides
  whether runs can be pooled is movement in the contracts this document
  *reads* (`analyze/v7`, `store/v1`), never the package version — the
  rule `bga compare` already applies to a pair.

Percentiles are **nearest-rank**: for `n` sorted samples, `p` is the
value at index `ceil(p × n) − 1`. No interpolation, so every figure is
a duration some build actually took.

`bga view`'s store trend draws the median–p95 band behind its points
from this document, and nothing at all when the store mixes host
classes — it prints the refusal instead.

### What that store would do as a queue (`UX-595`, `UX-613`)

`--capacity N,RATE` reads the same store as an M/G/c queue: `N`
builders, `RATE` builds arriving per day.

```bash
bga snapshot --capacity 4,400                 # text
bga snapshot --capacity 4,400 --format json   # a `capacity-model/v1` document
```

`bga snapshot --capacity --schema` prints the contract it stamps.

```text
  4 builder(s), 400 build(s)/day

  unknown host - 6 run(s)
    Service time: mean 703.3s, sd 105.4s, CV^2 0.02, n=6
    Utilization: 81.4% of 4 builder(s)
      assumes per_host_class, finished_runs_only, service_is_the_store,
              arrival_rate_declared, servers_interchangeable,
              steady_state
    Wait before a build starts: 300.6s
```

It is a **model, not a measurement**, and the document says so in three
ways a consumer can key on:

- **The arrival rate is yours.** A store records when builds ran, never
  when they were asked for, so `arrivals_per_day` is the number you
  passed and `arrival_rate_declared` sits on every figure resting on it.
- **Every figure names what it assumed.** `answers[].assumes` is
  recorded where each assumption entered the arithmetic, so a number
  cannot acquire one the list does not carry.
- **A refusal is a value, not a gap.** `refusal` and `shortfall` are
  written as `null` where nothing was refused, so an absent key still
  means "the producer had never heard of this". An unstable queue
  (utilization at or above 1) publishes no wait at all, because a finite
  one would be a number about a system that never reaches equilibrium.

Host classes are never blended - a queue over two service times is two
queues - so each class is modelled as if it served the whole arrival
stream, and a cross-host store exits **6** exactly as `--aggregate`
does.

### Choosing the fixes (`UX-230`)

`bga whatif` projects the build for a set of fixes you choose:

```bash
bga whatif RUN/ --element core.bst --element lib.bst
```

```text
What if these were fixed: core.bst, lib.bst
  Makespan 0.014s -> 0.004s (saves 0.010s)
  Their individual savings add up to 0.011s, which is not what they are
  worth together (0.010s) - what one fix is worth depends on the others.
```

That last line is the whole point. **Savings do not add.** One
longest-path recompute with every chosen element zeroed is the answer;
summing what each is worth alone is wrong the moment two share a chain,
and on the golden fixture the two figures already differ.

"Fixed" means the element becomes instant, over this run's measured
durations, with nothing else assumed to change — an upper bound, not a
forecast. The convention travels in every answer. A selection with an
element the run does not know, one with no measured duration, or an
empty one is **refused by name** rather than projected, and a refusal
still exits 0: it is the answer, not a failure.

The page has the same thing with checkboxes. A prefix of the published
plan is read straight from `optimization_horizon`; any other
subset is asked of the server, which runs this same projection. In an
export there is no server, so the section shows the command instead of
a control that cannot answer.

**The payload: `whatif/v1`** (`UX-295`). `--format json` stamps this
shape as its first key, and a consumer holding one reads:

| key | what it is |
|---|---|
| `run_id` | the run this projection is over |
| `selected` | the element uids you asked about, as given |
| `total_duration_us` | the run's own wall-clock, for scale |
| `convention` | the sentence every figure here depends on, carried in the payload rather than left to the reader (`UX-244`) |
| `refusals` | why no projection was made, when one was not — a list of `{check, elements, sentence}` |
| `projected` | the projection, or `null` when `refusals` is non-empty |

and inside `projected`:

| key | what it is |
|---|---|
| `baseline_makespan_us` | this run's longest path, unchanged |
| `makespan_after_us` | that path recomputed with every selected element zeroed |
| `joint_saving_us` | the difference — what the set is worth **together**, and the answer |
| `sum_of_individual_us` | what each element is worth alone, summed; published *because* it can differ, never as the answer |

Measured on the golden fixture for `base.bst`: baseline 14,000 µs,
after 8,000 µs, joint saving 6,000 µs, sum of individuals 6,000 µs —
equal here because one element cannot disagree with itself; the two
figures separate as soon as two selected elements share a chain.

A refusal is a populated answer rather than an error, and the command
still exits 0 — which is why a consumer reads `refusals` before
`projected` rather than after, and why `projected` being `null` is a
statement rather than a missing field.

`bga whatif --schema` prints the whole shape without needing a run.

### N variant builds, or one junctioned invocation (`UX-904`)

`bga variant-cost` (alias `junction-cost`) prices N separate builds of one type under
different variants against one BuildStream invocation that junctions
them together:

```bash
bga variant-cost RUN-x86/ RUN-arm/ --format json
```

Two elements in different variants are one element only when their
cache key is identical; a name is not an identity, because an asan and
a release compile of one source share a name and not a key. The runs
must declare one build type (`UX-898`); variants differ by design.
A single run, mixed build types, or a run with no cache keys is
**refused by name**, and a refusal still exits 0.

**The payload: `junction-cost/v1`.** `runs` lists each run's
`run_id`, `build_class`, `elements`, `keyed_elements` and
`pipeline_overhead_us`; `assumptions` is a list of `{id, text}` every
figure cites; `refusals` is a list of `{check, runs, sentence}`; and
`projected`, `null` on a refusal, carries:

| key | what it is |
|---|---|
| `shared` | `{cache_key, elements, duration_us}` per key two or more runs share; built once, at its longest measured duration |
| `shared_closed_downward` | whether every dependency of a shared key is shared too |
| `shared_work_saving_us` | build work the N runs repeated on shared keys |
| `pipeline` | per phase: `phase`, `sum_us` paid N times, `max_us` paid once, `saving_us` |
| `pipeline_saving_us` | the phases' savings summed — an upper bound |
| `saving_us` | the two savings together — an upper bound |
| `separate_floors_us` | each run's own T∞, in run order |
| `union_floor_us` | T∞ over the N graphs merged at shared keys |
| `one_invocation_lower_bound_us` | the pipeline paid once plus `union_floor_us` |
| `junction_staging_us` | `null`: staging the subprojects is not measured, and the bound excludes it |
| `overlap` | the shared set in one sentence, including when it is empty |

With no shared key the build-work saving is zero and `overlap` says so;
the pipeline term is then all that remains, and it is an assumption.
A re-capture of the junctioned invocation is still the ground truth.

### Why this one is ranked first (`UX-227`)

Each top action in the decision panel carries a **Why #n** fold: the
rule that ranked it (read from that finding's `provenance` record), what
this run measured about the element, the findings that name it, and how
it has moved across the store.

Every value in the fold carries the path it was read from in
`data-field` — for example
`critical_path_detail[element_uid=core.bst].share_of_path` — in
the same grammar `provenance.evidence[].path` uses. Nothing in the fold
is derived; it is the document, gathered under one question.

### The chain behind every claim (`UX-229`)

Every claim the report makes — the diagnosis, each finding, each top
action — carries a **provenance record**: the published fields it was
read from, the rule that fired, and the trace query that deepens it.

```text
claim -> evidence (field refs) -> rule -> trace query
```

`--explain` prints the chain under each claim in the terminal:

```bash
bga analyze RUN/ --explain
```

```text
  This build is scheduler-bound, not chain-bound: the critical path is
  88% of wall-clock, so the time is going somewhere other than the chain.
    why: The critical path is 87.5% of the task horizon (the span from
         the first task's start to the last one's finish, excluding
         BuildStream's own startup), below the 90% line at which the
         chain rather than the scheduler is called the constraint, so
         this build is scheduler-bound.
    rule: CHAIN_BOUND_RATIO = 0.9 (<, bga/findings.py)
      floors.t_infinity_observed = 14000
      total_duration_us = 16000
      headline.chain_share = 0.875
    deeper: trace query `element-time`
```

The same object is in the JSON at `headline.provenance` and
`findings[].provenance`, and the page renders it folded under each
claim:

- `evidence[]` — each entry is a `path` **into this same document** plus
  the `value` found there, so a reader follows the reference rather than
  trusting the quote. Paths are dotted keys, `[i]` for a list index and
  `[key=value]` for the one list entry matching it.
- `rule` — the constant that decided the claim, read live: change
  `CHAIN_BOUND_RATIO` and `rule.threshold` changes with it. `name` is
  `null` where a claim has no threshold, which is a different statement
  from a threshold of zero.
- `trace_query` — the `bga timeline` question that deepens it, or
  `null`. This mapping used to live only in the viewer.
- `unpublished_inputs` — fields a claim was genuinely drawn from that
  this document does not carry. Named rather than omitted: silence
  would read as no gap.
- `document` — which schema the paths walk. Load-bearing when a record
  travels: `bga compare --format json` carries the candidate run's
  chain at `candidate_diagnosis`, and its paths resolve against that
  run's `analyze/v7`, not against the comparison.

A top action's provenance is a **pointer** (`see`) at the finding's
record, because the action is already a reference to that finding.

`bga compare --format ci-comment` cites the same record in a folded
*Why the candidate looks like this* block, so a reviewer asking "why do
you say that" gets the answer in the comment rather than in another
command's output.

### The two-plane join, published (`UX-215`)

`bga correlate --format json` has emitted the join since `UX-51`. It
was unversioned until round 25 — no `schema` stamp, no view-hints,
served by nothing — so the one place where *"this element is on the
path, is worth 12.05s, and was pinned to one job on four cores"* is a
single row was invisible to `bga view`, to CI and to every external
consumer. It is `correlate/v2` now, with no change to what it computes.

```bash
bga correlate @last --schema | jq '.properties.elements["bga:columns"]'
bga correlate @last --format json | jq '.elements[] | select(.on_critical_path)'
```

One row per element, from both planes:

| | |
| --- | --- |
| Plane 1 | `on_critical_path`, `critical_path_share`, `potential_saving_us`, `saving_share`, `blast_radius` |
| Plane 2 | `cores_busy`, `cpu_coverage`, `requested_jobs`, `resolved_jobs` (`UX-894`: the width BuildStream resolved for the element, read from the run's graph document, where a non-parallel element is a width of one and not a missing value), `jobs_denominator` (which of the two widths the achieved ratio divided by, or absent when no ratio was computed), `peak_rss_bytes`, `dominant_binary`, `serial_binary` |

`bga analyze --plane2 PLANE2.json` now carries the same rows as
`element_join`, from the same function — so the report and the command
cannot describe an element differently. Without `--plane2` the key is
**absent**, not empty: with one plane there is no join, and its Plane 1
half is already in `signals`.

Two refusals the document keeps rather than smoothing over:

- An element Plane 2 never saw is a row with its Plane 1 half and no
  Plane 2 numbers — not zeros, which would read as *"measured, and
  idle"*.
- An element Plane 2 named that Plane 1 never declared (`declared:
  false`) is listed, because hiding it would hide a real disagreement
  between the planes, and it never carries a recommendation (`UX-66`).
