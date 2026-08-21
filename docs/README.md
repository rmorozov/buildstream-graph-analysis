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

New to `bga`? The [project README](../README.md) has a 30-second start
that needs no BuildStream. Then
[`guides/real-project.md`](guides/real-project.md) is the end-to-end
path on a real project.

On a real project the two commands to know first are `bga doctor`
(`UX-125` — can this machine capture at all, before a build proves it
cannot) and `bga snapshot` (`UX-126` — the whole local loop, run twice).
Both are in [`guides/cli.md`](guides/cli.md#bga-snapshot--the-local-loop-ux-126).
`bga view` (`UX-193`) opens the same report in a browser, and
`bga view --export` writes it as one file you can attach.

Three planes of evidence, and they cost different things to obtain —
which is why the guides pick between them rather than always saying
"capture everything":

| plane | what it sees | what it costs |
|---|---|---|
| **1** — one run's element-level log | the whole schedule, the critical path, the floors | a log; the analysis needs no live BuildStream |
| **2** — processes inside a sandbox | what one element's own build system actually did | a real `bst` + `bwrap` build you decided to capture |
| **3** — BuildStream's own kept logs | history: what this project keeps spending time on | nothing — `bga cache-logs` reads what is already on disk |

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
| [`guides/cli.md`](guides/cli.md) | every command, flag and exit code | reference |

### Case studies

Records of real sessions, kept verbatim. They are evidence, not
instructions — their commands are the ones those rounds ran, not the
ones to run today (`UX-139`).

| document | what it records |
|---|---|
| [`audits/case-study-06-macro-micro.md`](audits/case-study-06-macro-micro.md) | the macro-then-micro cycle, **including where the tool did not guide the user** |
| [`audits/optimization-walkthrough-04.md`](audits/optimization-walkthrough-04.md) | the retired `sleep N` proxy walkthrough, kept for provenance |

## Specification and contracts

What must be true. The ground truth for what every number means.

| document | what it covers |
|---|---|
| [`spec/specification.md`](spec/specification.md) | the v9 specification — Parts 0-40, invariants `I1`-`I13` |
| [`spec/ingestion-pipeline.md`](spec/ingestion-pipeline.md) | how real BuildStream output maps to the schema, with the empirically confirmed facts behind it |

## Design

Why it is this way. Arguments and structure, not instructions.

| document | what it covers |
|---|---|
| [`design/architecture.md`](design/architecture.md) | the three analysis planes, how the ingestion path measures itself, and every extension beyond the spec |
| [`design/directions.md`](design/directions.md) | `bga` as a local helper vs `bga` as a CI gate |

## Contributing

How to work on this repository.

| document | what it covers |
|---|---|
| [`contributing/style-guide.md`](contributing/style-guide.md) | what documentation here has to do, and the two rules that are enforced by tests |
| [`contributing/fixing-guide.md`](contributing/fixing-guide.md) | the mandatory entry point for picking up a backlog task |

## Audits

What was found, and when. Append-only by nature: each round is a
timestamped record, not a statement of current state.

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
[the original spec-compliance review](audits/spec-compliance-review.md)

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
