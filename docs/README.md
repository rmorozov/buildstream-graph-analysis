# Documentation

Start here. Each folder answers one kind of question; if you know which
question you have, you know which folder to open.

| I want to… | go to |
|---|---|
| **use the tool** on a project | [`guides/`](#guides) |
| know **what must be true** of its output | [`spec/`](#specification-and-contracts) |
| understand **why it works this way** | [`design/`](#design) |
| **work on this repository** | [`contributing/`](#contributing) |
| see **what was found, and when** | [`audits/`](#audits) |
| find **what is still open** | [`backlog/`](#backlog) |

What changed between the `bga` you installed and this one is
[`CHANGELOG.md`](../CHANGELOG.md) — a release records a contract state
rather than a date (`UX-251`).

New to `bga`? The [project README](../README.md) has a 30-second start
that needs no BuildStream. Then
[`guides/real-project.md`](guides/real-project.md) is the end-to-end
path on a real project.

On a real project the two commands to know first are `bga doctor`
(`UX-125` — can this machine capture at all, before a build proves it
cannot) and `bga snapshot` (`UX-126` — the whole local loop, run twice).
Both are in [`guides/cli.md`](guides/cli.md#bga-snapshot--the-local-loop-ux-126).
`bga view` (`UX-193`) opens the same report in a browser, and
`bga view --export` writes it as one file you can attach. `bga bundle`
carries a whole capture to another machine in one file — `run/` is
only half of it (`UX-520`). Three more
answer questions the analysis alone does not: `bga whatif` prices a
chosen set of fixes (`UX-230`), `bga analyze --explain` shows the
evidence behind every claim (`UX-229`), and `bga snapshot --aggregate`
speaks for the whole store rather than one run (`UX-234`). The
section-only commands — `graph`, `floors`, `replay`, `sweep`,
`utilisation`, `diagnostics` — are `analyze`'s own sections, printable
on their own; `cache-trend` reads a series rather than a pair. All of
them are in [`guides/cli.md`](guides/cli.md).

Three planes of evidence, and they cost different things to obtain —
which is why the guides pick between them rather than always saying
"capture everything":

| plane | what it sees | what it costs |
|---|---|---|
| **1** — one run's element-level log | the whole schedule, the critical path, the floors | a log; the analysis needs no live BuildStream |
| **2** — processes inside a sandbox | what one element's own build system actually did | a real `bst` + `bwrap` build you decided to capture |
| **3** — BuildStream's own kept logs | history: what this project keeps spending time on | nothing — `bga cache-logs` reads what is already on disk |

## What it emits

Every JSON document `bga` writes carries its schema id, and
`bga <command> --schema` prints that command's contract — types, units,
and the view-hints the browser report renders from (`UX-201`). Where a
command emits two documents, the flag selects: `bga snapshot --list
--schema` and `bga snapshot --aggregate --schema` print different
contracts. Twenty-five ids, and what writes each:

| document | written by |
|---|---|
| `analyze/v6` | `bga analyze --format json` — the analysis, its findings, and why each one is believed (`UX-229`) |
| `compare/v2` | `bga compare --format json` — the verdict, the noise band, the culprit elements |
| `blast/v2` | `bga blast --format json` — what a change to one resource rebuilds |
| `correlate/v2` | `bga correlate --format json` — Plane 1 and Plane 2 joined on element uid |
| `whatif/v1` | `bga whatif --format json` — what the build drops to if a chosen set is fixed, and whether the savings add (`UX-230`) |
| `store/v1` | `bga snapshot --list --format json` — the runs in this project's `.bga/runs` |
| `store-aggregate/v1` | `bga snapshot --aggregate --format json` — the store as a distribution, per host class (`UX-234`) |
| `capacity-model/v1` | `bga snapshot --capacity N,RATE --format json` — a builder count and an arrival rate as a queue: utilization, the wait before a build starts and the number waiting, per host class, each figure carrying the assumptions its own arithmetic used (`UX-613`) |
| `sweep/v1` | `bga sweep --format json` — what more capacity would buy, the knee past which it buys little, and where the model contradicted itself (`UX-339`) |
| `host/v2` | `bga.hostinfo`, inside every `run-context.json` — which machine measured this run, and what makes two runs comparable |
| `sources/v1` | `bga extract`, at `sources.json` in a run directory — every element's sources, and how each one is keyed |
| `plane2/v3` | `bga capture`, at `plane2.json` beside a run — what Plane 2 measured about one build: run-level measurements, with the per-element reductions among them. Measured on the committed fixture, 21 of 24 top-level blocks are run-level and 3 are keyed by element uid, so a reader after the host's peak memory, the build's process count or whether the spine ran is in the right file (`UX-386`). The per-process record list `UX-297` retired is gone |
| `host-samples/v1` | `bga capture`, at `host-samples.jsonl` beside a run — the host's memory and swap while the build ran, one object per line (`UX-378`) |
| `capture-layout/v1` | the capture directory `.bga/` itself — every path it holds, what writes it, what reads it, and what an absence means. Specification 32.6 (`UX-381`) |
| `bundle-manifest/v1` | `bga bundle --export`, inside `bundle.json` in the archive — each member's path, presence and contract version, plus the `bga` that packed it, so the receiving side refuses a bundle it cannot read in full rather than half-loading it (`UX-520`) |
| `plane2/v2` | the same file as a capture before `UX-384` wrote it, with the element names of every redundancy finding embedded. Still read, never written |
| `plane2/v1` | the same file as a capture before `UX-297` wrote it, with every per-process record embedded. Still read, never written |
| `analyze/v5` | what `bga analyze` wrote before `UX-641` gave `parallelism.levels` its members rather than the row number. Still read, never written |
| `analyze/v4` | what `bga analyze` wrote before `UX-535` published the graph's shape once. Still read, never written |
| `analyze/v3` | what `bga analyze` wrote before `UX-344` lifted the `signals` and `structural` namespaces. Still read, never written |
| `analyze/v2` | what it wrote before `UX-341` unified the units — `measured_seconds`, `peak_rss_kb`, `useful_pct`. Still read, never written |
| `compare/v1` | the same, for a comparison. Still read, never written |
| `blast/v1` | the same, for a blast answer. Still read, never written |
| `correlate/v1` | the same, for the two-plane join. Still read, never written |
| `host/v1` | the host manifest with `memory_mb` where `host/v2` has `memory_bytes`. Read and converted on the way in, so an old baseline still compares — never written |

The last sixteen are written into a run directory — or, for
`bundle-manifest/v1`, into the bundle that carries one — rather than
printed by a command, so no `--schema` invocation prints them, and ten of those
are only ever *read* - they are the shapes an older store's artifacts
are in (`plane2/v1` from `UX-297`, `plane2/v2` from `UX-384`, five from
`UX-341`, `analyze/v3` from `UX-344`, `analyze/v4` from `UX-535` and
`analyze/v5` from `UX-641`). The other nine
each have a command that prints their contract, and
`tests/unit/test_every_emitted_contract_is_answerable.py` holds that
split by running both sides rather than by reading this table
(`UX-328`). Every command that prints a document now answers for it:
`bga sweep` was the last that did not, and `UX-339` gave it one. A key
may be added to
any of these without a version bump; a rename or a removal bumps. The full contract table is
[spec Part 32.5](spec/specification.md); what each command does with it
is [`guides/cli.md`](guides/cli.md).

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
input: the shapes are specified in [spec Parts 32.1-32.3](spec/specification.md).

## Words this project uses precisely

Ten that are easy to blur, pinned here so every other document can be
short (`UX-138`, extended by `UX-180` for the source axis):

| term | means |
|---|---|
| **element** | a BuildStream element — what user docs call the unit of work. The spec says "task"; that is spec vocabulary, defined there |
| **capture** | the act of recording a build, and the artifact it publishes. **Snapshot** = a capture in a project's own `.bga/runs/`, named by `@last`/`@prev` |
| **sandbox tax** | element time spent staging, integrating and caching rather than building. One name — the reports print it too |
| **cold / incremental** | the two capture *modes* (caches off / caches on). Unrelated to the **cold floor** (`bga floors --cold`), which is a structural lower bound |
| **baseline set → noise band** | the *runs* you compare against, and the *statistic* built from them (median ± k·MAD). A set of fewer than three defines no band |
| **resource** | the thing a source consumes, normalised to one identity — a repository url, or a path for content-keyed sources. Not the source, and not the element: many elements share one resource, which is what makes it worth naming |
| **blast** | the elements a change to one resource rebuilds: the direct consumers plus their downstream closure. `bga blast <target>` prices it. A question, not a gate — it always exits 0 |
| **keying: ref vs content** | what BuildStream's cache key for a source covers. **Ref-keyed** (`git`, `tar`, `pip`, …): any new ref rebuilds every consumer of that url. **Content-keyed** (`local`, `patch`): only the elements whose files changed |
| **work vs wall clock** | **work** is the summed duration of the tasks a change rebuilds (what a blast reports); **wall clock** is what the build took. They differ by whatever ran in parallel, so a blast's work is never a predicted build time |
| **building vs assembling** | **building** elements run a sandbox and cost real time; **assembling** ones (`stack`, `import`, `filter`, `junction`, `compose`, `link`) only rearrange what others produced. A blast counts both and says which is which, because forty assembling elements are not forty rebuilds |

---

## Guides

How to use the tool. These are the documents that tell you what to type.

Two journeys, one page each — then the reference.

| document | what it covers | for |
|---|---|---|
| [`guides/real-project.md`](guides/real-project.md) | a real project end to end: capture, read, fix, prove | **the local optimizer** |
| [`guides/ci-comment.md`](guides/ci-comment.md) | capture → baseline set → gates → the PR comment | **the CI owner** |
| [`guides/what-the-viewer-answers.md`](guides/what-the-viewer-answers.md) | which questions the page answers, and when to drop into Perfetto — by role | **anyone reading a report** |
| [`guides/cli.md`](guides/cli.md) | every command, flag and exit code | reference |

### Case studies

Records of real sessions, kept verbatim. They are evidence, not
instructions — their commands are the ones those rounds ran, not the
ones to run today (`UX-139`).

| document | what it records |
|---|---|
| [`audits/case-study-06-macro-micro.md`](audits/case-study-06-macro-micro.md) | the macro-then-micro cycle, **including where the tool did not guide the user** |
| [`audits/optimization-walkthrough-04.md`](audits/optimization-walkthrough-04.md) | the retired `sleep N` proxy walkthrough, kept for provenance |
| [`audits/planted-defect-walk-round-72.md`](audits/planted-defect-walk-round-72.md) | three defects **chosen first**, generated into real projects, and how far the front door gets each reader towards the planted answer (`UX-468`) |

## Specification and contracts

What must be true. The ground truth for what every number means.

| document | what it covers |
|---|---|
| [`spec/specification.md`](spec/specification.md) | the v9 specification — Parts 0-40, invariants `I1`-`I13` |
| [`spec/ingestion-pipeline.md`](spec/ingestion-pipeline.md) | how real BuildStream output maps to the schema, with the empirically confirmed facts behind it |
| [`spec/trace-dictionary.md`](spec/trace-dictionary.md) | what a slice in the Perfetto trace carries — the annotation keys, scopes, counter track and flows a canned query is written against (`UX-312`) |

## Design

Why it is this way. Arguments and structure, not instructions.

| document | what it covers |
|---|---|
| [`design/architecture.md`](design/architecture.md) | the three analysis planes, how the ingestion path measures itself, and every extension beyond the spec |
| [`design/directions.md`](design/directions.md) | `bga` as a local helper vs `bga` as a CI gate |
| [`design/roles.md`](design/roles.md) | the role model — eight roles, their contradictions, and the gap analysis |
| [`design/styleguide.md`](design/styleguide.md) | the web report's visual contract — shape→control mapping, drawings, color and emphasis budget, dark first |

## Contributing

How to work on this repository.

| document | what it covers |
|---|---|
| [`contributing/style-guide.md`](contributing/style-guide.md) | what documentation here has to do, and the two rules that are enforced by tests |
| [`contributing/fixing-guide.md`](contributing/fixing-guide.md) | the mandatory entry point for picking up a backlog task |
| [`contributing/release-guide.md`](contributing/release-guide.md) | how a release is cut: the contract state it records, and the version derived from it |

## Audits

What was found, and when. Append-only by nature: each round is a
timestamped record, not a statement of current state.

Two of them are not rounds. They stand outside the sequence and are
appended to instead of superseded:

| document | what it records |
|---|---|
| [`audits/architecture-review.md`](audits/architecture-review.md) | every architecture and documentation review the `UX-241` cadence has called, newest last — **append-only**, so a superseded finding stays where it was written and the review after it says so |
| [`audits/spec-compliance-review.md`](audits/spec-compliance-review.md) | the original review of the tool against its specification, before the round sequence began |

The rounds themselves:

[`audits/round-2.md`](audits/round-2.md) ·
[3](audits/round-3.md) ·
[4](audits/round-4.md) ·
[5](audits/round-5.md) ·
[6](audits/round-6.md) ·
[7](audits/round-7.md) ·
[8](audits/round-8.md) ·
[9](audits/round-9.md) ·
[10](audits/round-10.md) ·
[11](audits/round-11.md) ·
[12](audits/round-12.md) ·
[13](audits/round-13.md) ·
[14](audits/round-14.md) ·
[15](audits/round-15.md) ·
[16](audits/round-16.md) ·
[17](audits/round-17.md) ·
[18](audits/round-18.md) ·
[19](audits/round-19.md) ·
[20](audits/round-20.md) ·
[21](audits/round-21.md) ·
[22](audits/round-22.md) ·
[23](audits/round-23.md) ·
[24](audits/round-24.md) ·
[27](audits/round-27.md) ·
[40](audits/round-40.md) ·
[41](audits/round-41.md) ·
[43](audits/round-43.md) ·
[44](audits/round-44.md) ·
[45](audits/round-45.md) ·
[46](audits/round-46.md) ·
[63](audits/round-63.md) ·
[64](audits/round-64.md) ·
[74](audits/round-74.md) ·
[75](audits/round-75.md) ·
[76](audits/round-76.md) ·
[77](audits/round-77.md) ·
[78](audits/round-78.md) ·
[79](audits/round-79.md) ·
[80](audits/round-80.md) ·
[81](audits/round-81.md) ·
[82](audits/round-82.md) ·
[83](audits/round-83.md) ·
[84](audits/round-84.md) ·
[85](audits/round-85.md) ·
[86](audits/round-86.md) ·
[87](audits/round-87.md) ·
[the guard census of round 64](audits/guard-census-round-64.md)

## Backlog

What is still open, and the record of what closed.

| document | what it covers |
|---|---|
| [`backlog/scenarios/README.md`](backlog/scenarios/README.md) | the `UX-*` backlog — usability and workflow work, each item with real before/after evidence |
| [`backlog/tasks/`](backlog/tasks/) | the `P*` backlog — spec-compliance work, complete |
| [`backlog/progress-tracker.md`](backlog/progress-tracker.md) | the `P*` tracker, closed 2026-08-15 |

---

## A note on how this tree is arranged

Until round 11 these were sixteen loose files in `docs/`, and
`design/directions.md` had grown a "What the Nth round found" section
per audit until it was 1237 lines — an argument about direction *and* a
changelog. Rounds 2-6 now sit with rounds 7-10, where they always
belonged.

The rules that keep it this way, and the reason for each, are in
[`contributing/style-guide.md`](contributing/style-guide.md). Two of
them are enforced by
[`tests/unit/test_docs_links_and_commands.py`](../tests/unit/test_docs_links_and_commands.py):
every relative link must resolve, and no instructional document may tell
a reader to run `python3 -m tools.<module>` <!-- docs-style: allow-direct-module -->
instead of the installed
`bga` alias.
