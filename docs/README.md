# Documentation

Start here: find the job, open the one page beside it.

| I want to… | read |
|---|---|
| **try it** in 30 seconds, no BuildStream needed | [the project README](../README.md#quick-start-30-seconds-no-buildstream-needed) |
| **optimise a real project** — capture, read, fix, prove | [`guides/real-project.md`](guides/real-project.md) |
| **run a pilot in CI** — the script, and every switch in one table | [`guides/pilot.md`](guides/pilot.md) |
| **gate pull requests** — baselines, the noise band, the PR comment | [`guides/ci-comment.md`](guides/ci-comment.md) |
| **share a capture** with another machine, or a pseudonymised one with an outside reader | [`guides/cli.md`](guides/cli.md#carrying-a-capture-to-another-machine-ux-520) |
| **read the report**, and know when to drop into Perfetto | [`guides/what-the-viewer-answers.md`](guides/what-the-viewer-answers.md) |
| **pair `--jobserver auto`** with a builder count | [`guides/jobserver.md`](guides/jobserver.md) |
| **see it change a real build** | [`cases/serial-giant-jobserver.md`](cases/serial-giant-jobserver.md) |
| **look up a command** — `analyze`, `snapshot`, `bundle`, `junction-cost`, `cache-trend`, the section-only `graph`, `floors`, `replay`, `sweep`, `utilisation` and `diagnostics` — its flags and exit codes | [`guides/cli.md`](guides/cli.md) |
| **look up a contract** — every schema id `bga` writes or reads | [`guides/json-contracts.md`](guides/json-contracts.md) |
| know **what must be true** — the v9 specification, Parts 0-44, invariants `I1`-`I13` | [`spec/specification.md`](spec/specification.md) |
| understand **why it works this way** — the three planes as one system | [`design/architecture.md`](design/architecture.md) |
| know **who it serves**, and what it declines | [`design/roles.md`](design/roles.md) |
| change **the page** — its visual contract | [`design/styleguide.md`](design/styleguide.md) |
| **work on this repository** | [`contributing/fixing-guide.md`](contributing/fixing-guide.md) |
| see **what was found, and when** — every round and review | [`audits/README.md`](audits/README.md) |
| find **what is still open** | [`backlog/scenarios/README.md`](backlog/scenarios/README.md) |
| know **what changed** since the `bga` you installed | [`CHANGELOG.md`](../CHANGELOG.md) |

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

The rules that keep this tree arranged are in
[`contributing/style-guide.md`](contributing/style-guide.md). Five of
them are enforced by
[`tests/unit/test_docs_links_and_commands.py`](../tests/unit/test_docs_links_and_commands.py).
