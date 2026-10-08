# Changelog

What changed between the `bga` you installed and the one you have now.

A release here records a **contract state**, not a date: the
twenty-eight published contracts and the command surface as they stood, plus what
moved since the last row. The procedure is
[`docs/contributing/release-guide.md`](docs/contributing/release-guide.md)
and the argument is
[Direction 10](docs/design/directions.md).

Two things a reader should know before using the numbers:

- **The package version is provenance, not compatibility.** It says
  which build wrote an artifact. What decides whether your parser still
  works is the *contract* version — `analyze/v2` — and those move
  independently. A release that bumps the package while every contract
  stays put has broken nothing you pin.
- **Pre-1.0, `breaking` and `extending` both move MINOR**, so the row
  records which it was. The number cannot say it while the major is
  pinned at 0.
- **A row below the newest is frozen.** Its state block carries a
  `digest` of the contracts and commands it recorded, so editing a
  shipped release's state reddens the guard rather than passing
  silently (`UX-550`). The newest row carries none: it is the one the
  tree itself answers for, and when the tree moves past it the answer
  is a new row, not an edit to that one. Between cuts that new row is
  **Unreleased**: no version, the tree's state, and the kind the next
  cut would be (`UX-1078`).

The `commit` column this table used to carry is gone, for the reason
`UX-332` dropped it from the review log: the one hash it held,
`fac9618`, is a real object in the author's clone and **not an
ancestor of `origin/main`**, so it identified a commit on one machine
and nowhere else. A release row also cannot honestly carry its own
commit's hash, because the hash covers the row. The tag is the
identity (`git tag v0.3.0`), and the closed-row marker is what the
derivation actually reads.

| release | date | closed rows | kind |
|---|---|---|---|
| [0.6.0](#060--findings-that-say-what-to-do-and-a-pool-that-fits-its-cgroup-2026-10-07) | 2026-10-07 | 1280 | breaking |
| [0.5.0](#050--the-tool-prices-its-own-cost-and-the-jobserver-2026-09-29) | 2026-09-29 | 1083 | extending |
| [0.4.1](#041--the-tool-says-what-it-assumes-2026-09-12) | 2026-09-12 | 813 | patch |
| [0.4.0](#040--a-capture-you-can-carry-2026-09-03) | 2026-09-03 | 537 | breaking |
| [0.3.0](#030--every-document-says-what-shape-it-is-2026-08-27) | 2026-08-27 | 332 | breaking |
| [0.2.0](#020--the-build-that-says-what-it-is-2026-08-24) | 2026-08-24 | 243 | initial |

Every row is tagged, and every tag names the commit that set its
version and is reachable from `main`:

```text
v0.2.0  3ebe7e1b5    v0.3.0  bc1593557    v0.4.0  679b9cf87    v0.4.1  8f238642
```

`tests/unit/test_a_release_records_a_contract_state.py` reads them, so
step 8 of the release guide cannot go unexecuted again.

Round 84 recorded `0.2.0` as "never a version anywhere in the tree" and
round 86 first "corrected" that to *a lineage `main` cannot reach*.
Both are wrong: `pyproject.toml` enters this history at `4ace856`
(2026-08-13) and `0.2.0` is an ordinary release. The wrong correction
was read off a shallow clone — `UX-633`, and `UX-637` for the cause.

## 0.6.0 — findings that say what to do, and a pool that fits its cgroup (2026-10-07)

Named for the two halves most of the 197 rows went into. Every finding
now publishes the step that answers it and says whether it is new, still
open or gone since the run before (`UX-1256`, `UX-1277`); five sections
that each publish a bound are checked to agree (`UX-1253`); Plane 2's
processes reach the findings (`UX-1255`); and a binary that waits is told
from one that computes, with a per-binary CPU and wall total behind "which
binaries cost this build its time?" (`UX-1247`, `UX-1275`). The page's review
rounds took it from raw keys and floats to keyboard sort, print and Back
(`UX-1140`..`UX-1279`). On the capture side, `--jobserver
auto` reads the cgroup a container agent is capped at, opens its pool
inside that cap and takes tokens back when the jobs outgrow it (`UX-1282`,
`UX-1283`, `UX-1339`), a patched ninja joins the pool (`UX-1336`), and
junctions are first-class: Plane 2 keys a junctioned element by its full
name, `bga blast` prices a junction bump, `cache-logs` reads every
junctioned project and a run rolls up by junction (`UX-1320`, `UX-1321`,
`UX-1325`, `UX-1327`). `bga snapshot -- ./build.sh` captures a build run
through a wrapper script (`UX-1322`), and a pilot kit runs bga in a team's
CI, report-only (`UX-1288`).

**Contract delta:** `analyze/v7` - `by_binary` is one row per binary,
`{binary, cpu_us, wall_us, calls, elements}` ranked by CPU, where it was
a map of binary to calls (`UX-1247`); `analyze/v6` is read, never
written. `bga junction-cost` is renamed `bga variant-cost`, the old name
kept as an unlisted alias (`UX-1327`). A bumped contract makes this cut
`breaking`.

**Upgrade note:** a parser reading `analyze` output's `by_binary` as a map
of binary to calls reads rows now: `{r["binary"]: r["calls"] for r in
doc["by_binary"]}` gives the old shape back. Artifacts `analyze/v6` wrote
still load. Scripts calling `bga junction-cost` keep working.

**Carried findings.** Review 37 (closed-row marker 1264) filed `UX-1332`..
`UX-1334`, all closed before this cut. Walk seed 5
([`walk-seed-5.md`](docs/audits/walk-seed-5.md), on `3e3657a7`) filed
`UX-1341`, closed here, and `UX-1342` - the headline's "top 3" and the
work order name two different triples - which ships open. `UX-1343` ships
open too: the pull-request lane never installs on Python 3.9, which is
how `main`'s 3.9 cell stayed red from `057bc920` until `UX-1340`.

```text state
contracts: analyze/v2 analyze/v3 analyze/v4 analyze/v5 analyze/v6 analyze/v7 blast/v1 blast/v2 bundle-manifest/v1 capacity-model/v1 capture-layout/v1 compare/v1 compare/v2 correlate/v1 correlate/v2 host-samples/v1 host/v1 host/v2 junction-cost/v1 plane2/v1 plane2/v2 plane2/v3 sources/v1 store-aggregate/v1 store/v1 sweep/v1 tail/v1 whatif/v1
commands: analyze baseline blast bundle cache-logs cache-trend capture checkout-cost chrome-to-trace compare correlate cross-check diagnostics doctor extract floors gen-synthetic graph graph-from-show junction-cost log-to-chrome native-to-chrome rebuild-set release-notes replay run-context snapshot sweep timeline utilisation variant-cost view whatif wrap
```

### What landed

<!-- generated: UX-252 1083→1280 -->
197 scenarios closed (closed-row markers 1083 → 1280).

**contracts**

- [UX-1100](docs/backlog/scenarios/UX-1100-cut-release-0-5-0.md) — [cut release 0.5.0 once the next features are in](docs/backlog/scenarios/UX-1100-cut-release-0-5-0.md)
- [UX-1218](docs/backlog/scenarios/UX-1218-the-verification-log-re-grounds-at-round-159.md) — [the verification log re-grounds at round 159's merge](docs/backlog/scenarios/UX-1218-the-verification-log-re-grounds-at-round-159.md)
- [UX-1278](docs/backlog/scenarios/UX-1278-the-verification-log-re-grounds-at-round-165.md) — [the verification log re-grounds at round 165's merge](docs/backlog/scenarios/UX-1278-the-verification-log-re-grounds-at-round-165.md)
- [UX-1298](docs/backlog/scenarios/UX-1298-compare-publishes-where-its-band-came-from-and-what-it-skipped.md) — [`compare/v2` publishes where its band was read from and how many members it skipped for host](docs/backlog/scenarios/UX-1298-compare-publishes-where-its-band-came-from-and-what-it-skipped.md)
- [UX-1333](docs/backlog/scenarios/UX-1333-the-compare-contract-and-its-schema-prose-omit-the-different-work-verdict.md) — [the `compare/v2` schema description lists four verdicts and the code emits a fifth, `different work`](docs/backlog/scenarios/UX-1333-the-compare-contract-and-its-schema-prose-omit-the-different-work-verdict.md)
- [UX-1344](docs/backlog/scenarios/UX-1344-cut-release-0-6-0.md) — [cut release 0.6.0, breaking](docs/backlog/scenarios/UX-1344-cut-release-0-6-0.md)

**cli**

- [UX-1286](docs/backlog/scenarios/UX-1286-the-gate-reads-kept-bundles-in-place.md) — [the review gate reads its band from the bundles CI kept, without a store on the runner](docs/backlog/scenarios/UX-1286-the-gate-reads-kept-bundles-in-place.md)
- [UX-1295](docs/backlog/scenarios/UX-1295-bundle-export-has-an-anonymize-switch.md) — [`bga bundle --export` has an `--anonymize` switch, so a pilot can share a capture without a Python call](docs/backlog/scenarios/UX-1295-bundle-export-has-an-anonymize-switch.md)
- [UX-1330](docs/backlog/scenarios/UX-1330-a-short-element-name-is-offered-its-junction-qualified-match.md) — [`whatif --element pkgs/gcc-libs.bst` is refused without offering the junction-qualified element it means](docs/backlog/scenarios/UX-1330-a-short-element-name-is-offered-its-junction-qualified-match.md)

**analysis**

- [UX-1138](docs/backlog/scenarios/UX-1138-pinned-is-the-resolved-width-not-an-argv-j1.md) — [every autotools element reads "pinned to -j1", because its install step says so](docs/backlog/scenarios/UX-1138-pinned-is-the-resolved-width-not-an-argv-j1.md)
- [UX-1139](docs/backlog/scenarios/UX-1139-the-costliest-pins-are-named-first.md) — [the capacity finding names whichever pinned elements sort first by name](docs/backlog/scenarios/UX-1139-the-costliest-pins-are-named-first.md)
- [UX-1244](docs/backlog/scenarios/UX-1244-a-capacity-bound-run-reads-scheduler-bound.md) — [a run whose resource floor is its wall reads "scheduler-bound" and is sent to the blast ranking](docs/backlog/scenarios/UX-1244-a-capacity-bound-run-reads-scheduler-bound.md)
- [UX-1245](docs/backlog/scenarios/UX-1245-oversubscription-evidence-reads-slot-occupancy-as-cpu.md) — [utilisation calls full builder slots "High CPU use", and its peak concurrency is always 1](docs/backlog/scenarios/UX-1245-oversubscription-evidence-reads-slot-occupancy-as-cpu.md)
- [UX-1247](docs/backlog/scenarios/UX-1247-the-binary-question-has-no-binary-total.md) — ["Which binaries cost this build its time?" has no per-binary total to answer with](docs/backlog/scenarios/UX-1247-the-binary-question-has-no-binary-total.md)
- [UX-1253](docs/backlog/scenarios/UX-1253-the-page-checks-its-verdicts-agree.md) — [five sections each publish a bound, and nothing checks that they agree](docs/backlog/scenarios/UX-1253-the-page-checks-its-verdicts-agree.md)
- [UX-1255](docs/backlog/scenarios/UX-1255-plane-2-measurements-reach-the-findings.md) — [39,854 Plane 2 processes produce no finding](docs/backlog/scenarios/UX-1255-plane-2-measurements-reach-the-findings.md)
- [UX-1256](docs/backlog/scenarios/UX-1256-every-finding-publishes-its-step.md) — [findings publish facts, and the steps live only in attribution hints and next steps](docs/backlog/scenarios/UX-1256-every-finding-publishes-its-step.md)
- [UX-1263](docs/backlog/scenarios/UX-1263-a-relative-run-path-drops-the-snapshot-and-compare-steps.md) — [a run passed as a relative path keeps the path and drops the snapshot and compare steps](docs/backlog/scenarios/UX-1263-a-relative-run-path-drops-the-snapshot-and-compare-steps.md)
- [UX-1265](docs/backlog/scenarios/UX-1265-the-graph-width-finding-lost-its-total-and-its-capacity-clause.md) — [the graph-width finding lost the total element count and "whatever the capacity" from its title](docs/backlog/scenarios/UX-1265-the-graph-width-finding-lost-its-total-and-its-capacity-clause.md)
- [UX-1266](docs/backlog/scenarios/UX-1266-joint-saving-and-optimization-horizon-name-the-same-set.md) — [joint-saving and optimization-horizon name the same element set on macro_micro](docs/backlog/scenarios/UX-1266-joint-saving-and-optimization-horizon-name-the-same-set.md)
- [UX-1268](docs/backlog/scenarios/UX-1268-a-capacity-bound-run-reads-capacity-matched-demand.md) — [a capacity-bound run reads "capacity matched demand", and the check does not see it](docs/backlog/scenarios/UX-1268-a-capacity-bound-run-reads-capacity-matched-demand.md)
- [UX-1272](docs/backlog/scenarios/UX-1272-the-sizing-card-memory-bound-counts-one-process-per-builder.md) — [the sizing card calls builders x one process's peak "at most", while an element runs many processes at once](docs/backlog/scenarios/UX-1272-the-sizing-card-memory-bound-counts-one-process-per-builder.md)
- [UX-1274](docs/backlog/scenarios/UX-1274-the-builder-sweep-is-drawn-and-reaches-the-graph-width.md) — ["the graph allows 8" is where the sweep stopped, and the page never shows what more builders would buy](docs/backlog/scenarios/UX-1274-the-builder-sweep-is-drawn-and-reaches-the-graph-width.md)
- [UX-1275](docs/backlog/scenarios/UX-1275-a-binary-that-waits-is-told-from-one-that-computes.md) — [the page says 2,300 elements wait rather than compute, and nothing says what they wait in](docs/backlog/scenarios/UX-1275-a-binary-that-waits-is-told-from-one-that-computes.md)
- [UX-1277](docs/backlog/scenarios/UX-1277-a-finding-says-whether-it-is-new-since-the-baseline.md) — [findings do not say whether they are new, still open or gone since the run before](docs/backlog/scenarios/UX-1277-a-finding-says-whether-it-is-new-since-the-baseline.md)
- [UX-1285](docs/backlog/scenarios/UX-1285-the-band-mixes-runs-from-different-hosts.md) — [the band a review build is judged against mixes runs from different hosts](docs/backlog/scenarios/UX-1285-the-band-mixes-runs-from-different-hosts.md)
- [UX-1321](docs/backlog/scenarios/UX-1321-blast-prices-a-junction-bump.md) — [`bga blast` on a junction, or a path inside a junctioned project, says it rebuilds nothing](docs/backlog/scenarios/UX-1321-blast-prices-a-junction-bump.md)
- [UX-1323](docs/backlog/scenarios/UX-1323-a-comparison-of-different-work-is-not-a-verdict.md) — [`compare` calls two incremental runs that rebuilt different elements IMPROVED, and the cold-then-incremental refusal names no next step](docs/backlog/scenarios/UX-1323-a-comparison-of-different-work-is-not-a-verdict.md)
- [UX-1324](docs/backlog/scenarios/UX-1324-a-builders-recommendation-needs-more-elements-than-builders.md) — [A run that rebuilt one element recommends `--builders 1` because memory binds, while saying memory fits 15.7 GB](docs/backlog/scenarios/UX-1324-a-builders-recommendation-needs-more-elements-than-builders.md)
- [UX-1325](docs/backlog/scenarios/UX-1325-cache-logs-reads-every-project-a-junction-brings-in.md) — [`bga cache-logs PROJECT` reads only the top project's logs and says nothing about the junctioned projects beside them](docs/backlog/scenarios/UX-1325-cache-logs-reads-every-project-a-junction-brings-in.md)
- [UX-1326](docs/backlog/scenarios/UX-1326-the-structural-questions-answer-before-the-first-capture.md) — [`bga blast --no-cost` refuses without a snapshot, though `bst show` holds everything it needs](docs/backlog/scenarios/UX-1326-the-structural-questions-answer-before-the-first-capture.md)
- [UX-1327](docs/backlog/scenarios/UX-1327-a-run-rolls-up-by-junction.md) — [No report section answers which junction's elements cost the most, and `junction-cost` is about variants](docs/backlog/scenarios/UX-1327-a-run-rolls-up-by-junction.md)

**capture**

- [UX-1182](docs/backlog/scenarios/UX-1182-a-synthetic-example-runs-hundreds-of-fake-binaries.md) — [a synthetic example runs hundreds of fake binaries per element, drawn from named distributions](docs/backlog/scenarios/UX-1182-a-synthetic-example-runs-hundreds-of-fake-binaries.md)
- [UX-1183](docs/backlog/scenarios/UX-1183-a-traced-element-s-binaries-reach-the-page.md) — [a traced element's binaries reach the page whole or counted](docs/backlog/scenarios/UX-1183-a-traced-element-s-binaries-reach-the-page.md)
- [UX-1205](docs/backlog/scenarios/UX-1205-a-real-capture-of-fake-sleeping-binaries-under.md) — [a real capture of fake sleeping binaries under the LD_PRELOAD hook](docs/backlog/scenarios/UX-1205-a-real-capture-of-fake-sleeping-binaries-under.md)
- [UX-1240](docs/backlog/scenarios/UX-1240-the-plane2-report-reads-a-large-log-lean.md) — [the Plane 2 report holds a large log's opened paths as strings in sets and parses every record twice over](docs/backlog/scenarios/UX-1240-the-plane2-report-reads-a-large-log-lean.md)
- [UX-1241](docs/backlog/scenarios/UX-1241-a-sandbox-writes-an-opened-path-once.md) — [every process of a sandbox writes every path it opened, so a C++ element's log repeats the same headers hundreds of times](docs/backlog/scenarios/UX-1241-a-sandbox-writes-an-opened-path-once.md)
- [UX-1242](docs/backlog/scenarios/UX-1242-the-process-records-wait-for-the-fold-packed.md) — [the Plane 2 report holds every process record as a dict until the fold, 1,232 bytes each](docs/backlog/scenarios/UX-1242-the-process-records-wait-for-the-fold-packed.md)
- [UX-1134](docs/backlog/scenarios/UX-1134-auto-oom-kills-a-memory-bound-giant-with-no-plan.md) — [`--jobserver auto` with no plan widens a memory-bound giant into the OOM killer](docs/backlog/scenarios/UX-1134-auto-oom-kills-a-memory-bound-giant-with-no-plan.md)
- [UX-1287](docs/backlog/scenarios/UX-1287-doctor-names-the-c-compiler-the-capture-needs.md) — [`bga doctor` names the C compiler the capture compiles its hook with](docs/backlog/scenarios/UX-1287-doctor-names-the-c-compiler-the-capture-needs.md)
- [UX-1301](docs/backlog/scenarios/UX-1301-four-capture-flags-appear-in-no-help-under-a-heading-that-says-they-do.md) — [four capture flags appear in no `--help`, under a heading that says they do](docs/backlog/scenarios/UX-1301-four-capture-flags-appear-in-no-help-under-a-heading-that-says-they-do.md)
- [UX-1302](docs/backlog/scenarios/UX-1302-bga-snapshot-refuses-the-per-element-jobserver-and-capture-log-flags-capture-run.md) — [`bga snapshot` refuses the per-element jobserver and capture-log flags `capture run` takes, and no doc says…
- [UX-1304](docs/backlog/scenarios/UX-1304-bga-jobserver-env-is-validated-and-recorded-and-no-sandbox-ever-reads-it.md) — [`bga-jobserver-env` is validated and recorded, and no sandbox ever reads it](docs/backlog/scenarios/UX-1304-bga-jobserver-env-is-validated-and-recorded-and-no-sandbox-ever-reads-it.md)
- [UX-1311](docs/backlog/scenarios/UX-1311-a-junctioned-elements-jobserver-annotation-never-reaches-the-shim.md) — [a junctioned element's jobserver annotation never reaches the shim](docs/backlog/scenarios/UX-1311-a-junctioned-elements-jobserver-annotation-never-reaches-the-shim.md)
- [UX-1312](docs/backlog/scenarios/UX-1312-jobserver-auth-override-reads-its-groups-from-a-file-for-capture-run-and-snapshot.md) — [`--jobserver-auth-override` takes only inline groups, and real element names are long junction-relative…
- [UX-1320](docs/backlog/scenarios/UX-1320-plane-2-keys-a-junctioned-element-by-its-full-name.md) — [Plane 2 keys a junctioned element by its full name, not the short name the shim keeps](docs/backlog/scenarios/UX-1320-plane-2-keys-a-junctioned-element-by-its-full-name.md)
- [UX-1322](docs/backlog/scenarios/UX-1322-a-build-run-through-a-wrapper-script-is-captured.md) — [`bga snapshot -- ./build.sh` ends in a Python traceback;
- [UX-1328](docs/backlog/scenarios/UX-1328-doctor-counts-what-junctions-stage.md) — [`bga doctor` warns every project whose toolchain arrives through a junction to run bga's own example scripts](docs/backlog/scenarios/UX-1328-doctor-counts-what-junctions-stage.md)
- [UX-1331](docs/backlog/scenarios/UX-1331-doctor-points-at-the-error-where-it-prints-it.md) — [`doctor` says "read the error below" above the error, and warns about suspend inside a container](docs/backlog/scenarios/UX-1331-doctor-points-at-the-error-where-it-prints-it.md)
- [UX-1315](docs/backlog/scenarios/UX-1315-a-nested-build-can-run-the-ninja-wrapper.md) — [a nested build can run the ninja wrapper](docs/backlog/scenarios/UX-1315-a-nested-build-can-run-the-ninja-wrapper.md)
- [UX-1336](docs/backlog/scenarios/UX-1336-a-patched-ninja-joins-the-jobserver.md) — [a patched ninja joins the jobserver](docs/backlog/scenarios/UX-1336-a-patched-ninja-joins-the-jobserver.md)
- [UX-1337](docs/backlog/scenarios/UX-1337-ctest-cannot-unblock-makes-pool.md) — [ctest cannot unblock make's pool](docs/backlog/scenarios/UX-1337-ctest-cannot-unblock-makes-pool.md)
- [UX-1282](docs/backlog/scenarios/UX-1282-the-memory-gate-reads-the-host-not-the-cgroup.md) — [the memory gate reads the host's memory, not the cgroup a container agent is capped at](docs/backlog/scenarios/UX-1282-the-memory-gate-reads-the-host-not-the-cgroup.md)
- [UX-1283](docs/backlog/scenarios/UX-1283-the-pool-seed-is-handed-out-before-the-memory-gate.md) — [the pool's seed tokens are handed out before the memory gate has a say](docs/backlog/scenarios/UX-1283-the-pool-seed-is-handed-out-before-the-memory-gate.md)
- [UX-1284](docs/backlog/scenarios/UX-1284-a-late-memory-peak-is-under-reserved.md) — [a link step that peaks above every compile before it is reserved at the compile's size](docs/backlog/scenarios/UX-1284-a-late-memory-peak-is-under-reserved.md)
- [UX-1310](docs/backlog/scenarios/UX-1310-the-decision-log-says-which-auth-style-each-element-was-forced-to-and-why.md) — [the decision log says which auth style each element was forced to, and by which switch](docs/backlog/scenarios/UX-1310-the-decision-log-says-which-auth-style-each-element-was-forced-to-and-why.md)
- [UX-1314](docs/backlog/scenarios/UX-1314-the-per-element-cpu-curve-samples-the-sandboxs-processes-not-host-pids-that-share-their-number.md) — [the per-element CPU curve samples the sandbox's processes, not host pids that share their…
- [UX-1339](docs/backlog/scenarios/UX-1339-the-opening-seed-can-exceed-a-cgroup-cap.md) — [the pool's opening width can exceed a cgroup cap, and nothing takes tokens back](docs/backlog/scenarios/UX-1339-the-opening-seed-can-exceed-a-cgroup-cap.md)

**viewer**

- [UX-1136](docs/backlog/scenarios/UX-1136-a-finding-card-prints-null.md) — [a finding card prints the word "null" between its parts](docs/backlog/scenarios/UX-1136-a-finding-card-prints-null.md)
- [UX-1137](docs/backlog/scenarios/UX-1137-the-describe-door-shifts-every-pair.md) — [the block's `?` door takes a grid cell and shifts every term one cell over](docs/backlog/scenarios/UX-1137-the-describe-door-shifts-every-pair.md)
- [UX-1140](docs/backlog/scenarios/UX-1140-a-quantity-in-the-decision-panel-and-provenance-prints.md) — [a quantity in the decision panel and provenance prints as a raw float or byte count](docs/backlog/scenarios/UX-1140-a-quantity-in-the-decision-panel-and-provenance-prints.md)
- [UX-1141](docs/backlog/scenarios/UX-1141-payload-keys-and-enum-values-are-shown-to-readers.md) — [payload keys and enum values are shown to readers as the label](docs/backlog/scenarios/UX-1141-payload-keys-and-enum-values-are-shown-to-readers.md)
- [UX-1142](docs/backlog/scenarios/UX-1142-task-ids-and-repository-paths-reach-reader-text-through.md) — [task ids and repository paths reach reader text through descriptions and notes](docs/backlog/scenarios/UX-1142-task-ids-and-repository-paths-reach-reader-text-through.md)
- [UX-1143](docs/backlog/scenarios/UX-1143-the-capacity-recommendation-lists-its-inputs-and-never-says.md) — [the capacity recommendation lists its inputs and never says what to set](docs/backlog/scenarios/UX-1143-the-capacity-recommendation-lists-its-inputs-and-never-says.md)
- [UX-1144](docs/backlog/scenarios/UX-1144-one-concept-carries-several-names-across-the-page.md) — [one concept carries several names across the page](docs/backlog/scenarios/UX-1144-one-concept-carries-several-names-across-the-page.md)
- [UX-1145](docs/backlog/scenarios/UX-1145-pair-lists-reader-chips-and-the-sticky-header-fail.md) — [pair lists, reader chips and the sticky header fail the compact class](docs/backlog/scenarios/UX-1145-pair-lists-reader-chips-and-the-sticky-header-fail.md)
- [UX-1146](docs/backlog/scenarios/UX-1146-the-decision-the-headline-and-next-steps-say-the.md) — [the decision, the headline and next steps say the same thing three times](docs/backlog/scenarios/UX-1146-the-decision-the-headline-and-next-steps-say-the.md)
- [UX-1147](docs/backlog/scenarios/UX-1147-headings-repeat-their-chapters-question-and-finding-titles-break.md) — [headings repeat their chapter's question and finding titles break sentence case](docs/backlog/scenarios/UX-1147-headings-repeat-their-chapters-question-and-finding-titles-break.md)
- [UX-1148](docs/backlog/scenarios/UX-1148-findings-are-not-listed-in-severity-order.md) — [findings are not listed in severity order](docs/backlog/scenarios/UX-1148-findings-are-not-listed-in-severity-order.md)
- [UX-1149](docs/backlog/scenarios/UX-1149-backticks-and-ascii-arrows-show-as-raw-characters.md) — [backticks and ASCII arrows show as raw characters](docs/backlog/scenarios/UX-1149-backticks-and-ascii-arrows-show-as-raw-characters.md)
- [UX-1150](docs/backlog/scenarios/UX-1150-booleans-and-dashes-stand-in-for-a-verdict.md) — [booleans and dashes stand in for a verdict](docs/backlog/scenarios/UX-1150-booleans-and-dashes-stand-in-for-a-verdict.md)
- [UX-1151](docs/backlog/scenarios/UX-1151-the-plane-2-sections-do-not-lead-with-their.md) — [the Plane 2 sections do not lead with their answer](docs/backlog/scenarios/UX-1151-the-plane-2-sections-do-not-lead-with-their.md)
- [UX-1152](docs/backlog/scenarios/UX-1152-folds-table-tools-and-element-card-links-repeat-what.md) — [folds, table tools and element-card links repeat what is already on screen](docs/backlog/scenarios/UX-1152-folds-table-tools-and-element-card-links-repeat-what.md)
- [UX-1153](docs/backlog/scenarios/UX-1153-six-low-impact-layout-and-glyph-defects-from-the.md) — [six low-impact layout and glyph defects from the view UI review](docs/backlog/scenarios/UX-1153-six-low-impact-layout-and-glyph-defects-from-the.md)
- [UX-1154](docs/backlog/scenarios/UX-1154-print-blanks-inner-folds-and-prints-its-controls.md) — [a print blanks inner folds and prints its controls](docs/backlog/scenarios/UX-1154-print-blanks-inner-folds-and-prints-its-controls.md)
- [UX-1155](docs/backlog/scenarios/UX-1155-accessible-names-repeat-or-omit-the-thing-they-name.md) — [accessible names repeat or omit the thing they name](docs/backlog/scenarios/UX-1155-accessible-names-repeat-or-omit-the-thing-they-name.md)
- [UX-1156](docs/backlog/scenarios/UX-1156-text-still-repeats-across-the-page.md) — [text still repeats across the page](docs/backlog/scenarios/UX-1156-text-still-repeats-across-the-page.md)
- [UX-1157](docs/backlog/scenarios/UX-1157-compact-layout-leaves-four-defects-at-390.md) — [compact layout leaves four defects at 390](docs/backlog/scenarios/UX-1157-compact-layout-leaves-four-defects-at-390.md)
- [UX-1158](docs/backlog/scenarios/UX-1158-filter-and-back-navigation-state-is-not-kept-or-told.md) — [filter and back-navigation state is not kept or told](docs/backlog/scenarios/UX-1158-filter-and-back-navigation-state-is-not-kept-or-told.md)
- [UX-1159](docs/backlog/scenarios/UX-1159-key-paths-and-schema-descriptions-reach-reader-text.md) — [key paths and schema descriptions reach reader text](docs/backlog/scenarios/UX-1159-key-paths-and-schema-descriptions-reach-reader-text.md)
- [UX-1160](docs/backlog/scenarios/UX-1160-the-pointer-travel-instrument-reads-a-content-visibility-placeholder.md) — [the pointer-travel instrument reads a content-visibility placeholder, not page geometry](docs/backlog/scenarios/UX-1160-the-pointer-travel-instrument-reads-a-content-visibility-placeholder.md)
- [UX-1161](docs/backlog/scenarios/UX-1161-print-keeps-residue-the-round-155-print-pass.md) — [print keeps residue the round-155 print pass left](docs/backlog/scenarios/UX-1161-print-keeps-residue-the-round-155-print-pass.md)
- [UX-1162](docs/backlog/scenarios/UX-1162-accessible-names-still-repeat-or-omit-what-they.md) — [accessible names still repeat or omit what they name](docs/backlog/scenarios/UX-1162-accessible-names-still-repeat-or-omit-what-they.md)
- [UX-1163](docs/backlog/scenarios/UX-1163-text-the-page-says-more-than-once-round.md) — [text the page says more than once, round 155's residue](docs/backlog/scenarios/UX-1163-text-the-page-says-more-than-once-round.md)
- [UX-1164](docs/backlog/scenarios/UX-1164-layout-residue-at-1440-and-390-after-ux.md) — [layout residue at 1440 and 390 after UX-1157](docs/backlog/scenarios/UX-1164-layout-residue-at-1440-and-390-after-ux.md)
- [UX-1165](docs/backlog/scenarios/UX-1165-filter-and-link-state-residue-after-ux-1158.md) — [filter and link state residue after UX-1158](docs/backlog/scenarios/UX-1165-filter-and-link-state-residue-after-ux-1158.md)
- [UX-1166](docs/backlog/scenarios/UX-1166-key-paths-and-dashes-still-reach-reader-text.md) — [key paths and dashes still reach reader text](docs/backlog/scenarios/UX-1166-key-paths-and-dashes-still-reach-reader-text.md)
- [UX-1168](docs/backlog/scenarios/UX-1168-the-rails-mark-goes-stale-when-no-section-enters-or-leaves.md) — [the rail's mark goes stale when no section enters or leaves](docs/backlog/scenarios/UX-1168-the-rails-mark-goes-stale-when-no-section-enters-or-leaves.md)
- [UX-1169](docs/backlog/scenarios/UX-1169-accessible-names-after-ux-1162-still-miss-the.md) — [accessible names after UX-1162 still miss the drawings' values and three labels](docs/backlog/scenarios/UX-1169-accessible-names-after-ux-1162-still-miss-the.md)
- [UX-1170](docs/backlog/scenarios/UX-1170-filter-residue-after-ux-1165-and-ux-1163.md) — [filter residue after UX-1165 and UX-1163](docs/backlog/scenarios/UX-1170-filter-residue-after-ux-1165-and-ux-1163.md)
- [UX-1171](docs/backlog/scenarios/UX-1171-layout-residue-at-390-and-forward.md) — [layout residue at 390 and Forward](docs/backlog/scenarios/UX-1171-layout-residue-at-390-and-forward.md)
- [UX-1172](docs/backlog/scenarios/UX-1172-text-residue-after-ux-1166.md) — [text residue after UX-1166](docs/backlog/scenarios/UX-1172-text-residue-after-ux-1166.md)
- [UX-1173](docs/backlog/scenarios/UX-1173-the-parallelism-structure-repeats-ids-labels-and-numbers.md) — [the #parallelism structure repeats ids, labels and numbers](docs/backlog/scenarios/UX-1173-the-parallelism-structure-repeats-ids-labels-and-numbers.md)
- [UX-1175](docs/backlog/scenarios/UX-1175-the-exported-page-ships-indentation.md) — [the exported page ships indentation](docs/backlog/scenarios/UX-1175-the-exported-page-ships-indentation.md)
- [UX-1176](docs/backlog/scenarios/UX-1176-announcements-after-ux-1169-and-ux-1170-do.md) — [announcements after UX-1169 and UX-1170 do not reach a screen reader](docs/backlog/scenarios/UX-1176-announcements-after-ux-1169-and-ux-1170-do.md)
- [UX-1177](docs/backlog/scenarios/UX-1177-jump-and-the-rail-disagree-about-what-a.md) — [Jump and the rail disagree about what a level fold and a preset are, after UX-1173](docs/backlog/scenarios/UX-1177-jump-and-the-rail-disagree-about-what-a.md)
- [UX-1178](docs/backlog/scenarios/UX-1178-layout-and-history-residue-at-390-and-after.md) — [layout and history residue at 390 and after Expand all](docs/backlog/scenarios/UX-1178-layout-and-history-residue-at-390-and-after.md)
- [UX-1179](docs/backlog/scenarios/UX-1179-print-and-find-in-page-lose-content-the.md) — [print and find-in-page lose content the page has](docs/backlog/scenarios/UX-1179-print-and-find-in-page-lose-content-the.md)
- [UX-1180](docs/backlog/scenarios/UX-1180-values-and-console-a-zero-length-ratio-an.md) — [values and console: a zero-length ratio, an epoch as hours, a tooltip-only explanation, a spaced hyphen, seven warnings](docs/backlog/scenarios/UX-1180-values-and-console-a-zero-length-ratio-an.md)
- [UX-1184](docs/backlog/scenarios/UX-1184-the-task-table-s-share-column-says-it.md) — [the task table's share column says it is a share, not a duration](docs/backlog/scenarios/UX-1184-the-task-table-s-share-column-says-it.md)
- [UX-1185](docs/backlog/scenarios/UX-1185-paging-continues-the-ranking-and-the-copy-label.md) — [paging continues the ranking, and the copy label follows the page](docs/backlog/scenarios/UX-1185-paging-continues-the-ranking-and-the-copy-label.md)
- [UX-1186](docs/backlog/scenarios/UX-1186-the-element-task-and-binary-tables-join-focus.md) — [the element, task and binary tables join Focus, Inspect and the jump box](docs/backlog/scenarios/UX-1186-the-element-task-and-binary-tables-join-focus.md)
- [UX-1187](docs/backlog/scenarios/UX-1187-every-element-view-carries-duration-and-level-and.md) — [every element view carries duration and level, and the card lists what an element blocks, bounded](docs/backlog/scenarios/UX-1187-every-element-view-carries-duration-and-level-and.md)
- [UX-1188](docs/backlog/scenarios/UX-1188-the-compare-chapter-states-how-many-elements-moved.md) — [the compare chapter states how many elements moved and offers them as a bounded, filterable table](docs/backlog/scenarios/UX-1188-the-compare-chapter-states-how-many-elements-moved.md)
- [UX-1189](docs/backlog/scenarios/UX-1189-copy-exports-the-filtered-population-not-the-page.md) — [Copy exports the filtered population, not the page](docs/backlog/scenarios/UX-1189-copy-exports-the-filtered-population-not-the-page.md)
- [UX-1190](docs/backlog/scenarios/UX-1190-table-sort-is-keyboard-reachable-shows-its-state.md) — [table sort is keyboard-reachable, shows its state, and ranks the whole population](docs/backlog/scenarios/UX-1190-table-sort-is-keyboard-reachable-shows-its-state.md)
- [UX-1191](docs/backlog/scenarios/UX-1191-a-key-column-matches-exactly-and-a-one.md) — [a key column matches exactly, and a one-op task table says its op once](docs/backlog/scenarios/UX-1191-a-key-column-matches-exactly-and-a-one.md)
- [UX-1192](docs/backlog/scenarios/UX-1192-table-strips-and-the-level-profile-say-their.md) — [table strips and the level profile say their values on hover and survive an outlier](docs/backlog/scenarios/UX-1192-table-strips-and-the-level-profile-say-their.md)
- [UX-1193](docs/backlog/scenarios/UX-1193-the-element-preset-and-the-latent-heavies-section.md) — [the element preset and the latent-heavies section use one population or two names](docs/backlog/scenarios/UX-1193-the-element-preset-and-the-latent-heavies-section.md)
- [UX-1194](docs/backlog/scenarios/UX-1194-op-and-a-duration-threshold-meet-on-the.md) — [op: and a duration threshold meet on the table that holds durations](docs/backlog/scenarios/UX-1194-op-and-a-duration-threshold-meet-on-the.md)
- [UX-1195](docs/backlog/scenarios/UX-1195-the-filter-grammar-matches-what-the-page-shows.md) — [the filter grammar matches what the page shows: a constant column, the displayed word, the column's name](docs/backlog/scenarios/UX-1195-the-filter-grammar-matches-what-the-page-shows.md)
- [UX-1196](docs/backlog/scenarios/UX-1196-a-head-and-tail-fold-prints-copies-and.md) — [a head-and-tail fold prints, copies and jumps to every row it holds, and a short table keeps its sort](docs/backlog/scenarios/UX-1196-a-head-and-tail-fold-prints-copies-and.md)
- [UX-1197](docs/backlog/scenarios/UX-1197-the-rows-shown-bound-holds-across-next-sort.md) — [the Rows-shown bound holds across Next, sort and the link, and a page step and a sort are announced and named](docs/backlog/scenarios/UX-1197-the-rows-shown-bound-holds-across-next-sort.md)
- [UX-1198](docs/backlog/scenarios/UX-1198-focus-shows-the-focused-element-s-row-in.md) — [Focus shows the focused element's row in each keyed table, and a focus link restores the bar](docs/backlog/scenarios/UX-1198-focus-shows-the-focused-element-s-row-in.md)
- [UX-1199](docs/backlog/scenarios/UX-1199-the-element-keyed-tables-declare-their-key-and.md) — [the element-keyed tables declare their key, and by_binary, binary_cost and serial_chains rank and name their quantity](docs/backlog/scenarios/UX-1199-the-element-keyed-tables-declare-their-key-and.md)
- [UX-1200](docs/backlog/scenarios/UX-1200-every-element-card-lists-what-it-blocks-as.md) — [every element card lists what it blocks, as links, with one count](docs/backlog/scenarios/UX-1200-every-element-card-lists-what-it-blocks-as.md)
- [UX-1201](docs/backlog/scenarios/UX-1201-the-compare-table-says-both-in-words-and.md) — [the compare table says 'both' in words and scales negative durations](docs/backlog/scenarios/UX-1201-the-compare-table-says-both-in-words-and.md)
- [UX-1202](docs/backlog/scenarios/UX-1202-plotted-values-reach-a-reader-as-bounded-text.md) — [plotted values reach a reader as bounded text, and an empty status is not mounted at rest](docs/backlog/scenarios/UX-1202-plotted-values-reach-a-reader-as-bounded-text.md)
- [UX-1203](docs/backlog/scenarios/UX-1203-the-rail-s-tools-and-the-pager-read.md) — [the rail's tools and the pager read as one set, and rail Next, Back and the card folds keep their order](docs/backlog/scenarios/UX-1203-the-rail-s-tools-and-the-pager-read.md)
- [UX-1204](docs/backlog/scenarios/UX-1204-the-element-view-uid-box-and-an-opened.md) — [the element-view uid box and an opened SQL paste fit at 390, and views.js and element.js drawings carry titles](docs/backlog/scenarios/UX-1204-the-element-view-uid-box-and-an-opened.md)
- [UX-1206](docs/backlog/scenarios/UX-1206-a-column-s-whole-displayed-name-reads-as.md) — [a column's whole displayed name reads as that column, and a clause not applied says the column is a share](docs/backlog/scenarios/UX-1206-a-column-s-whole-displayed-name-reads-as.md)
- [UX-1207](docs/backlog/scenarios/UX-1207-every-map-table-s-key-column-has-one.md) — [every map table's key column has one name across header, cell label and Copy](docs/backlog/scenarios/UX-1207-every-map-table-s-key-column-has-one.md)
- [UX-1208](docs/backlog/scenarios/UX-1208-at-390-a-rail-link-and-expand-all.md) — [at 390 a rail link and Expand all keep the reader's place for Back](docs/backlog/scenarios/UX-1208-at-390-a-rail-link-and-expand-all.md)
- [UX-1209](docs/backlog/scenarios/UX-1209-the-rail-s-markdown-checkbox-matches-its-13.md) — [the rail's Markdown checkbox matches its 13 px tools](docs/backlog/scenarios/UX-1209-the-rail-s-markdown-checkbox-matches-its-13.md)
- [UX-1210](docs/backlog/scenarios/UX-1210-the-critical-path-s-head-and-tail-stub.md) — [the critical path's head-and-tail stub never sorts, counts or outlives a bound, and the chain drawing shows no stale More](docs/backlog/scenarios/UX-1210-the-critical-path-s-head-and-tail-stub.md)
- [UX-1211](docs/backlog/scenarios/UX-1211-copy-follows-the-order-on-screen.md) — [Copy follows the order on screen](docs/backlog/scenarios/UX-1211-copy-follows-the-order-on-screen.md)
- [UX-1212](docs/backlog/scenarios/UX-1212-focus-heads-its-investigation-and-names-what-the.md) — [Focus heads its investigation and names what the document holds](docs/backlog/scenarios/UX-1212-focus-heads-its-investigation-and-names-what-the.md)
- [UX-1213](docs/backlog/scenarios/UX-1213-a-value-reads-the-same-in-a-card.md) — [a value reads the same in a card, a table, a badge and a sentence](docs/backlog/scenarios/UX-1213-a-value-reads-the-same-in-a-card.md)
- [UX-1214](docs/backlog/scenarios/UX-1214-a-card-s-n-more-blocks-reach-every.md) — [a card's +N more Blocks reach every element it counts](docs/backlog/scenarios/UX-1214-a-card-s-n-more-blocks-reach-every.md)
- [UX-1219](docs/backlog/scenarios/UX-1219-back-after-collapse-all-reopens-what-it-folded.md) — [Back after Collapse all reopens what it folded](docs/backlog/scenarios/UX-1219-back-after-collapse-all-reopens-what-it-folded.md)
- [UX-1220](docs/backlog/scenarios/UX-1220-the-narrow-rail-jump-box-keeps-the-place-read-for.md) — [the narrow rail jump box keeps the place read for Back, as its links do](docs/backlog/scenarios/UX-1220-the-narrow-rail-jump-box-keeps-the-place-read-for.md)
- [UX-1221](docs/backlog/scenarios/UX-1221-back-after-a-card-link-restores-the-card-offset.md) — [Back after a card link restores the card offset](docs/backlog/scenarios/UX-1221-back-after-a-card-link-restores-the-card-offset.md)
- [UX-1222](docs/backlog/scenarios/UX-1222-focus-is-one-step-back.md) — [Focus is one step Back](docs/backlog/scenarios/UX-1222-focus-is-one-step-back.md)
- [UX-1223](docs/backlog/scenarios/UX-1223-returning-to-all-rows-restores-the-chain-order-or.md) — [returning to All rows restores the chain order, or the badge says sorted](docs/backlog/scenarios/UX-1223-returning-to-all-rows-restores-the-chain-order-or.md)
- [UX-1224](docs/backlog/scenarios/UX-1224-a-printed-filtered-table-states-its-filter.md) — [a printed filtered table states its filter](docs/backlog/scenarios/UX-1224-a-printed-filtered-table-states-its-filter.md)
- [UX-1225](docs/backlog/scenarios/UX-1225-a-jump-to-a-binary-lands-on-the-filtered-by-binary.md) — [a jump to a binary lands on the filtered by_binary list](docs/backlog/scenarios/UX-1225-a-jump-to-a-binary-lands-on-the-filtered-by-binary.md)
- [UX-1226](docs/backlog/scenarios/UX-1226-a-card-label-reads-as-its-column-title.md) — [a card label reads as its column title](docs/backlog/scenarios/UX-1226-a-card-label-reads-as-its-column-title.md)
- [UX-1227](docs/backlog/scenarios/UX-1227-the-palette-s-first-arrowdown-lands-on-its-first.md) — [the palette's first ArrowDown lands on its first row](docs/backlog/scenarios/UX-1227-the-palette-s-first-arrowdown-lands-on-its-first.md)
- [UX-1228](docs/backlog/scenarios/UX-1228-a-transitive-downstream-clause-filters-the-elements.md) — [a transitive downstream: clause filters the elements an element blocks, through every level](docs/backlog/scenarios/UX-1228-a-transitive-downstream-clause-filters-the-elements.md)
- [UX-1229](docs/backlog/scenarios/UX-1229-focusing-the-elements-filter-box-after-n-more-is.md) — [focusing the Elements filter box after +N more is measured at 390 for the touch keyboard](docs/backlog/scenarios/UX-1229-focusing-the-elements-filter-box-after-n-more-is.md)
- [UX-1234](docs/backlog/scenarios/UX-1234-a-column-title-a-card-shares-reads-as-the-reader-s-word.md) — [a column title the card shares reads as the reader's word](docs/backlog/scenarios/UX-1234-a-column-title-a-card-shares-reads-as-the-reader-s-word.md)
- [UX-1236](docs/backlog/scenarios/UX-1236-a-bare-downstream-comparison-says-what-it-read.md) — [a bare `downstream > N` says what it read, and `downstream_count > N` is guarded](docs/backlog/scenarios/UX-1236-a-bare-downstream-comparison-says-what-it-read.md)
- [UX-1246](docs/backlog/scenarios/UX-1246-the-capacity-recommendation-names-a-policy-cap-as-cpu.md) — [the capacity recommendation names the host-core cap "CPU" while CPU does not bind](docs/backlog/scenarios/UX-1246-the-capacity-recommendation-names-a-policy-cap-as-cpu.md)
- [UX-1248](docs/backlog/scenarios/UX-1248-a-finding-title-leads-with-its-number-and-stays-short.md) — [finding titles run to 276 characters and bury the number they lead with](docs/backlog/scenarios/UX-1248-a-finding-title-leads-with-its-number-and-stays-short.md)
- [UX-1249](docs/backlog/scenarios/UX-1249-findings-say-each-thing-once-and-info-without-action-folds.md) — [findings name the same elements twice and ten Info findings carry no step](docs/backlog/scenarios/UX-1249-findings-say-each-thing-once-and-info-without-action-folds.md)
- [UX-1250](docs/backlog/scenarios/UX-1250-a-next-step-command-names-the-run-by-its-snapshot.md) — [next-step commands carry a 100-character absolute run path](docs/backlog/scenarios/UX-1250-a-next-step-command-names-the-run-by-its-snapshot.md)
- [UX-1251](docs/backlog/scenarios/UX-1251-the-floors-drawing-labels-collide-on-a-narrow-segment.md) — [the floors drawing's labels overprint each other when the chain segment is narrow](docs/backlog/scenarios/UX-1251-the-floors-drawing-labels-collide-on-a-narrow-segment.md)
- [UX-1252](docs/backlog/scenarios/UX-1252-all-clear-counters-are-one-sentence-and-values-keep-separators.md) — [zero counters take a row each, counts lose their separators, and an absence names the wrong series](docs/backlog/scenarios/UX-1252-all-clear-counters-are-one-sentence-and-values-keep-separators.md)
- [UX-1254](docs/backlog/scenarios/UX-1254-an-agent-sizing-card-for-the-capacity-operator.md) — [the capacity operator assembles a sizing answer from five sections](docs/backlog/scenarios/UX-1254-an-agent-sizing-card-for-the-capacity-operator.md)
- [UX-1257](docs/backlog/scenarios/UX-1257-the-compare-chapter-leads-with-the-delta.md) — ["What changed since last time?" has an empty lead, and the first screen never says the delta](docs/backlog/scenarios/UX-1257-the-compare-chapter-leads-with-the-delta.md)
- [UX-1258](docs/backlog/scenarios/UX-1258-the-capacity-bound-first-action-has-no-why-disclosure.md) — [the capacity-bound first action row has no numbered "Why #1" disclosure](docs/backlog/scenarios/UX-1258-the-capacity-bound-first-action-has-no-why-disclosure.md)
- [UX-1261](docs/backlog/scenarios/UX-1261-the-binary-cost-answer-names-a-binary-its-first-page-does-not-show.md) — [#binary_cost's answer sentence names `make` over a pair table whose first page does not show make](docs/backlog/scenarios/UX-1261-the-binary-cost-answer-names-a-binary-its-first-page-does-not-show.md)
- [UX-1267](docs/backlog/scenarios/UX-1267-ranked-element-cards-never-show-the-map-rows.md) — [ranked element cards never show the map rows ("On the path")](docs/backlog/scenarios/UX-1267-ranked-element-cards-never-show-the-map-rows.md)
- [UX-1269](docs/backlog/scenarios/UX-1269-one-quantity-under-four-names-on-the-capacity-page.md) — [one wait quantity carries four names, and two glosses contradict their source](docs/backlog/scenarios/UX-1269-one-quantity-under-four-names-on-the-capacity-page.md)
- [UX-1270](docs/backlog/scenarios/UX-1270-an-all-clear-group-keeps-a-no-that-answers.md) — [the all-clear group is labelled "None" and swallows a "no" or a 0 ms that answers the question](docs/backlog/scenarios/UX-1270-an-all-clear-group-keeps-a-no-that-answers.md)
- [UX-1271](docs/backlog/scenarios/UX-1271-a-finding-step-hands-its-command-over-as-a-command.md) — [a finding's Next line runs its command into prose, with no copy control, and the High step names enum words](docs/backlog/scenarios/UX-1271-a-finding-step-hands-its-command-over-as-a-command.md)
- [UX-1273](docs/backlog/scenarios/UX-1273-the-ready-queue-question-asks-what-it-does-not-count.md) — ["How much work was waiting to start?" excludes work waiting for a builder, so a capacity-bound run reads 1% queued](docs/backlog/scenarios/UX-1273-the-ready-queue-question-asks-what-it-does-not-count.md)
- [UX-1276](docs/backlog/scenarios/UX-1276-a-saving-is-priced-in-agent-hours-a-day.md) — [every saving is in build seconds, and the lead asks what it is worth to the team](docs/backlog/scenarios/UX-1276-a-saving-is-priced-in-agent-hours-a-day.md)
- [UX-1279](docs/backlog/scenarios/UX-1279-a-sort-button-names-what-pressing-it-does.md) — [a sort button's name says what pressing it does, not "sort: By binary"](docs/backlog/scenarios/UX-1279-a-sort-button-names-what-pressing-it-does.md)

**guards**

- [UX-1167](docs/backlog/scenarios/UX-1167-the-page-has-255-b-of-its-150.md) — [the page has 255 B of its 150,000 B budget left, and every viewer row now pays with cuts](docs/backlog/scenarios/UX-1167-the-page-has-255-b-of-its-150.md)
- [UX-1174](docs/backlog/scenarios/UX-1174-the-page-size-guard-subtracts-the-embedded-data.md) — [the page-size guard subtracts the embedded data's characters, not its bytes](docs/backlog/scenarios/UX-1174-the-page-size-guard-subtracts-the-embedded-data.md)
- [UX-1181](docs/backlog/scenarios/UX-1181-two-page-half-instruments-disagree-by-169-b.md) — [two page-half instruments disagree by 169 B, and two tests still count characters](docs/backlog/scenarios/UX-1181-two-page-half-instruments-disagree-by-169-b.md)
- [UX-1215](docs/backlog/scenarios/UX-1215-a-back-pushing-browser-guard-runs-on-a.md) — [a Back-pushing browser guard runs on a fresh history](docs/backlog/scenarios/UX-1215-a-back-pushing-browser-guard-runs-on-a.md)
- [UX-1216](docs/backlog/scenarios/UX-1216-the-store-trend-comparison-band-and-element-history.md) — [the store trend, comparison band and element history drawings are on a built test page](docs/backlog/scenarios/UX-1216-the-store-trend-comparison-band-and-element-history.md)
- [UX-1217](docs/backlog/scenarios/UX-1217-a-browser-guard-leaves-no-preference-behind-in.md) — [a browser guard leaves no preference behind in the worker's shared Chrome](docs/backlog/scenarios/UX-1217-a-browser-guard-leaves-no-preference-behind-in.md)
- [UX-1230](docs/backlog/scenarios/UX-1230-the-badge-s-all-n-matched-arm-and-the-said-back.md) — [the badge's all-N-matched arm and the said-back clause's owned-words rule have a mutation that reddens them](docs/backlog/scenarios/UX-1230-the-badge-s-all-n-matched-arm-and-the-said-back.md)
- [UX-1232](docs/backlog/scenarios/UX-1232-the-hang-guard-s-sleeper-does-not-take-49-9-s-of.md) — [the hang guard's sleeper does not take 49.9 s of wall at 2.05 s of user](docs/backlog/scenarios/UX-1232-the-hang-guard-s-sleeper-does-not-take-49-9-s-of.md)
- [UX-1233](docs/backlog/scenarios/UX-1233-the-page-budget-is-raised-to-165-000-b.md) — [the page budget is raised to 165,000 B for round 161's eleven viewer rows](docs/backlog/scenarios/UX-1233-the-page-budget-is-raised-to-165-000-b.md)
- [UX-1235](docs/backlog/scenarios/UX-1235-a-binary-jump-lands-below-the-stuck-tools-at-every-width.md) — [a binary jump lands below the stuck tools, at every width, with the rail open](docs/backlog/scenarios/UX-1235-a-binary-jump-lands-below-the-stuck-tools-at-every-width.md)
- [UX-1260](docs/backlog/scenarios/UX-1260-the-binary-jump-landing-guard-misses-1440-rail-open.md) — [the binary-jump landing is unguarded at 1440 with the rail open, and UX-1236's several-candidates branch has no page](docs/backlog/scenarios/UX-1260-the-binary-jump-landing-guard-misses-1440-rail-open.md)
- [UX-1262](docs/backlog/scenarios/UX-1262-no-page-guard-has-rendered-a-comparison-from-an-exported-page.md) — [`pages.export_uri` copies only the snapshot, so no page guard has ever rendered a comparison](docs/backlog/scenarios/UX-1262-no-page-guard-has-rendered-a-comparison-from-an-exported-page.md)
- [UX-1264](docs/backlog/scenarios/UX-1264-no-fixture-has-resource-wait-as-its-biggest-wait-category.md) — [no fixture has resource_wait as its biggest wait category, so wait-category's step is unexercised](docs/backlog/scenarios/UX-1264-no-fixture-has-resource-wait-as-its-biggest-wait-category.md)
- [UX-1313](docs/backlog/scenarios/UX-1313-the-dangling-help-scan-reads-a-scratch-file-another-guard-deletes.md) — [the dangling-help scan reads a scratch file another guard deletes mid-run](docs/backlog/scenarios/UX-1313-the-dangling-help-scan-reads-a-scratch-file-another-guard-deletes.md)
- [UX-1338](docs/backlog/scenarios/UX-1338-no-progress-leaks-into-the-next-test.md) — [two snapshot tests leak `BGA_NO_PROGRESS` into whichever test runs next](docs/backlog/scenarios/UX-1338-no-progress-leaks-into-the-next-test.md)
- [UX-1340](docs/backlog/scenarios/UX-1340-the-dev-extra-pins-a-hypothesis-the-3-9-cell-cannot-install.md) — [the dev extra pins a hypothesis the 3.9 cell cannot install, and main has been red since](docs/backlog/scenarios/UX-1340-the-dev-extra-pins-a-hypothesis-the-3-9-cell-cannot-install.md)

**docs**

- [UX-1231](docs/backlog/scenarios/UX-1231-the-styleguide-states-two-rules-a-filtering-link.md) — [the styleguide states two rules: a filtering link moves focus to its filter, an entry naming no View is at the opening View](docs/backlog/scenarios/UX-1231-the-styleguide-states-two-rules-a-filtering-link.md)
- [UX-902](docs/backlog/scenarios/UX-0902-the-showcase-case-file-and-its-two-capture-rule.md) — [a showcase case is two captures, and there is nowhere to put one](docs/backlog/scenarios/UX-0902-the-showcase-case-file-and-its-two-capture-rule.md)
- [UX-1294](docs/backlog/scenarios/UX-1294-changelog-links-resolve-from-the-repo-root.md) — [the CHANGELOG's task links resolve from the repository root](docs/backlog/scenarios/UX-1294-changelog-links-resolve-from-the-repo-root.md)
- [UX-1288](docs/backlog/scenarios/UX-1288-a-pilot-kit-runs-bga-in-a-teams-ci-in-report-only-mode.md) — [a pilot kit runs bga in a team's CI, report-only, from one script](docs/backlog/scenarios/UX-1288-a-pilot-kit-runs-bga-in-a-teams-ci-in-report-only-mode.md)
- [UX-1292](docs/backlog/scenarios/UX-1292-stale-and-retired-doc-pages-are-corrected.md) — [the stale claims the docs audit found are corrected, and the retired stub is removed](docs/backlog/scenarios/UX-1292-stale-and-retired-doc-pages-are-corrected.md)
- [UX-1289](docs/backlog/scenarios/UX-1289-docs-front-door-is-a-router-not-a-round-log.md) — [`docs/README.md` is a one-screen router by job, and the round log moves under `audits/`](docs/backlog/scenarios/UX-1289-docs-front-door-is-a-router-not-a-round-log.md)
- [UX-1293](docs/backlog/scenarios/UX-1293-design-directions-holds-directions-not-round-history.md) — [`design/directions.md` holds the directions in order, and its round history moves to `audits/`](docs/backlog/scenarios/UX-1293-design-directions-holds-directions-not-round-history.md)
- [UX-1299](docs/backlog/scenarios/UX-1299-three-pointers-name-where-the-audit-history-used-to-be.md) — [three pointers name a place in the audit and design history that is no longer there](docs/backlog/scenarios/UX-1299-three-pointers-name-where-the-audit-history-used-to-be.md)
- [UX-1296](docs/backlog/scenarios/UX-1296-the-pilot-guide-states-a-band-threshold-and-an-exit-6-the-kit-does-not-have.md) — [`pilot.md` states a band threshold and an exit-6 behaviour the kit does not have](docs/backlog/scenarios/UX-1296-the-pilot-guide-states-a-band-threshold-and-an-exit-6-the-kit-does-not-have.md)
- [UX-1297](docs/backlog/scenarios/UX-1297-the-pilot-workflow-keeps-no-pull-request-verdict.md) — [the pilot's workflow keeps no pull request's verdict, and its overhead control is in no file](docs/backlog/scenarios/UX-1297-the-pilot-workflow-keeps-no-pull-request-verdict.md)
- [UX-1290](docs/backlog/scenarios/UX-1290-cli-md-is-split-into-commands-contracts-and-viewer.md) — [`cli.md` is split into a command reference, a contracts page and a viewer page, and user switches are separated from internal variables](docs/backlog/scenarios/UX-1290-cli-md-is-split-into-commands-contracts-and-viewer.md)
- [UX-1291](docs/backlog/scenarios/UX-1291-a-sharing-a-capture-guide.md) — [one guide says how to keep, share, anonymise and reload a capture](docs/backlog/scenarios/UX-1291-a-sharing-a-capture-guide.md)
- [UX-1300](docs/backlog/scenarios/UX-1300-the-jobserver-guide-names-every-per-element-switch.md) — [the jobserver guide names every way to keep one element out of `auto` or force its style](docs/backlog/scenarios/UX-1300-the-jobserver-guide-names-every-per-element-switch.md)
- [UX-1303](docs/backlog/scenarios/UX-1303-bga-config-s-hand-edited-keys-have-no-section-saying-what-each-one-does.md) — [`.bga/config`'s hand-edited keys have no section saying what each one does](docs/backlog/scenarios/UX-1303-bga-config-s-hand-edited-keys-have-no-section-saying-what-each-one-does.md)
- [UX-1308](docs/backlog/scenarios/UX-1308-the-graph-owner-has-no-end-to-end-guide.md) — [the graph owner has no end-to-end guide](docs/backlog/scenarios/UX-1308-the-graph-owner-has-no-end-to-end-guide.md)
- [UX-1307](docs/backlog/scenarios/UX-1307-about-twenty-user-facing-flags-are-named-by-no-doc-at-all.md) — [about twenty user-facing flags are named by no doc at all](docs/backlog/scenarios/UX-1307-about-twenty-user-facing-flags-are-named-by-no-doc-at-all.md)
- [UX-1305](docs/backlog/scenarios/UX-1305-a-capture-that-recorded-zero-processes-has-no-troubleshooting-guide.md) — [a capture that recorded zero processes has no troubleshooting guide](docs/backlog/scenarios/UX-1305-a-capture-that-recorded-zero-processes-has-no-troubleshooting-guide.md)
- [UX-1306](docs/backlog/scenarios/UX-1306-no-guide-says-the-run-store-grows-or-how-to-prune-it.md) — [no guide says the run store grows, or how to prune it](docs/backlog/scenarios/UX-1306-no-guide-says-the-run-store-grows-or-how-to-prune-it.md)
- [UX-1329](docs/backlog/scenarios/UX-1329-the-first-commands-are-the-first-thing-help-shows.md) — [The README's real-project install line installs the user's project, and `bga --help` buries doctor, snapshot and view](docs/backlog/scenarios/UX-1329-the-first-commands-are-the-first-thing-help-shows.md)
- [UX-1332](docs/backlog/scenarios/UX-1332-json-contracts-and-the-schema-name-the-old-command-for-variant-cost.md) — [`json-contracts.md` and the `junction-cost/v1` schema still name `bga junction-cost` as the emitter](docs/backlog/scenarios/UX-1332-json-contracts-and-the-schema-name-the-old-command-for-variant-cost.md)
- [UX-1334](docs/backlog/scenarios/UX-1334-four-junction-round-changes-no-guide-names.md) — [wrapper-script capture, `cache-logs` across junctions, doctor's junction check and help's start block are in no guide](docs/backlog/scenarios/UX-1334-four-junction-round-changes-no-guide-names.md)
- [UX-1341](docs/backlog/scenarios/UX-1341-the-release-guide-spells-release-notes-with-positional-markers.md) — [the release guide spells `bga release-notes` with positional markers the CLI refuses](docs/backlog/scenarios/UX-1341-the-release-guide-spells-release-notes-with-positional-markers.md)

<!-- /generated -->

## 0.5.0 — the tool prices its own cost and the jobserver (2026-09-29)

Named for what the tree now says about itself. The snapshot records what
`bga` itself cost after the build (`tail/v1`, `UX-1078`); `bga compare`
and `bga view` read each side's published analysis instead of analysing
both runs again, and `--reanalyse` forces the old path (`UX-1073`).
Round 152's jobserver work is what a user meets first: `bga analyze`
now recommends a builder count and a pool size from a capture, with the
next token going to the critical path (`UX-1005`), and qualifies its
`--jobserver auto` advice by the capture's memory, because widening a
memory-bound giant on the default kills it in the OOM killer
(`UX-1134`). `bga junction-cost` prices N separate CI builds against one
junctioned invocation (`UX-904`), and `bga bundle --load` takes a
directory tree of bundles, all or none, so a store can be rebuilt from
what CI kept (`UX-900`).

**Contract delta:** two new contracts, `tail/v1` - what bga itself
costs after the build, written beside each snapshot (`UX-1078`) - and
`junction-cost/v1` - N variant builds priced against one junctioned
invocation, printed by the new `bga junction-cost` (`UX-904`) - which
makes this cut `extending`.

**Upgrade note:** none. `tail/v1` and `junction-cost/v1` are new files
beside the old ones; `--reanalyse` and `bundle --load DIR` are new
spellings, nothing was removed or renamed.

**Carried findings.** Review 28 (closed-row marker 982) filed two
bookkeeping lines and no task file, so it leaves no open row. Walk
seed 4 ([`walk-seed-4.md`](docs/audits/walk-seed-4.md), on `74aa14f2`)
filed `UX-1135`, closed before this cut, and six bookkeeping lines.
`UX-1134`'s memory gate ships with its Graviton reading still open.

```text state
digest: 6157b7b8d5e4
contracts: analyze/v2 analyze/v3 analyze/v4 analyze/v5 analyze/v6 blast/v1 blast/v2 bundle-manifest/v1 capacity-model/v1 capture-layout/v1 compare/v1 compare/v2 correlate/v1 correlate/v2 host-samples/v1 host/v1 host/v2 junction-cost/v1 plane2/v1 plane2/v2 plane2/v3 sources/v1 store-aggregate/v1 store/v1 sweep/v1 tail/v1 whatif/v1
commands: analyze baseline blast bundle cache-logs cache-trend capture checkout-cost chrome-to-trace compare correlate cross-check diagnostics doctor extract floors gen-synthetic graph graph-from-show junction-cost log-to-chrome native-to-chrome rebuild-set release-notes replay run-context snapshot sweep timeline utilisation view whatif wrap
```

### What landed

<!-- generated: UX-252 813→1083 -->
270 scenarios closed (closed-row markers 813 → 1083).

**contracts**

- [UX-838](docs/backlog/scenarios/UX-0838-fan-in-direct-ships-with-no-prose-and-no-guard-can-see-it.md) — [`fan_in[].direct` ships with no prose, and no guard can see it](docs/backlog/scenarios/UX-0838-fan-in-direct-ships-with-no-prose-and-no-guard-can-see-it.md)
- [UX-851](docs/backlog/scenarios/UX-0851-the-jobserver-is-a-capture-option-and-a-snapshot-fact.md) — [the jobserver is a capture option and a snapshot fact](docs/backlog/scenarios/UX-0851-the-jobserver-is-a-capture-option-and-a-snapshot-fact.md)
- [UX-898](docs/backlog/scenarios/UX-0898-a-comparison-class-is-the-host-and-the-build-type.md) — [a comparison class is the host class and the build type together](docs/backlog/scenarios/UX-0898-a-comparison-class-is-the-host-and-the-build-type.md)
- [UX-903](docs/backlog/scenarios/UX-0903-a-variant-is-a-second-axis-under-the-build-type.md) — [a variant is a second axis under the build type, and nothing records it](docs/backlog/scenarios/UX-0903-a-variant-is-a-second-axis-under-the-build-type.md)
- [UX-1031](docs/backlog/scenarios/UX-1031-every-growing-sequence-is-declared-in-the-schema.md) — [every list and data-keyed map in the payload is declared, with whether it grows](docs/backlog/scenarios/UX-1031-every-growing-sequence-is-declared-in-the-schema.md)
- [UX-1101](docs/backlog/scenarios/UX-1101-the-verification-log-is-re-grounded-at-a-shared-merge.md) — [the verification log is re-grounded at a shared merge](docs/backlog/scenarios/UX-1101-the-verification-log-is-re-grounded-at-a-shared-merge.md)
- [UX-1060](docs/backlog/scenarios/UX-1060-every-exported-value-path-declares-what-it-discloses.md) — [every exported value path declares what it discloses](docs/backlog/scenarios/UX-1060-every-exported-value-path-declares-what-it-discloses.md)
- [UX-1070](docs/backlog/scenarios/UX-1070-the-disclosure-policy-names-what-the-producer-writes.md) — [the disclosure policy names what the producer writes](docs/backlog/scenarios/UX-1070-the-disclosure-policy-names-what-the-producer-writes.md)
- [UX-1103](docs/backlog/scenarios/UX-1103-the-verification-log-and-the-loop-ceiling-re-ground-at-the-298-300-merge.md) — [the verification log and the loop ceiling re-ground at the #298/#300 merge](docs/backlog/scenarios/UX-1103-the-verification-log-and-the-loop-ceiling-re-ground-at-the-298-300-merge.md)
- [UX-1123](docs/backlog/scenarios/UX-1123-the-verification-log-re-grounds-at-round-151.md) — [the verification log re-grounds at round 151's merge](docs/backlog/scenarios/UX-1123-the-verification-log-re-grounds-at-round-151.md)
- [UX-1131](docs/backlog/scenarios/UX-1131-the-schema-count-says-ten-and-bga-schema-prints-nine.md) — [`docs/README.md` counts ten printable contracts and `bga --schema` prints nine](docs/backlog/scenarios/UX-1131-the-schema-count-says-ten-and-bga-schema-prints-nine.md)
- [UX-1133](docs/backlog/scenarios/UX-1133-the-verification-log-re-grounds-at-round-152.md) — [round 152's architecture.md edits get their verification-log entry](docs/backlog/scenarios/UX-1133-the-verification-log-re-grounds-at-round-152.md)

**cli**

- [UX-1036](docs/backlog/scenarios/UX-1036-the-export-message-prints-a-double-period.md) — [`bga view --export` prints a double period before its timeline hint](docs/backlog/scenarios/UX-1036-the-export-message-prints-a-double-period.md)
- [UX-1038](docs/backlog/scenarios/UX-1038-cli-output-prints-parenthesised-plurals.md) — [CLI output prints `(s)` plurals where the count is known](docs/backlog/scenarios/UX-1038-cli-output-prints-parenthesised-plurals.md)
- [UX-1077](docs/backlog/scenarios/UX-1077-the-tail-and-the-view-say-what-they-are-doing.md) — [the snapshot tail and bga view run minutes of work with no progress and no timing](docs/backlog/scenarios/UX-1077-the-tail-and-the-view-say-what-they-are-doing.md)
- [UX-1064](docs/backlog/scenarios/UX-1064-a-pseudonym-in-any-text-resolves-back-to-the-real-name.md) — [a pseudonym in any text resolves back to the real name](docs/backlog/scenarios/UX-1064-a-pseudonym-in-any-text-resolves-back-to-the-real-name.md)

**analysis**

- [UX-827](docs/backlog/scenarios/UX-0827-the-distribution-twin-draws-five-of-sixteen-published-marks-and-no-mean.md) — [the distribution twin draws five of sixteen published marks, and no mean](docs/backlog/scenarios/UX-0827-the-distribution-twin-draws-five-of-sixteen-published-marks-and-no-mean.md)
- [UX-826](docs/backlog/scenarios/UX-0826-five-bare-task-ids-and-a-pipe-delimited-task-key-reach-the-reader.md) — [five bare task ids and a pipe-delimited task key reach the reader](docs/backlog/scenarios/UX-0826-five-bare-task-ids-and-a-pipe-delimited-task-key-reach-the-reader.md)
- [UX-823](docs/backlog/scenarios/UX-0823-the-intervals-from-column-renders-a-monotonic-epoch-as-a-duration.md) — [the intervals' From column renders a monotonic epoch as a duration](docs/backlog/scenarios/UX-0823-the-intervals-from-column-renders-a-monotonic-epoch-as-a-duration.md)
- [UX-817](docs/backlog/scenarios/UX-0817-the-join-calls-a-zero-rebuilt-run-an-attribution-failure.md) — [the join calls a zero-rebuilt run an attribution failure](docs/backlog/scenarios/UX-0817-the-join-calls-a-zero-rebuilt-run-an-attribution-failure.md)
- [UX-833](docs/backlog/scenarios/UX-0833-a-declared-source-kind-map-for-custom-source-plugins.md) — [a declared source-kind map for custom source plugins](docs/backlog/scenarios/UX-0833-a-declared-source-kind-map-for-custom-source-plugins.md)
- [UX-830](docs/backlog/scenarios/UX-0830-the-serial-chains-ranked-not-the-longest-one.md) — [the serial chains, ranked, not the longest one](docs/backlog/scenarios/UX-0830-the-serial-chains-ranked-not-the-longest-one.md)
- [UX-847](docs/backlog/scenarios/UX-0847-the-token-ledger-lands-in-plane-2-and-the-page.md) — [the token ledger lands in Plane 2 and the page](docs/backlog/scenarios/UX-0847-the-token-ledger-lands-in-plane-2-and-the-page.md)
- [UX-861](docs/backlog/scenarios/UX-0861-a-builder-count-above-the-hosts-cores-is-never-recommended-verbatim.md) — [a builder count above the host's cores is never recommended verbatim](docs/backlog/scenarios/UX-0861-a-builder-count-above-the-hosts-cores-is-never-recommended-verbatim.md)
- [UX-860](docs/backlog/scenarios/UX-0860-swap-is-a-finding-not-a-word-in-a-cpu-sentence.md) — [swap is a finding, not a word in a CPU sentence](docs/backlog/scenarios/UX-0860-swap-is-a-finding-not-a-word-in-a-cpu-sentence.md)
- [UX-891](docs/backlog/scenarios/UX-0891-the-certified-floors-never-divide-by-the-machines-cores.md) — [the certified floors never divide by the machine's cores](docs/backlog/scenarios/UX-0891-the-certified-floors-never-divide-by-the-machines-cores.md)
- [UX-899](docs/backlog/scenarios/UX-0899-the-seconds-slower-gate-needs-a-band-not-a-pair.md) — ["this PR made the build N seconds slower" needs a band, not a pair](docs/backlog/scenarios/UX-0899-the-seconds-slower-gate-needs-a-band-not-a-pair.md)
- [UX-1073](docs/backlog/scenarios/UX-1073-compare-reads-the-published-analyses.md) — [compare reads each side's published analysis instead of analyzing both runs again](docs/backlog/scenarios/UX-1073-compare-reads-the-published-analyses.md)
- [UX-1074](docs/backlog/scenarios/UX-1074-reachability-is-one-bitset-closure-per-graph.md) — [graph reachability is materialised as sets, five times per analysis](docs/backlog/scenarios/UX-1074-reachability-is-one-bitset-closure-per-graph.md)
- [UX-1106](docs/backlog/scenarios/UX-1106-blast-radius-sums-durations-off-the-bitset.md) — [blast radius decodes every element's downstream set to sum durations over it](docs/backlog/scenarios/UX-1106-blast-radius-sums-durations-off-the-bitset.md)
- [UX-1012](docs/backlog/scenarios/UX-1012-the-report-says-which-elements-drew-from-the-jobserver.md) — [the report says which elements drew from the jobserver, not only which were offered it](docs/backlog/scenarios/UX-1012-the-report-says-which-elements-drew-from-the-jobserver.md)
- [UX-1008](docs/backlog/scenarios/UX-1008-a-consumer-with-no-width-promise-is-named.md) — [a consumer with no width promise is named, not silently oversubscribing](docs/backlog/scenarios/UX-1008-a-consumer-with-no-width-promise-is-named.md)
- [UX-904](docs/backlog/scenarios/UX-0904-separate-invocations-or-one-junctioned-build.md) — [nothing prices N separate CI builds against one junctioned invocation](docs/backlog/scenarios/UX-0904-separate-invocations-or-one-junctioned-build.md)
- [UX-1005](docs/backlog/scenarios/UX-1005-bga-recommends-builders-and-pool-size-from-a-capture.md) — [bga recommends a builder count and a pool size from a capture, and the critical path gets the next token](docs/backlog/scenarios/UX-1005-bga-recommends-builders-and-pool-size-from-a-capture.md)
- [UX-1135](docs/backlog/scenarios/UX-1135-the-joint-saving-compares-against-each-elements-own-saving.md) — [the joint saving compares against each element's own saving, not the horizon's steps](docs/backlog/scenarios/UX-1135-the-joint-saving-compares-against-each-elements-own-saving.md)

**capture**

- [UX-841](docs/backlog/scenarios/UX-0841-the-tracers-fifo-lifecycle-is-guarded-and-the-auth-style-follows-make.md) — [the tracer's FIFO lifecycle is guarded, and the auth style follows `make`](docs/backlog/scenarios/UX-0841-the-tracers-fifo-lifecycle-is-guarded-and-the-auth-style-follows-make.md)
- [UX-845](docs/backlog/scenarios/UX-0845-the-pool-follows-the-machine-not-the-load-average.md) — [the pool follows the machine, not the load average](docs/backlog/scenarios/UX-0845-the-pool-follows-the-machine-not-the-load-average.md)
- [UX-842](docs/backlog/scenarios/UX-0842-a-pinned-element-never-joins-the-jobserver.md) — [a pinned element never joins the jobserver](docs/backlog/scenarios/UX-0842-a-pinned-element-never-joins-the-jobserver.md)
- [UX-843](docs/backlog/scenarios/UX-0843-the-per-kind-environment-table-and-the-ninja-that-cannot-join.md) — [the per-kind environment table, and the ninja that cannot join](docs/backlog/scenarios/UX-0843-the-per-kind-environment-table-and-the-ninja-that-cannot-join.md)
- [UX-848](docs/backlog/scenarios/UX-0848-a-compile-bound-example-is-the-jobservers-evaluation.md) — [a compile-bound example is the jobserver's evaluation](docs/backlog/scenarios/UX-0848-a-compile-bound-example-is-the-jobservers-evaluation.md)
- [UX-846](docs/backlog/scenarios/UX-0846-a-tool-that-will-not-read-the-pipe-holds-tokens-instead.md) — [a tool that will not read the pipe holds tokens instead](docs/backlog/scenarios/UX-0846-a-tool-that-will-not-read-the-pipe-holds-tokens-instead.md)
- [UX-852](docs/backlog/scenarios/UX-0852-outstanding-tokens-are-audited-against-live-processes.md) — [outstanding tokens are audited against live processes](docs/backlog/scenarios/UX-0852-outstanding-tokens-are-audited-against-live-processes.md)
- [UX-849](docs/backlog/scenarios/UX-0849-per-element-proxies-grant-tokens-by-slack.md) — [per-element proxies grant tokens by slack](docs/backlog/scenarios/UX-0849-per-element-proxies-grant-tokens-by-slack.md)
- [UX-850](docs/backlog/scenarios/UX-0850-memory-is-a-second-resource-the-pool-reads.md) — [memory is a second resource the pool reads](docs/backlog/scenarios/UX-0850-memory-is-a-second-resource-the-pool-reads.md)
- [UX-853](docs/backlog/scenarios/UX-0853-the-memory-gate-sums-the-elements-that-run-together.md) — [the memory gate sums the elements that run together](docs/backlog/scenarios/UX-0853-the-memory-gate-sums-the-elements-that-run-together.md)
- [UX-856](docs/backlog/scenarios/UX-0856-the-jobserver-is-a-snapshot-switch.md) — [the jobserver is a snapshot switch](docs/backlog/scenarios/UX-0856-the-jobserver-is-a-snapshot-switch.md)
- [UX-854](docs/backlog/scenarios/UX-0854-a-proxy-token-held-by-a-killed-job-is-audited-too.md) — [a proxy token held by a killed job is audited too](docs/backlog/scenarios/UX-0854-a-proxy-token-held-by-a-killed-job-is-audited-too.md)
- [UX-857](docs/backlog/scenarios/UX-0857-one-long-element-under-a-cap-is-the-servers-shape.md) — [one long element under a cap is the server's shape](docs/backlog/scenarios/UX-0857-one-long-element-under-a-cap-is-the-servers-shape.md)
- [UX-859](docs/backlog/scenarios/UX-0859-a-recipe-that-spends-jobs-joins-the-jobserver-whatever-its-kind.md) — [a recipe that spends `JOBS` joins the jobserver, whatever its kind](docs/backlog/scenarios/UX-0859-a-recipe-that-spends-jobs-joins-the-jobserver-whatever-its-kind.md)
- [UX-865](docs/backlog/scenarios/UX-0865-a-relative-open-is-recorded-against-its-cwd.md) — [a relative open is recorded against its cwd](docs/backlog/scenarios/UX-0865-a-relative-open-is-recorded-against-its-cwd.md)
- [UX-858](docs/backlog/scenarios/UX-0858-the-pool-grows-toward-the-machine-not-its-opening-seed.md) — [the pool grows toward the machine, not its opening seed](docs/backlog/scenarios/UX-0858-the-pool-grows-toward-the-machine-not-its-opening-seed.md)
- [UX-870](docs/backlog/scenarios/UX-0870-the-kinds-read-carries-the-users-own-bst-options-and-says-why-it-failed.md) — [the kinds read carries the user's own bst options and says why it failed](docs/backlog/scenarios/UX-0870-the-kinds-read-carries-the-users-own-bst-options-and-says-why-it-failed.md)
- [UX-871](docs/backlog/scenarios/UX-0871-a-junctioned-element-finds-its-kind.md) — [a junctioned element finds its kind](docs/backlog/scenarios/UX-0871-a-junctioned-element-finds-its-kind.md)
- [UX-869](docs/backlog/scenarios/UX-0869-the-jobserver-fifo-mounts-under-the-bind-destination.md) — [the jobserver FIFO mounts under the bind destination](docs/backlog/scenarios/UX-0869-the-jobserver-fifo-mounts-under-the-bind-destination.md)
- [UX-873](docs/backlog/scenarios/UX-0873-the-target-read-knows-the-subcommands-own-option-arity.md) — [the target read knows the subcommand's own option arity](docs/backlog/scenarios/UX-0873-the-target-read-knows-the-subcommands-own-option-arity.md)
- [UX-872](docs/backlog/scenarios/UX-0872-a-junctioned-example-builds-under-the-mode-in-ci.md) — [a junctioned example builds under the mode in CI](docs/backlog/scenarios/UX-0872-a-junctioned-example-builds-under-the-mode-in-ci.md)
- [UX-875](docs/backlog/scenarios/UX-0875-bga-snapshot-forwards-the-auth-style.md) — [bga snapshot forwards the jobserver auth style](docs/backlog/scenarios/UX-0875-bga-snapshot-forwards-the-auth-style.md)
- [UX-874](docs/backlog/scenarios/UX-0874-the-auth-style-follows-the-make-that-consumes-it.md) — [the jobserver auth style follows the make that consumes it](docs/backlog/scenarios/UX-0874-the-auth-style-follows-the-make-that-consumes-it.md)
- [UX-876](docs/backlog/scenarios/UX-0876-auto-picks-fd-the-style-every-make-accepts.md) — [jobserver auto picks fd, the style every make accepts](docs/backlog/scenarios/UX-0876-auto-picks-fd-the-style-every-make-accepts.md)
- [UX-877](docs/backlog/scenarios/UX-0877-the-downgrade-covers-every-kind-that-injects-makeflags.md) — [the sandbox-make downgrade covers every kind that injects MAKEFLAGS](docs/backlog/scenarios/UX-0877-the-downgrade-covers-every-kind-that-injects-makeflags.md)
- [UX-878](docs/backlog/scenarios/UX-0878-the-lto-link-survives-the-jobserver.md) — the injected jobserver never reaches gcc's lto-wrapper as an fd it can't use
- [UX-879](docs/backlog/scenarios/UX-0879-a-per-element-switch-forces-the-jobserver-auth-style.md) — a per-element switch forces the jobserver auth style, overriding auto
- [UX-880](docs/backlog/scenarios/UX-0880-a-compiler-lto-shim-fills-the-box-without-the-ice.md) — [a compiler-LTO shim fills the box without the gcc-13 ICE](docs/backlog/scenarios/UX-0880-a-compiler-lto-shim-fills-the-box-without-the-ice.md)
- [UX-883](docs/backlog/scenarios/UX-0883-a-preflight-warns-when-lto-meets-a-sub-4-4-make.md) — [a preflight warns when an LTO element meets a sub-4.4 make](docs/backlog/scenarios/UX-0883-a-preflight-warns-when-lto-meets-a-sub-4-4-make.md)
- [UX-881](docs/backlog/scenarios/UX-0881-an-operator-ships-their-own-wrapper-directory.md) — [an operator ships their own wrapper directory for a custom-prefix toolchain](docs/backlog/scenarios/UX-0881-an-operator-ships-their-own-wrapper-directory.md)
- [UX-882](docs/backlog/scenarios/UX-0882-a-public-annotation-sets-the-jobserver-auth-style.md) — [a `public:` annotation sets the jobserver auth style, version-controlled](docs/backlog/scenarios/UX-0882-a-public-annotation-sets-the-jobserver-auth-style.md)
- [UX-888](docs/backlog/scenarios/UX-0888-the-ninja-wrapper-owns-ninjas-j-flag.md) — [the ninja wrapper owns ninja's -j, stripping the recipe's own](docs/backlog/scenarios/UX-0888-the-ninja-wrapper-owns-ninjas-j-flag.md)
- [UX-896](docs/backlog/scenarios/UX-0896-the-caches-capacity-is-invisible-until-it-rebuilds.md) — [the cache's capacity is invisible until it rebuilds](docs/backlog/scenarios/UX-0896-the-caches-capacity-is-invisible-until-it-rebuilds.md)
- [UX-897](docs/backlog/scenarios/UX-0897-transfer-is-seconds-and-never-bytes.md) — [transfer is measured in seconds and never in bytes](docs/backlog/scenarios/UX-0897-transfer-is-seconds-and-never-bytes.md)
- [UX-892](docs/backlog/scenarios/UX-0892-the-per-element-token-record-drops-the-timestamp-it-was-given.md) — [the per-element token record drops the timestamp it was given](docs/backlog/scenarios/UX-0892-the-per-element-token-record-drops-the-timestamp-it-was-given.md)
- [UX-893](docs/backlog/scenarios/UX-0893-cores-busy-is-an-average-over-the-span-not-a-curve.md) — [cores busy is an average over the span, not a curve](docs/backlog/scenarios/UX-0893-cores-busy-is-an-average-over-the-span-not-a-curve.md)
- [UX-894](docs/backlog/scenarios/UX-0894-the-requested-j-is-an-argv-regex-over-three-binaries.md) — [the requested -j is an argv regex over three binaries, not the element's resolved width](docs/backlog/scenarios/UX-0894-the-requested-j-is-an-argv-regex-over-three-binaries.md)
- [UX-907](docs/backlog/scenarios/UX-0907-an-artifacts-weight-has-no-cheap-source.md) — [an artifact's weight has no cheap source](docs/backlog/scenarios/UX-0907-an-artifacts-weight-has-no-cheap-source.md)
- [UX-906](docs/backlog/scenarios/UX-0906-the-jobservers-corner-cases-are-a-register-not-a-memory.md) — [the jobserver's corner cases live in twelve task files and no register](docs/backlog/scenarios/UX-0906-the-jobservers-corner-cases-are-a-register-not-a-memory.md)
- [UX-901](docs/backlog/scenarios/UX-0901-the-jobserver-is-a-subtool-behind-a-boundary.md) — [the jobserver is a subtool behind a boundary](docs/backlog/scenarios/UX-0901-the-jobserver-is-a-subtool-behind-a-boundary.md)
- [UX-1001](docs/backlog/scenarios/UX-1001-ninja-1-13s-client-is-read-by-its-version-not-its-help.md) — [ninja 1.13's jobserver client is read by its version, not its help text](docs/backlog/scenarios/UX-1001-ninja-1-13s-client-is-read-by-its-version-not-its-help.md)
- [UX-1002](docs/backlog/scenarios/UX-1002-a-capture-names-its-physical-cores.md) — [a capture names its physical cores, not only its logical CPUs](docs/backlog/scenarios/UX-1002-a-capture-names-its-physical-cores.md)
- [UX-1003](docs/backlog/scenarios/UX-1003-a-shared-build-root-hides-the-kind-so-make-elements-never-join.md) — [a shared build root hides the element's kind, so fdsdk's make elements never join](docs/backlog/scenarios/UX-1003-a-shared-build-root-hides-the-kind-so-make-elements-never-join.md)
- [UX-1004](docs/backlog/scenarios/UX-1004-the-runner-s-effective-core-count-is-calibrated.md) — [the runner's effective core count is calibrated, not read from nproc](docs/backlog/scenarios/UX-1004-the-runner-s-effective-core-count-is-calibrated.md)
- [UX-1006](docs/backlog/scenarios/UX-1006-a-wrapped-ninja-hands-gcc-a-fifo-not-a-blocking-fd-pair.md) — [a wrapped ninja hands gcc a fifo path, not a blocking fd pair](docs/backlog/scenarios/UX-1006-a-wrapped-ninja-hands-gcc-a-fifo-not-a-blocking-fd-pair.md)
- [UX-884](docs/backlog/scenarios/UX-0884-the-lto-scrub-covers-make-and-autotools-kinds.md) — [the LTO scrub covers make/autotools kinds, not only cmake/meson/cargo](docs/backlog/scenarios/UX-0884-the-lto-scrub-covers-make-and-autotools-kinds.md)
- [UX-1009](docs/backlog/scenarios/UX-1009-the-examples-cannot-stage-their-toolchain-on-aarch64.md) — [the examples cannot stage their toolchain on aarch64](docs/backlog/scenarios/UX-1009-the-examples-cannot-stage-their-toolchain-on-aarch64.md)
- [UX-895](docs/backlog/scenarios/UX-0895-the-captures-own-overhead-is-unmeasured.md) — [the capture's own overhead is unmeasured, so Plane 2 on every build is a guess](docs/backlog/scenarios/UX-0895-the-captures-own-overhead-is-unmeasured.md)
- [UX-905](docs/backlog/scenarios/UX-0905-the-jobserver-has-no-compile-bound-project-at-scale.md) — [the jobserver has no compile-bound project at the scale it is meant for](docs/backlog/scenarios/UX-0905-the-jobserver-has-no-compile-bound-project-at-scale.md)
- [UX-1011](docs/backlog/scenarios/UX-1011-jobserver-auto-pays-three-bst-show-calls-before-the-build.md) — [`--jobserver auto` pays three `bst show` calls before the build](docs/backlog/scenarios/UX-1011-jobserver-auto-pays-three-bst-show-calls-before-the-build.md)
- [UX-1072](docs/backlog/scenarios/UX-1072-the-snapshot-tail-analyzes-the-run-once.md) — [the snapshot tail analyzes the run once, not twice](docs/backlog/scenarios/UX-1072-the-snapshot-tail-analyzes-the-run-once.md)
- [UX-1075](docs/backlog/scenarios/UX-1075-the-raw-log-is-compressed-at-level-six.md) — [the raw Plane 2 log is compressed at gzip level 9, 5x slower than level 6 for 3% size](docs/backlog/scenarios/UX-1075-the-raw-log-is-compressed-at-level-six.md)
- [UX-1076](docs/backlog/scenarios/UX-1076-the-open-paths-are-interned.md) — [the Plane 2 report holds each element's opened paths as separate strings](docs/backlog/scenarios/UX-1076-the-open-paths-are-interned.md)
- [UX-1078](docs/backlog/scenarios/UX-1078-the-snapshot-records-bgas-own-cost.md) — [a snapshot does not record what bga itself cost the build](docs/backlog/scenarios/UX-1078-the-snapshot-records-bgas-own-cost.md)
- [UX-1079](docs/backlog/scenarios/UX-1079-capture-report-reads-opens-from-a-gzipped-log.md) — [`bga capture report` on a gzipped raw log drops every opened path, silently](docs/backlog/scenarios/UX-1079-capture-report-reads-opens-from-a-gzipped-log.md)
- [UX-1080](docs/backlog/scenarios/UX-1080-the-tails-buildstream-calls-are-measured.md) — [the BuildStream calls bga makes around the build have never been timed](docs/backlog/scenarios/UX-1080-the-tails-buildstream-calls-are-measured.md)
- [UX-1082](docs/backlog/scenarios/UX-1082-the-cache-key-set-reads-the-builds-options.md) — [the cache key set is read without the build's own options, and silently](docs/backlog/scenarios/UX-1082-the-cache-key-set-reads-the-builds-options.md)
- [UX-1083](docs/backlog/scenarios/UX-1083-an-equal-key-set-reuses-the-graph.md) — [a build whose key set equals the baseline's reads its graph again](docs/backlog/scenarios/UX-1083-an-equal-key-set-reuses-the-graph.md)
- [UX-1110](docs/backlog/scenarios/UX-1110-the-width-calibration-runs-on-every-pr.md) — [the width calibration runs on every pull request and gates nothing](docs/backlog/scenarios/UX-1110-the-width-calibration-runs-on-every-pr.md)
- [UX-1116](docs/backlog/scenarios/UX-1116-the-hook-is-built-without-warnings.md) — [the LD_PRELOAD hook is built with no warnings and never runs under a sanitizer](docs/backlog/scenarios/UX-1116-the-hook-is-built-without-warnings.md)
- [UX-1117](docs/backlog/scenarios/UX-1117-the-log-parser-has-no-property-tests.md) — [the scheduler-log parser is tested only on the logs someone thought to write](docs/backlog/scenarios/UX-1117-the-log-parser-has-no-property-tests.md)
- [UX-1124](docs/backlog/scenarios/UX-1124-parse-timestamp-reads-the-wrappers-utc-stamp-as-local.md) — [`parse_timestamp` reads the wrapper's UTC stamp as local time](docs/backlog/scenarios/UX-1124-parse-timestamp-reads-the-wrappers-utc-stamp-as-local.md)
- [UX-1007](docs/backlog/scenarios/UX-1007-a-width-promised-through-maxjobs-reads-unknown-kind.md) — [a width promised through MAXJOBS or MAX_JOBS reads unknown_kind](docs/backlog/scenarios/UX-1007-a-width-promised-through-maxjobs-reads-unknown-kind.md)
- [UX-1010](docs/backlog/scenarios/UX-1010-a-second-fixture-for-the-jobservers-breadth-win.md) — [a second fixture for the jobserver's breadth win - one giant, many single-core elements](docs/backlog/scenarios/UX-1010-a-second-fixture-for-the-jobservers-breadth-win.md)
- [UX-1132](docs/backlog/scenarios/UX-1132-new-jobserver-shapes-for-the-default.md) — [three new example shapes and their arm legs test the "safe cap plus auto" default](docs/backlog/scenarios/UX-1132-new-jobserver-shapes-for-the-default.md)
- [UX-1013](docs/backlog/scenarios/UX-1013-admission-ranks-from-buildstreams-own-cached-build-logs.md) — [admission ranks from BuildStream's own cached build logs when bga never captured the project](docs/backlog/scenarios/UX-1013-admission-ranks-from-buildstreams-own-cached-build-logs.md)

**viewer**

- [UX-834](docs/backlog/scenarios/UX-0834-a-disclosure-without-aria-expanded-and-a-link-whose-name-glues-three-values.md) — [a disclosure without aria-expanded, and a link whose name glues three values](docs/backlog/scenarios/UX-0834-a-disclosure-without-aria-expanded-and-a-link-whose-name-glues-three-values.md)
- [UX-825](docs/backlog/scenarios/UX-0825-thirty-seven-raw-section-keys-are-visible-beside-their-headings.md) — [thirty-seven raw section keys are visible beside their headings](docs/backlog/scenarios/UX-0825-thirty-seven-raw-section-keys-are-visible-beside-their-headings.md)
- [UX-822](docs/backlog/scenarios/UX-0822-the-readers-table-repeats-the-header-picker-s-five-labels.md) — [the readers table repeats the header picker's five labels](docs/backlog/scenarios/UX-0822-the-readers-table-repeats-the-header-picker-s-five-labels.md)
- [UX-819](docs/backlog/scenarios/UX-0819-the-export-s-perfetto-handoff-fetches-a-quoted-data-uri.md) — [the export's Perfetto handoff fetches a quoted data: URI](docs/backlog/scenarios/UX-0819-the-export-s-perfetto-handoff-fetches-a-quoted-data-uri.md)
- [UX-828](docs/backlog/scenarios/UX-0828-the-header-spends-14-of-the-viewport-on-a-filesystem-path.md) — [the header spends 14% of the viewport on a filesystem path](docs/backlog/scenarios/UX-0828-the-header-spends-14-of-the-viewport-on-a-filesystem-path.md)
- [UX-831](docs/backlog/scenarios/UX-0831-a-max-jobs-advice-row-is-four-levels-deep.md) — [a max-jobs advice row is four levels deep](docs/backlog/scenarios/UX-0831-a-max-jobs-advice-row-is-four-levels-deep.md)
- [UX-829](docs/backlog/scenarios/UX-0829-five-of-seven-joined-fields-on-the-elements-table-draw-no-column.md) — [five of seven joined fields on the elements table draw no column](docs/backlog/scenarios/UX-0829-five-of-seven-joined-fields-on-the-elements-table-draw-no-column.md)
- [UX-837](docs/backlog/scenarios/UX-0837-structured-js-sits-at-the-ceiling-the-copy-format-preference-moves-out.md) — [structured.js sits at the ceiling;
- [UX-840](docs/backlog/scenarios/UX-0840-the-3e-summary-table-is-one-item-behind-the-bound-it-summarises.md) — [the §3e summary table is one item behind the bound it summarises](docs/backlog/scenarios/UX-0840-the-3e-summary-table-is-one-item-behind-the-bound-it-summarises.md)
- [UX-864](docs/backlog/scenarios/UX-0864-a-one-key-per-item-map-is-a-table-with-filters.md) — [a one-key-per-item map is a table with filters](docs/backlog/scenarios/UX-0864-a-one-key-per-item-map-is-a-table-with-filters.md)
- [UX-862](docs/backlog/scenarios/UX-0862-the-twin-table-hides-on-screen.md) — [the twin table hides on screen](docs/backlog/scenarios/UX-0862-the-twin-table-hides-on-screen.md)
- [UX-863](docs/backlog/scenarios/UX-0863-the-density-strip-ticks-every-mark-its-twin-lists.md) — [the density strip ticks every mark its twin lists](docs/backlog/scenarios/UX-0863-the-density-strip-ticks-every-mark-its-twin-lists.md)
- [UX-868](docs/backlog/scenarios/UX-0868-a-merged-edge-tick-sits-flush-with-its-edge.md) — [a merged edge tick sits flush with its edge](docs/backlog/scenarios/UX-0868-a-merged-edge-tick-sits-flush-with-its-edge.md)
- [UX-921](docs/backlog/scenarios/UX-0921-hidden-findings-keep-live-controls.md) — [hidden findings keep live controls](docs/backlog/scenarios/UX-0921-hidden-findings-keep-live-controls.md)
- [UX-1015](docs/backlog/scenarios/UX-1015-find-in-page-reaches-folded-chapters.md) — [find-in-page reaches text inside a folded chapter](docs/backlog/scenarios/UX-1015-find-in-page-reaches-folded-chapters.md)
- [UX-1016](docs/backlog/scenarios/UX-1016-one-focus-ring-and-a-keyboard-journey.md) — [every focusable control wears one focus ring, and a keyboard journey reaches every chapter](docs/backlog/scenarios/UX-1016-one-focus-ring-and-a-keyboard-journey.md)
- [UX-1017](docs/backlog/scenarios/UX-1017-every-drawing-has-a-name-and-a-data-route.md) — [every drawing has an accessible name and a route to its numbers](docs/backlog/scenarios/UX-1017-every-drawing-has-a-name-and-a-data-route.md)
- [UX-1018](docs/backlog/scenarios/UX-1018-a-chapter-title-outranks-its-section-titles.md) — [a chapter title outranks its section titles in the heading outline](docs/backlog/scenarios/UX-1018-a-chapter-title-outranks-its-section-titles.md)
- [UX-1019](docs/backlog/scenarios/UX-1019-one-concept-one-word-one-control.md) — [one concept is one word and one control on every bga surface](docs/backlog/scenarios/UX-1019-one-concept-one-word-one-control.md)
- [UX-1020](docs/backlog/scenarios/UX-1020-sentence-case-from-a-rendered-string-inventory.md) — [every rendered label is sentence case, and a plural follows its count](docs/backlog/scenarios/UX-1020-sentence-case-from-a-rendered-string-inventory.md)
- [UX-1021](docs/backlog/scenarios/UX-1021-one-door-per-block.md) — [one `?` door per block opens every description in it](docs/backlog/scenarios/UX-1021-one-door-per-block.md)
- [UX-1022](docs/backlog/scenarios/UX-1022-controls-meet-the-target-size.md) — [every control is at least 24x24 CSS px, 44 under a coarse pointer](docs/backlog/scenarios/UX-1022-controls-meet-the-target-size.md)
- [UX-1023](docs/backlog/scenarios/UX-1023-a-compact-size-class.md) — [the page has a compact size class, and compact draws no empty chrome](docs/backlog/scenarios/UX-1023-a-compact-size-class.md)
- [UX-1024](docs/backlog/scenarios/UX-1024-an-absence-is-one-sentence.md) — [an absence is one sentence, and no separator stands beside an empty value](docs/backlog/scenarios/UX-1024-an-absence-is-one-sentence.md)
- [UX-1025](docs/backlog/scenarios/UX-1025-one-disclosure-glyph-pair.md) — [one disclosure glyph pair, and a fold's label names its content](docs/backlog/scenarios/UX-1025-one-disclosure-glyph-pair.md)
- [UX-1026](docs/backlog/scenarios/UX-1026-spacing-comes-from-a-scale.md) — [spacing comes from a 4px scale of tokens](docs/backlog/scenarios/UX-1026-spacing-comes-from-a-scale.md)
- [UX-1027](docs/backlog/scenarios/UX-1027-a-primary-control-grade.md) — [one control per view wears a primary grade](docs/backlog/scenarios/UX-1027-a-primary-control-grade.md)
- [UX-1028](docs/backlog/scenarios/UX-1028-all-rows-draws-past-a-ceiling.md) — ["All rows" draws the whole table past any ceiling](docs/backlog/scenarios/UX-1028-all-rows-draws-past-a-ceiling.md)
- [UX-1029](docs/backlog/scenarios/UX-1029-the-more-reveal-draws-every-name.md) — [the "+N more" reveal draws every name in one run of text](docs/backlog/scenarios/UX-1029-the-more-reveal-draws-every-name.md)
- [UX-1030](docs/backlog/scenarios/UX-1030-a-json-door-draws-a-whole-section.md) — [a "view as JSON" door draws a whole section as one node](docs/backlog/scenarios/UX-1030-a-json-door-draws-a-whole-section.md)
- [UX-1032](docs/backlog/scenarios/UX-1032-the-bound-census-presses-every-step.md) — [the §3k census presses every step control at the largest size class](docs/backlog/scenarios/UX-1032-the-bound-census-presses-every-step.md)
- [UX-1033](docs/backlog/scenarios/UX-1033-form-controls-take-the-type-scale.md) — [form controls take the type scale, not the browser's 13.333px](docs/backlog/scenarios/UX-1033-form-controls-take-the-type-scale.md)
- [UX-1034](docs/backlog/scenarios/UX-1034-reader-chips-print-internal-keys.md) — [reader chips print R1 to R5 inside section headings](docs/backlog/scenarios/UX-1034-reader-chips-print-internal-keys.md)
- [UX-1035](docs/backlog/scenarios/UX-1035-fonts-compute-to-the-two-stacks.md) — [fonts compute to the two declared stacks, not Arial or bare monospace](docs/backlog/scenarios/UX-1035-fonts-compute-to-the-two-stacks.md)
- [UX-1037](docs/backlog/scenarios/UX-1037-a-growing-container-with-no-bounding-control.md) — [26 payload containers grow with the run and no §1 control bounds them](docs/backlog/scenarios/UX-1037-a-growing-container-with-no-bounding-control.md)
- [UX-1042](docs/backlog/scenarios/UX-1042-pointer-travel-is-a-budget.md) — [pointer travel is a budget, measured per journey](docs/backlog/scenarios/UX-1042-pointer-travel-is-a-budget.md)
- [UX-1043](docs/backlog/scenarios/UX-1043-a-sections-controls-sit-together.md) — [a section's fold, door and JSON toggle sit together, at one place](docs/backlog/scenarios/UX-1043-a-sections-controls-sit-together.md)
- [UX-1044](docs/backlog/scenarios/UX-1044-a-chapter-fold-has-one-place-and-one-label.md) — [a chapter's fold sits at one place and says the same thing in the rail and the document](docs/backlog/scenarios/UX-1044-a-chapter-fold-has-one-place-and-one-label.md)
- [UX-1046](docs/backlog/scenarios/UX-1046-the-rail-shows-the-current-chapter-or-every-open-one.md) — [the rail shows the current chapter's sections, or every open chapter's — one rule](docs/backlog/scenarios/UX-1046-the-rail-shows-the-current-chapter-or-every-open-one.md)
- [UX-1047](docs/backlog/scenarios/UX-1047-the-page-h1-names-the-run.md) — [the page's one `h1` is the run, or §6e.1 says it is the wordmark](docs/backlog/scenarios/UX-1047-the-page-h1-names-the-run.md)
- [UX-1048](docs/backlog/scenarios/UX-1048-the-accent-lists-every-job-it-does.md) — [§4 lists every job the accent does, and the fills it takes](docs/backlog/scenarios/UX-1048-the-accent-lists-every-job-it-does.md)
- [UX-1049](docs/backlog/scenarios/UX-1049-one-landed-height-bound-per-size-class.md) — [the landed page has one bound per size class, written once](docs/backlog/scenarios/UX-1049-one-landed-height-bound-per-size-class.md)
- [UX-1050](docs/backlog/scenarios/UX-1050-the-budgets-are-measured-with-both-planes-at-scale.md) — [the volume budgets are measured on a two-plane page at scale](docs/backlog/scenarios/UX-1050-the-budgets-are-measured-with-both-planes-at-scale.md)
- [UX-1051](docs/backlog/scenarios/UX-1051-every-select-wears-a-resting-grade.md) — [every `select` and `input` wears a declared resting appearance](docs/backlog/scenarios/UX-1051-every-select-wears-a-resting-grade.md)
- [UX-1052](docs/backlog/scenarios/UX-1052-the-viewer-js-ships-compressed.md) — [the export carries its viewer JS gzipped, and a guard bounds its bytes](docs/backlog/scenarios/UX-1052-the-viewer-js-ships-compressed.md)
- [UX-1053](docs/backlog/scenarios/UX-1053-a-two-plane-pages-growth-is-bounded-by-section.md) — [a two-plane page's growth with the run is bounded by the section that grows](docs/backlog/scenarios/UX-1053-a-two-plane-pages-growth-is-bounded-by-section.md)
- [UX-1054](docs/backlog/scenarios/UX-1054-the-first-tab-starts-at-the-top.md) — [the first Tab from a fresh load starts at the top of the page](docs/backlog/scenarios/UX-1054-the-first-tab-starts-at-the-top.md)
- [UX-1055](docs/backlog/scenarios/UX-1055-a-tables-copy-and-top-n-sit-in-one-place.md) — [a table's Copy rows and top-N controls sit in one place in its tool row](docs/backlog/scenarios/UX-1055-a-tables-copy-and-top-n-sit-in-one-place.md)
- [UX-1081](docs/backlog/scenarios/UX-1081-the-export-predicts-the-timeline-it-can-carry.md) — [`bga view --export` renders a whole timeline before refusing it and rendering a narrower one](docs/backlog/scenarios/UX-1081-the-export-predicts-the-timeline-it-can-carry.md)
- [UX-1127](docs/backlog/scenarios/UX-1127-codeql-findings-on-the-viewer-server.md) — [the viewer's pre-flight echoes any header list, and CodeQL reads the asset path as the request's](docs/backlog/scenarios/UX-1127-codeql-findings-on-the-viewer-server.md)
- [UX-1107](docs/backlog/scenarios/UX-1107-the-exports-anchor-breaks-a-tie-by-set-order.md) — [the export's anchor breaks a tie by set order](docs/backlog/scenarios/UX-1107-the-exports-anchor-breaks-a-tie-by-set-order.md)
- [UX-1057](docs/backlog/scenarios/UX-1057-the-drawing-routes-twin-table-drops-the-lower-bound-mark.md) — [the decomposition bar's aria-details twin table drops the certified lower-bound mark](docs/backlog/scenarios/UX-1057-the-drawing-routes-twin-table-drops-the-lower-bound-mark.md)
- [UX-1130](docs/backlog/scenarios/UX-1130-the-resting-appearance-guard-reads-weight-against-the-parent.md) — [the resting-appearance guard reads a weight equal to the parent's as inherited](docs/backlog/scenarios/UX-1130-the-resting-appearance-guard-reads-weight-against-the-parent.md)
- [UX-1056](docs/backlog/scenarios/UX-1056-back-after-a-reveal-does-not-re-fold.md) — [navigating back after an in-page reveal does not re-fold the chapter](docs/backlog/scenarios/UX-1056-back-after-a-reveal-does-not-re-fold.md)
- [UX-1058](docs/backlog/scenarios/UX-1058-the-narrow-rail-toggle-is-unreachable-by-keyboard.md) — [the narrow-rail fold toggle is a click-only `<p>`, unreachable by keyboard](docs/backlog/scenarios/UX-1058-the-narrow-rail-toggle-is-unreachable-by-keyboard.md)
- [UX-1045](docs/backlog/scenarios/UX-1045-a-tables-tools-are-one-row.md) — [§3's tool row names the column thresholds §3d attaches to their headers](docs/backlog/scenarios/UX-1045-a-tables-tools-are-one-row.md)

**store**

- [UX-1061](docs/backlog/scenarios/UX-1061-a-pseudonym-is-keyed-stable-and-keeps-the-names-shape.md) — [a pseudonym is keyed, stable, and keeps the name's shape](docs/backlog/scenarios/UX-1061-a-pseudonym-is-keyed-stable-and-keeps-the-names-shape.md)
- [UX-1067](docs/backlog/scenarios/UX-1067-the-archive-and-its-manifest-carry-no-original-metadata.md) — [the archive and its manifest carry no original metadata](docs/backlog/scenarios/UX-1067-the-archive-and-its-manifest-carry-no-original-metadata.md)
- [UX-1062](docs/backlog/scenarios/UX-1062-a-bundle-exports-anonymized-and-refuses-a-leftover-name.md) — [a bundle exports anonymized, and refuses a leftover name](docs/backlog/scenarios/UX-1062-a-bundle-exports-anonymized-and-refuses-a-leftover-name.md)
- [UX-1065](docs/backlog/scenarios/UX-1065-a-declared-public-junction-keeps-its-public-names.md) — [a declared public junction keeps its public names](docs/backlog/scenarios/UX-1065-a-declared-public-junction-keeps-its-public-names.md)
- [UX-1068](docs/backlog/scenarios/UX-1068-a-credential-in-a-command-line-is-dropped-not-kept.md) — [a credential in a command line is dropped, not kept](docs/backlog/scenarios/UX-1068-a-credential-in-a-command-line-is-dropped-not-kept.md)
- [UX-1069](docs/backlog/scenarios/UX-1069-the-anonymized-export-runs-in-bounded-memory.md) — [the anonymized export runs in bounded memory](docs/backlog/scenarios/UX-1069-the-anonymized-export-runs-in-bounded-memory.md)
- [UX-1071](docs/backlog/scenarios/UX-1071-the-residue-scan-reads-a-large-member-in-linear-time.md) — [the residue scan reads a large member in linear time](docs/backlog/scenarios/UX-1071-the-residue-scan-reads-a-large-member-in-linear-time.md)
- [UX-1084](docs/backlog/scenarios/UX-1084-a-short-numeric-credential-still-exports-verbatim.md) — [a short numeric credential still exports verbatim](docs/backlog/scenarios/UX-1084-a-short-numeric-credential-still-exports-verbatim.md)
- [UX-1085](docs/backlog/scenarios/UX-1085-the-residue-scan-misses-non-ascii-identifiers.md) — [the residue scan misses non-ASCII identifiers](docs/backlog/scenarios/UX-1085-the-residue-scan-misses-non-ascii-identifiers.md)
- [UX-1086](docs/backlog/scenarios/UX-1086-the-archive-publishes-before-the-map-is-saved.md) — [the archive publishes before the map is saved](docs/backlog/scenarios/UX-1086-the-archive-publishes-before-the-map-is-saved.md)
- [UX-1087](docs/backlog/scenarios/UX-1087-the-bounded-memory-measurement-holds-identifiers-constant.md) — [the bounded-memory measurement holds identifiers constant](docs/backlog/scenarios/UX-1087-the-bounded-memory-measurement-holds-identifiers-constant.md)
- [UX-1088](docs/backlog/scenarios/UX-1088-an-unrecognized-numeric-value-is-dropped-not-mapped.md) — [an unrecognized numeric value is dropped, not mapped](docs/backlog/scenarios/UX-1088-an-unrecognized-numeric-value-is-dropped-not-mapped.md)
- [UX-1089](docs/backlog/scenarios/UX-1089-a-glued-j-keeps-its-digits-only-on-a-make-like-tool.md) — [a glued -j keeps its digits only on a make-like tool](docs/backlog/scenarios/UX-1089-a-glued-j-keeps-its-digits-only-on-a-make-like-tool.md)
- [UX-1066](docs/backlog/scenarios/UX-1066-raw-logs-travel-tokenized.md) — [raw logs travel tokenized](docs/backlog/scenarios/UX-1066-raw-logs-travel-tokenized.md)
- [UX-900](docs/backlog/scenarios/UX-0900-a-store-is-a-directory-but-ci-keeps-bundles.md) — [a store is a directory, but CI will keep bundles in versioned directories](docs/backlog/scenarios/UX-0900-a-store-is-a-directory-but-ci-keeps-bundles.md)

**guards**

- [UX-821](docs/backlog/scenarios/UX-0821-the-adopt-jobs-run-a-tool-on-a-bare-interpreter.md) — [the adopt jobs run a tool on a bare interpreter](docs/backlog/scenarios/UX-0821-the-adopt-jobs-run-a-tool-on-a-bare-interpreter.md)
- [UX-836](docs/backlog/scenarios/UX-0836-the-page-census-lists-no-tables.md) — [the page census lists no tables](docs/backlog/scenarios/UX-0836-the-page-census-lists-no-tables.md)
- [UX-835](docs/backlog/scenarios/UX-0835-a-capped-table-filters-every-column-it-sorts.md) — [a capped table filters every column it sorts](docs/backlog/scenarios/UX-0835-a-capped-table-filters-every-column-it-sorts.md)
- [UX-818](docs/backlog/scenarios/UX-0818-two-canned-queries-error-when-an-element-is-given.md) — [two canned queries error when an element is given](docs/backlog/scenarios/UX-0818-two-canned-queries-error-when-an-element-is-given.md)
- [UX-824](docs/backlog/scenarios/UX-0824-reader-facing-strings-the-rule-and-a-guard-that-reads-the-page.md) — [reader-facing strings: the rule, and a guard that reads the page](docs/backlog/scenarios/UX-0824-reader-facing-strings-the-rule-and-a-guard-that-reads-the-page.md)
- [UX-844](docs/backlog/scenarios/UX-0844-the-cache-key-is-equal-with-and-without-the-jobserver.md) — [the cache key is equal with and without the jobserver](docs/backlog/scenarios/UX-0844-the-cache-key-is-equal-with-and-without-the-jobserver.md)
- [UX-855](docs/backlog/scenarios/UX-0855-the-ninja-probe-has-its-own-guard.md) — [the ninja probe has its own guard](docs/backlog/scenarios/UX-0855-the-ninja-probe-has-its-own-guard.md)
- [UX-886](docs/backlog/scenarios/UX-0886-the-token-refill-guard-has-a-2s-timing-flake.md) — [the token-refill guard has a 2s SIGKILL-timing flake](docs/backlog/scenarios/UX-0886-the-token-refill-guard-has-a-2s-timing-flake.md)
- [UX-885](docs/backlog/scenarios/UX-0885-the-push-gate-runs-make-lint-not-only-make-test.md) — [the push gate runs `make lint`, not only `make test`](docs/backlog/scenarios/UX-0885-the-push-gate-runs-make-lint-not-only-make-test.md)
- [UX-887](docs/backlog/scenarios/UX-0887-the-implementer-brief-repoints-the-editable-install.md) — [the implementer brief's dev-deps reinstall repoints the shared editable install](docs/backlog/scenarios/UX-0887-the-implementer-brief-repoints-the-editable-install.md)
- [UX-889](docs/backlog/scenarios/UX-0889-the-env-check-pin-checks-ruff-and-nothing-else.md) — [the pre-gate env check pin-checks ruff and nothing else](docs/backlog/scenarios/UX-0889-the-env-check-pin-checks-ruff-and-nothing-else.md)
- [UX-911](docs/backlog/scenarios/UX-0911-the-styleguide-scan-rereads-every-document-once-per-candidate.md) — [the styleguide scan re-reads every tracked document once per candidate](docs/backlog/scenarios/UX-0911-the-styleguide-scan-rereads-every-document-once-per-candidate.md)
- [UX-910](docs/backlog/scenarios/UX-0910-the-serial-giant-gate-asserts-an-unbanded-inequality.md) — [the serial-giant gate asserts an unbanded inequality the jobserver cannot satisfy](docs/backlog/scenarios/UX-0910-the-serial-giant-gate-asserts-an-unbanded-inequality.md)
- [UX-909](docs/backlog/scenarios/UX-0909-the-documentation-guard-cannot-see-a-blocks-own-keys.md) — [the documentation guard cannot see a published block's own keys](docs/backlog/scenarios/UX-0909-the-documentation-guard-cannot-see-a-blocks-own-keys.md)
- [UX-918](docs/backlog/scenarios/UX-0918-the-wrapper-shims-need-coreutils-a-staged-sandbox-has-not-got.md) — [the wrapper shims open on `dirname`, which a staged-toolchain sandbox has not got](docs/backlog/scenarios/UX-0918-the-wrapper-shims-need-coreutils-a-staged-sandbox-has-not-got.md)
- [UX-913](docs/backlog/scenarios/UX-0913-the-jobserver-scrubs-itself-off-every-cmake-element-under-make-43.md) — [the jobserver scrubs itself off every cmake element under a make-4.3 sandbox](docs/backlog/scenarios/UX-0913-the-jobserver-scrubs-itself-off-every-cmake-element-under-make-43.md)
- [UX-915](docs/backlog/scenarios/UX-0915-the-examples-stage-the-hosts-make-so-auto-never-meets-a-4-4.md) — [the examples stage the host's own make, so `--jobserver auto` has never met a make 4.4](docs/backlog/scenarios/UX-0915-the-examples-stage-the-hosts-make-so-auto-never-meets-a-4-4.md)
- [UX-916](docs/backlog/scenarios/UX-0916-only-one-make-is-staged-so-the-version-switch-has-one-live-branch.md) — [only one make is ever staged, so the version switch has one live branch](docs/backlog/scenarios/UX-0916-only-one-make-is-staged-so-the-version-switch-has-one-live-branch.md)
- [UX-914](docs/backlog/scenarios/UX-0914-the-examples-sysroot-is-the-hosts-so-the-examples-measure-the-host.md) — [the examples' sysroot is the host's own /usr/bin](docs/backlog/scenarios/UX-0914-the-examples-sysroot-is-the-hosts-so-the-examples-measure-the-host.md)
- [UX-922](docs/backlog/scenarios/UX-0922-a-squash-merge-redates-a-round-document.md) — [a squash merge redates a round document](docs/backlog/scenarios/UX-0922-a-squash-merge-redates-a-round-document.md)
- [UX-908](docs/backlog/scenarios/UX-0908-the-drawing-grade-guard-excurses-three-times-and-rising.md) — [the drawing-grade guard's excursions are a stale record, not a rising cost](docs/backlog/scenarios/UX-0908-the-drawing-grade-guard-excurses-three-times-and-rising.md)
- [UX-923](docs/backlog/scenarios/UX-0923-the-base-carry-restore-asks-for-a-version-no-save-wrote.md) — [the base-carry restore names a path no save wrote, so its cache version never matches](docs/backlog/scenarios/UX-0923-the-base-carry-restore-asks-for-a-version-no-save-wrote.md)
- [UX-924](docs/backlog/scenarios/UX-0924-the-adopt-route-feeds-the-committed-median-back-to-itself.md) — [the adopt route feeds the committed median back to itself, so a reference entry is write-once](docs/backlog/scenarios/UX-0924-the-adopt-route-feeds-the-committed-median-back-to-itself.md)
- [UX-927](docs/backlog/scenarios/UX-0927-a-pin-is-one-nar-so-a-staged-compiler-reaches-outside-itself.md) — [a pin is one NAR, so a compiler staged that way reaches outside itself, and nothing in the tree says so](docs/backlog/scenarios/UX-0927-a-pin-is-one-nar-so-a-staged-compiler-reaches-outside-itself.md)
- [UX-930](docs/backlog/scenarios/UX-0930-the-toolchain-parameters-are-assumed-not-read-back.md) — [the toolchain's two parameters are assumed rather than read back, and the one that decides which `cc1` runs fails silently](docs/backlog/scenarios/UX-0930-the-toolchain-parameters-are-assumed-not-read-back.md)
- [UX-931](docs/backlog/scenarios/UX-0931-the-pin-verifies-the-wrapper-not-the-store-path.md) — [the pin verifies the compressed wrapper, not the store path, so a cache that re-compresses reds as a broken pin](docs/backlog/scenarios/UX-0931-the-pin-verifies-the-wrapper-not-the-store-path.md)
- [UX-933](docs/backlog/scenarios/UX-0933-a-dev-extra-absent-reds-a-correct-tree.md) — [the `zstd` clauses fail where every other optional prerequisite skips, so a tree without the extra reads as a broken one](docs/backlog/scenarios/UX-0933-a-dev-extra-absent-reds-a-correct-tree.md)
- [UX-939](docs/backlog/scenarios/UX-0939-the-exercised-line-names-an-environment-nothing-can-read.md) — [the exercised line names an environment nothing can read, so a version bump in CI reds every branch](docs/backlog/scenarios/UX-0939-the-exercised-line-names-an-environment-nothing-can-read.md)
- [UX-925](docs/backlog/scenarios/UX-0925-the-toolchain-axis-is-host-gcc-because-gcc-is-not-relocatable.md) — [the toolchain axis is this host's gcc, because gcc's search paths are not relocatable](docs/backlog/scenarios/UX-0925-the-toolchain-axis-is-host-gcc-because-gcc-is-not-relocatable.md)
- [UX-934](docs/backlog/scenarios/UX-0934-the-adopt-jobs-push-with-a-token-that-triggers-no-workflow.md) — [the three adopt jobs push with a token that triggers no workflow, so a commit that reds `main` carries no CI](docs/backlog/scenarios/UX-0934-the-adopt-jobs-push-with-a-token-that-triggers-no-workflow.md)
- [UX-943](docs/backlog/scenarios/UX-0943-the-adopt-jobs-run-on-a-run-whose-suite-failed.md) — [the adopt jobs write to the default branch from a run whose whole suite failed](docs/backlog/scenarios/UX-0943-the-adopt-jobs-run-on-a-run-whose-suite-failed.md)
- [UX-936](docs/backlog/scenarios/UX-0936-a-heavy-fixture-guard-excurses-on-a-record-that-is-not-too-low.md) — [a heavy-fixture guard excurses three times on a record that is not too low, so the ledger is reading the runner](docs/backlog/scenarios/UX-0936-a-heavy-fixture-guard-excurses-on-a-record-that-is-not-too-low.md)
- [UX-890](docs/backlog/scenarios/UX-0890-the-trace-census-guard-has-three-unconfirmed-excursions.md) — [the trace-census guard has three unconfirmed CI excursions and no filing](docs/backlog/scenarios/UX-0890-the-trace-census-guard-has-three-unconfirmed-excursions.md)
- [UX-917](docs/backlog/scenarios/UX-0917-the-fold-depth-guard-has-three-unconfirmed-excursions.md) — [the fold-depth guard has three unconfirmed CI excursions, spread over three weeks](docs/backlog/scenarios/UX-0917-the-fold-depth-guard-has-three-unconfirmed-excursions.md)
- [UX-944](docs/backlog/scenarios/UX-0944-the-sysroot-fixture-clones-910mb-to-read-nine-files.md) — [the sysroot fixture clones 910 MB to read nine files, so its cost has two modes 30x apart and the reference entry is the median of…
- [UX-929](docs/backlog/scenarios/UX-0929-two-population-sized-guards-reach-three-excursions-in-one-run.md) — [population-sized guards reach three excursions in one run, and their records were frozen](docs/backlog/scenarios/UX-0929-two-population-sized-guards-reach-three-excursions-in-one-run.md)
- [UX-912](docs/backlog/scenarios/UX-0912-the-timing-reference-is-unrepresentative-and-branches-pay-for-it.md) — [the timing reference is unrepresentative on four files, and branches pay for it](docs/backlog/scenarios/UX-0912-the-timing-reference-is-unrepresentative-and-branches-pay-for-it.md)
- [UX-935](docs/backlog/scenarios/UX-0935-a-conflicted-path-is-counted-once-per-stage.md) — [a conflicted path is counted once per stage, so `--check --write` bakes a wrong number and calls the tree clean](docs/backlog/scenarios/UX-0935-a-conflicted-path-is-counted-once-per-stage.md)
- [UX-932](docs/backlog/scenarios/UX-0932-a-sandboxed-check-write-escapes-into-the-tree-it-guards.md) — [a sandboxed `--check --write` escapes into the tree it guards, so `make test` is not read-only](docs/backlog/scenarios/UX-0932-a-sandboxed-check-write-escapes-into-the-tree-it-guards.md)
- [UX-920](docs/backlog/scenarios/UX-0920-two-task-files-can-share-one-id-and-nothing-reads-it.md) — [two task files can share one backlog id, and no guard reads ids for uniqueness](docs/backlog/scenarios/UX-0920-two-task-files-can-share-one-id-and-nothing-reads-it.md)
- [UX-937](docs/backlog/scenarios/UX-0937-the-area-vocabulary-cannot-spell-tests.md) — [the area vocabulary is derived by a regex that admits two of the tree's three top-level directories, so no row can declare `tests`](docs/backlog/scenarios/UX-0937-the-area-vocabulary-cannot-spell-tests.md)
- [UX-942](docs/backlog/scenarios/UX-0942-the-selector-misses-a-guard-that-reads-a-record-through-a-tool.md) — [the touching selector misses a guard that reads a record through a tool's constant](docs/backlog/scenarios/UX-0942-the-selector-misses-a-guard-that-reads-a-record-through-a-tool.md)
- [UX-928](docs/backlog/scenarios/UX-0928-the-routing-rule-sends-a-prose-diff-to-a-protocol-that-opens-on-a-page.md) — [the routing rule sends a prose diff to a protocol that opens on a served page](docs/backlog/scenarios/UX-0928-the-routing-rule-sends-a-prose-diff-to-a-protocol-that-opens-on-a-page.md)
- [UX-940](docs/backlog/scenarios/UX-0940-the-versions-the-behaviour-claims-were-confirmed-on-are-three.md) — [the BuildStream behaviour claims are pinned to three versions and nothing says which were re-confirmed](docs/backlog/scenarios/UX-0940-the-versions-the-behaviour-claims-were-confirmed-on-are-three.md)
- [UX-941](docs/backlog/scenarios/UX-0941-the-only-job-that-builds-anything-is-a-population-of-one.md) — [the one job that builds anything real produces a single number per run and records none of them, so no instrument in this repository can read its…
- [UX-926](docs/backlog/scenarios/UX-0926-a-round-that-leaves-no-trace-is-invisible-to-the-register.md) — [a round that leaves neither a document nor a ledger row is invisible to the register, and so to the guard whose job is to demand its…
- [UX-948](docs/backlog/scenarios/UX-0948-the-push-gate-is-the-whole-suite-and-ci-runs-it-again.md) — [the push gate is the whole suite, and CI runs the same suite again before anything merges](docs/backlog/scenarios/UX-0948-the-push-gate-is-the-whole-suite-and-ci-runs-it-again.md)
- [UX-956](docs/backlog/scenarios/UX-0956-a-docs-only-pull-request-runs-the-whole-matrix.md) — [a docs-only pull request runs the whole matrix, and the selector that could narrow it misses the guards that read documents by glob](docs/backlog/scenarios/UX-0956-a-docs-only-pull-request-runs-the-whole-matrix.md)
- [UX-993](docs/backlog/scenarios/UX-0993-an-architect-shapes-a-row-before-a-round-schedules-it.md) — [an architect shapes a row before a round schedules it](docs/backlog/scenarios/UX-0993-an-architect-shapes-a-row-before-a-round-schedules-it.md)
- [UX-994](docs/backlog/scenarios/UX-0994-a-round-spends-at-most-forty-percent-of-its-rows-on-process.md) — [a round spends at most forty percent of its rows on process](docs/backlog/scenarios/UX-0994-a-round-spends-at-most-forty-percent-of-its-rows-on-process.md)
- [UX-991](docs/backlog/scenarios/UX-0991-the-docs-lanes-first-live-pr-never-ran-green.md) — [UX-956's docs lane never ran green on its first live PR](docs/backlog/scenarios/UX-0991-the-docs-lanes-first-live-pr-never-ran-green.md)
- [UX-996](docs/backlog/scenarios/UX-0996-a-derived-figure-is-computed-where-it-is-read-never-committed.md) — [a derived figure is computed where it is read, never committed](docs/backlog/scenarios/UX-0996-a-derived-figure-is-computed-where-it-is-read-never-committed.md)
- [UX-995](docs/backlog/scenarios/UX-0995-a-pull-request-runs-the-suite-on-the-newest-python-only.md) — [a pull request runs the suite on the newest Python only;
- [UX-992](docs/backlog/scenarios/UX-0992-the-push-gate-reads-the-main-checkouts-head-from-a-worktree.md) — [the push gate reads the main checkout's `HEAD` from a worktree](docs/backlog/scenarios/UX-0992-the-push-gate-reads-the-main-checkouts-head-from-a-worktree.md)
- [UX-990](docs/backlog/scenarios/UX-0990-the-tools-behaviour-claims-are-outside-the-register.md) — [the BuildStream behaviour claims in `tools/` are outside the register `UX-940` built for `bga/`](docs/backlog/scenarios/UX-0990-the-tools-behaviour-claims-are-outside-the-register.md)
- [UX-998](docs/backlog/scenarios/UX-0998-a-bookkeeping-finding-is-one-line-swept-once-a-round.md) — [a bookkeeping finding is one line in a ledger, swept once a round](docs/backlog/scenarios/UX-0998-a-bookkeeping-finding-is-one-line-swept-once-a-round.md)
- [UX-999](docs/backlog/scenarios/UX-0999-a-weekly-retro-turns-repeated-bookkeeping-into-automation.md) — [a weekly retro turns repeated bookkeeping into automation](docs/backlog/scenarios/UX-0999-a-weekly-retro-turns-repeated-bookkeeping-into-automation.md)
- [UX-979](docs/backlog/scenarios/UX-0979-a-guard-citation-names-a-class-a-rename-retired.md) — [§7a cites a guard class a rename retired, and no guard resolves the part after `::`](docs/backlog/scenarios/UX-0979-a-guard-citation-names-a-class-a-rename-retired.md)
- [UX-977](docs/backlog/scenarios/UX-0977-the-coverage-section-states-the-surface-twice-and-the-guard-reads-one.md) — [the coverage section states the surface twice, and the guard reads one of them](docs/backlog/scenarios/UX-0977-the-coverage-section-states-the-surface-twice-and-the-guard-reads-one.md)
- [UX-945](docs/backlog/scenarios/UX-0945-the-context-map-existence-check-reads-five-typed-top-level-names.md) — [the context map's existence check reads five typed top-level names, so a §6 line under any other directory is never checked against the…
- [UX-997](docs/backlog/scenarios/UX-0997-a-record-ci-measures-lives-outside-main.md) — [a record CI measures lives outside main, and main carries only reviewed commits](docs/backlog/scenarios/UX-0997-a-record-ci-measures-lives-outside-main.md)
- [UX-1000](docs/backlog/scenarios/UX-1000-an-area-page-names-each-scenarios-guard-and-ci-publishes-it.md) — [an area page names each scenario's guard, and CI publishes it where it can be read](docs/backlog/scenarios/UX-1000-an-area-page-names-each-scenarios-guard-and-ci-publishes-it.md)
- [UX-1039](docs/backlog/scenarios/UX-1039-every-agent-names-its-model-and-effort.md) — [every agent names its model and effort, and the seams between tracks have owners](docs/backlog/scenarios/UX-1039-every-agent-names-its-model-and-effort.md)
- [UX-938](docs/backlog/scenarios/UX-0938-an-acceptance-clause-can-name-a-reading-no-environment-takes.md) — [an acceptance clause can name a reading that no environment in this project ever takes, and nothing says so until the round that owes…
- [UX-950](docs/backlog/scenarios/UX-0950-the-flake-ledger-counts-a-runner-event-once-per-file.md) — [the flake ledger's excursions cluster by run, and the census counts a runner event once per file](docs/backlog/scenarios/UX-0950-the-flake-ledger-counts-a-runner-event-once-per-file.md)
- [UX-955](docs/backlog/scenarios/UX-0955-a-population-entry-keeps-the-size-its-seconds-no-longer-describe.md) — [a population entry keeps the tree size its seconds no longer describe, so the gate scales the growth twice](docs/backlog/scenarios/UX-0955-a-population-entry-keeps-the-size-its-seconds-no-longer-describe.md)
- [UX-1041](docs/backlog/scenarios/UX-1041-an-agent-cannot-repoint-the-shared-install-or-run-the-sweep.md) — [an agent cannot repoint the shared install or start the touching sweep](docs/backlog/scenarios/UX-1041-an-agent-cannot-repoint-the-shared-install-or-run-the-sweep.md)
- [UX-1090](docs/backlog/scenarios/UX-1090-the-retro-keys-a-ledger-line-by-its-own-class.md) — [the retro keys a ledger line by its own class, and "none reported" is no finding](docs/backlog/scenarios/UX-1090-the-retro-keys-a-ledger-line-by-its-own-class.md)
- [UX-1091](docs/backlog/scenarios/UX-1091-the-records-writers-queue-instead-of-cancelling.md) — [the records writers queue instead of cancelling each other](docs/backlog/scenarios/UX-1091-the-records-writers-queue-instead-of-cancelling.md)
- [UX-1092](docs/backlog/scenarios/UX-1092-a-scenario-declares-its-guard-in-one-field.md) — [a scenario declares its guard in one field, backfilled from the inferred column](docs/backlog/scenarios/UX-1092-a-scenario-declares-its-guard-in-one-field.md)
- [UX-1093](docs/backlog/scenarios/UX-1093-the-enter-on-a-reached-fold-journey-is-intermittent.md) — [the Enter-on-a-reached-fold journey fails intermittently on the older Pythons](docs/backlog/scenarios/UX-1093-the-enter-on-a-reached-fold-journey-is-intermittent.md)
- [UX-1063](docs/backlog/scenarios/UX-1063-analysis-commutes-with-anonymization.md) — [analysis commutes with anonymization](docs/backlog/scenarios/UX-1063-analysis-commutes-with-anonymization.md)
- [UX-1105](docs/backlog/scenarios/UX-1105-a-page-fixture-split-across-workers-is-built-once.md) — [a page fixture split across workers is built once](docs/backlog/scenarios/UX-1105-a-page-fixture-split-across-workers-is-built-once.md)
- [UX-1102](docs/backlog/scenarios/UX-1102-review-the-architecture-after-298-and-300.md) — [the architecture review is due once #298 and #300 have both landed](docs/backlog/scenarios/UX-1102-review-the-architecture-after-298-and-300.md)
- [UX-1108](docs/backlog/scenarios/UX-1108-ci-cancels-a-superseded-pr-run.md) — [a superseded pull request run keeps burning its runner minutes](docs/backlog/scenarios/UX-1108-ci-cancels-a-superseded-pr-run.md)
- [UX-1109](docs/backlog/scenarios/UX-1109-the-bst-jobs-wait-for-the-suite.md) — [the bst jobs wait for the suite and use nothing it produced](docs/backlog/scenarios/UX-1109-the-bst-jobs-wait-for-the-suite.md)
- [UX-1111](docs/backlog/scenarios/UX-1111-the-small-tier-runs-three-times-per-pr.md) — [the small tier runs three times on every pull request](docs/backlog/scenarios/UX-1111-the-small-tier-runs-three-times-per-pr.md)
- [UX-1112](docs/backlog/scenarios/UX-1112-the-push-gate-relints-all-markdown.md) — [the push gate re-lints ten megabytes of markdown the diff never touched](docs/backlog/scenarios/UX-1112-the-push-gate-relints-all-markdown.md)
- [UX-1113](docs/backlog/scenarios/UX-1113-the-gate-runs-the-tools-on-path-not-the-lock.md) — [the gate runs whichever ruff and pyright are first on PATH, not the locked ones](docs/backlog/scenarios/UX-1113-the-gate-runs-the-tools-on-path-not-the-lock.md)
- [UX-1114](docs/backlog/scenarios/UX-1114-a-fresh-session-starts-shallow-and-unlocked.md) — [a fresh session starts shallow and without the locked dependencies](docs/backlog/scenarios/UX-1114-a-fresh-session-starts-shallow-and-unlocked.md)
- [UX-1115](docs/backlog/scenarios/UX-1115-the-area-pages-publish-from-a-red-run.md) — [the area pages publish from a run whose suite failed](docs/backlog/scenarios/UX-1115-the-area-pages-publish-from-a-red-run.md)
- [UX-1119](docs/backlog/scenarios/UX-1119-docstrings-follow-no-convention.md) — [docstrings follow no convention a tool can read](docs/backlog/scenarios/UX-1119-docstrings-follow-no-convention.md)
- [UX-1120](docs/backlog/scenarios/UX-1120-the-closed-index-is-one-large-file.md) — [the closed index is one 729 KB file the markdown lint reads superlinearly](docs/backlog/scenarios/UX-1120-the-closed-index-is-one-large-file.md)
- [UX-1121](docs/backlog/scenarios/UX-1121-timing-gates-red-prs-for-the-runner.md) — [timing gates red pull requests for the runner's speed](docs/backlog/scenarios/UX-1121-timing-gates-red-prs-for-the-runner.md)
- [UX-1122](docs/backlog/scenarios/UX-1122-a-guard-never-retires.md) — [a guard never retires, so every gate is paid on every pull request forever](docs/backlog/scenarios/UX-1122-a-guard-never-retires.md)
- [UX-1118](docs/backlog/scenarios/UX-1118-nothing-formats-the-code.md) — [nothing formats the code, so layout is argued in review](docs/backlog/scenarios/UX-1118-nothing-formats-the-code.md)
- [UX-1126](docs/backlog/scenarios/UX-1126-the-size-ledger-depends-on-the-walk-order.md) — [the size ledger's duplicate count depends on the filesystem's walk order](docs/backlog/scenarios/UX-1126-the-size-ledger-depends-on-the-walk-order.md)
- [UX-1128](docs/backlog/scenarios/UX-1128-the-weekly-lock-check-reds-on-an-upstream-release.md) — [the weekly lock check reds on any upstream release, so the audit never runs](docs/backlog/scenarios/UX-1128-the-weekly-lock-check-reds-on-an-upstream-release.md)
- [UX-1125](docs/backlog/scenarios/UX-1125-a-red-ledger-gives-the-guard-prices-a-last-catch.md) — [a red ledger gives `dev_guard_prices` a last-catch source](docs/backlog/scenarios/UX-1125-a-red-ledger-gives-the-guard-prices-a-last-catch.md)
- [UX-1129](docs/backlog/scenarios/UX-1129-a-union-merge-reopens-swept-bookkeeping-lines.md) — [a union merge reopens swept bookkeeping lines](docs/backlog/scenarios/UX-1129-a-union-merge-reopens-swept-bookkeeping-lines.md)

**docs**

- [UX-832](docs/backlog/scenarios/UX-0832-the-foundation-declaration-is-in-no-guide.md) — [the foundation declaration is in no guide](docs/backlog/scenarios/UX-0832-the-foundation-declaration-is-in-no-guide.md)
- [UX-820](docs/backlog/scenarios/UX-0820-the-generated-release-body-ends-its-list-on-the-closing-marker.md) — [the generated release body ends its list on the closing marker](docs/backlog/scenarios/UX-0820-the-generated-release-body-ends-its-list-on-the-closing-marker.md)
- [UX-839](docs/backlog/scenarios/UX-0839-the-clone-size-claim-is-half-what-a-clone-now-costs.md) — [the clone-size claim is half what a clone now costs](docs/backlog/scenarios/UX-0839-the-clone-size-claim-is-half-what-a-clone-now-costs.md)
- [UX-867](docs/backlog/scenarios/UX-0867-the-context-maps-open-labels-read-the-status-they-name.md) — [the context map's open labels read the status they name](docs/backlog/scenarios/UX-0867-the-context-maps-open-labels-read-the-status-they-name.md)
- [UX-866](docs/backlog/scenarios/UX-0866-a-key-under-a-bare-object-is-still-a-documented-key.md) — [a key under a bare object is still a documented key](docs/backlog/scenarios/UX-0866-a-key-under-a-bare-object-is-still-a-documented-key.md)
- [UX-978](docs/backlog/scenarios/UX-0978-the-serial-giant-readme-describes-an-assertion-ci-no-longer-makes.md) — [the serial-giant README describes an `auto < off` assertion CI no longer makes](docs/backlog/scenarios/UX-0978-the-serial-giant-readme-describes-an-assertion-ci-no-longer-makes.md)
- [UX-975](docs/backlog/scenarios/UX-0975-the-examples-install-a-host-toolchain-the-stager-no-longer-reads.md) — [the examples still install a host toolchain the stager no longer reads, and two CI comments say it copies from one](docs/backlog/scenarios/UX-0975-the-examples-install-a-host-toolchain-the-stager-no-longer-reads.md)
- [UX-976](docs/backlog/scenarios/UX-0976-the-toolchain-closure-is-35-paths-and-the-readme-counts-the-make-pins-into-it.md) — [the toolchain closure is 35 store paths, and the examples README counts the two make pins into it](docs/backlog/scenarios/UX-0976-the-toolchain-closure-is-35-paths-and-the-readme-counts-the-make-pins-into-it.md)

<!-- /generated -->

## 0.4.1 — the tool says what it assumes (2026-09-12)

Named for what every new number in it carries: the assumption it
rests on, stated beside it. The max-jobs advice (`UX-677`) is priced by
replay (`UX-739`) — two runs of the scheduler's own rule, each capped
element's build floored at its measured CPU over the recommended jobs
— and the figure is published as a **floor** that errs optimistic, with
the two sentences that say so rendered under it (`UX-809`). Remote
execution is priced two ways and never summed (`UX-680`); the cached
build gets a verdict with its dominant elements (`UX-684`); memory
joins the capacity sweep (`UX-678`); the utilisation envelope reads
real cores rather than slots (`UX-675`, `UX-676`). A jobserver every
sandbox joins was built and measured (`UX-679`): the under-utilised
share fell fourfold on `examples/06` at an unchanged wall, so it stays
a capture flag, off by default, until a compile-bound capture moves
its wall.

The architecture document's chapters moved into hand-written area
pages beside the derived tables that keep them honest (`UX-689`, six
moves, no sentence lost), the shelf's Dependabot pull requests can merge
again (`UX-811`), and review 22 found the round records holding.

**Contract delta:** none — the twenty-five contracts and the command
surface are `0.4.0`'s, which makes the row `patch`. What moved sits
inside them: `analyze/v6` gained `utilization_envelope`,
`max_jobs_advice` with its `priced` rows and `priced_jointly`,
`cached_shape` and the `remote-execution-whatif` finding; `sweep/v1`
gained `memory_knee_points` and `binding_constraints`; `bga capture run`
gained `--jobserver N`; the guide's key table stands at 263.

**Upgrade note:** none. Every addition is a new key beside the old
ones, and an older reader ignores what it does not name.

**Carried findings.** Review 22 (closed-row marker 808) filed `UX-813`
and `UX-814`, both closed in the same round. Walk seed 3 (2026-09-12,
on this release's candidate commit) filed three, open at this cut and
named here so "we knew" is on the record: `UX-817` — the join names
the wrong absence on a zero-rebuilt run; `UX-818` — two canned Perfetto
questions error under `--element`; `UX-819` — the export's Perfetto
handoff fetches a quoted `data:` URI. They are the three rows open at
the cut.

```text state
digest: 32a915ff3719
contracts: analyze/v2 analyze/v3 analyze/v4 analyze/v5 analyze/v6 blast/v1 blast/v2 bundle-manifest/v1 capacity-model/v1 capture-layout/v1 compare/v1 compare/v2 correlate/v1 correlate/v2 host-samples/v1 host/v1 host/v2 plane2/v1 plane2/v2 plane2/v3 sources/v1 store-aggregate/v1 store/v1 sweep/v1 whatif/v1
commands: analyze baseline blast bundle cache-logs cache-trend capture checkout-cost chrome-to-trace compare correlate cross-check diagnostics doctor extract floors gen-synthetic graph graph-from-show log-to-chrome native-to-chrome rebuild-set release-notes replay run-context snapshot sweep timeline utilisation view whatif wrap
```

### What landed

<!-- generated: UX-252 537→813 -->
276 scenarios closed (closed-row markers 537 → 813).

**contracts**

- [UX-553](docs/backlog/scenarios/UX-0553-the-holder-set-is-mandated-and-unread.md) — [the resource-holder set is spec-mandated and reaches no reader](docs/backlog/scenarios/UX-0553-the-holder-set-is-mandated-and-unread.md)
- [UX-540](docs/backlog/scenarios/UX-0540-the-three-contracts-bga-reads-and-never-registers.md) — [the three contracts `bga` reads and never registers](docs/backlog/scenarios/UX-0540-the-three-contracts-bga-reads-and-never-registers.md)
- [UX-550](docs/backlog/scenarios/UX-0550-the-newest-release-row-records-the-state-now.md) — [the newest release row records the state *now*, not the one it shipped](docs/backlog/scenarios/UX-0550-the-newest-release-row-records-the-state-now.md)
- [UX-602](docs/backlog/scenarios/UX-0602-two-hard-gates-are-published-and-named-nowhere.md) — [two hard gates are published and named nowhere](docs/backlog/scenarios/UX-0602-two-hard-gates-are-published-and-named-nowhere.md)
- [UX-598](docs/backlog/scenarios/UX-0598-two-of-the-four-percentile-rows-publish-no-distribution.md) — [two of the four percentile rows publish no distribution](docs/backlog/scenarios/UX-0598-two-of-the-four-percentile-rows-publish-no-distribution.md)
- [UX-610](docs/backlog/scenarios/UX-0610-the-verdict-record-is-not-a-published-key.md) — [the verdict record is not a published key](docs/backlog/scenarios/UX-0610-the-verdict-record-is-not-a-published-key.md)
- [UX-613](docs/backlog/scenarios/UX-0613-the-capacity-model-emits-no-document.md) — [the capacity model emits no document](docs/backlog/scenarios/UX-0613-the-capacity-model-emits-no-document.md)
- [UX-628](docs/backlog/scenarios/UX-0628-five-published-keys-no-document-names.md) — [five published keys no document names](docs/backlog/scenarios/UX-0628-five-published-keys-no-document-names.md)
- [UX-629](docs/backlog/scenarios/UX-0629-a-required-set-grew-under-an-unchanged-id.md) — [a required set grew under an unchanged id](docs/backlog/scenarios/UX-0629-a-required-set-grew-under-an-unchanged-id.md)
- [UX-637](docs/backlog/scenarios/UX-0637-a-shallow-clone-answers-and-does-not-say-so.md) — [a shallow clone answers, and does not say so](docs/backlog/scenarios/UX-0637-a-shallow-clone-answers-and-does-not-say-so.md)
- [UX-659](docs/backlog/scenarios/UX-0659-two-superseded-ids-sit-on-a-live-line.md) — [two superseded ids sit on a live line of the spec's registry](docs/backlog/scenarios/UX-0659-two-superseded-ids-sit-on-a-live-line.md)

**cli**

- [UX-574](docs/backlog/scenarios/UX-0574-invalid-arguments-exit-2-which-the-table-gives-to-ingestion.md) — ["invalid arguments" exit 2, which the table gives to ingestion](docs/backlog/scenarios/UX-0574-invalid-arguments-exit-2-which-the-table-gives-to-ingestion.md)
- [UX-575](docs/backlog/scenarios/UX-0575-a-documented-pipe-prints-a-traceback.md) — [a documented pipe prints a traceback](docs/backlog/scenarios/UX-0575-a-documented-pipe-prints-a-traceback.md)
- [UX-725](docs/backlog/scenarios/UX-0725-view-export-prints-two-error-lines-and-exits-zero.md) — [`bga view --export` prints two ERROR lines and exits 0](docs/backlog/scenarios/UX-0725-view-export-prints-two-error-lines-and-exits-zero.md)

**analysis**

- [UX-541](docs/backlog/scenarios/UX-0541-the-gap-sweep-is-cut-but-still-quadratic.md) — [the gap sweep is cut and still quadratic, and the reason is a contract](docs/backlog/scenarios/UX-0541-the-gap-sweep-is-cut-but-still-quadratic.md)
- [UX-542](docs/backlog/scenarios/UX-0542-diagnostics-is-now-the-largest-phase.md) — [`_compute_diagnostics` is now the largest phase of `analyze`](docs/backlog/scenarios/UX-0542-diagnostics-is-now-the-largest-phase.md)
- [UX-563](docs/backlog/scenarios/UX-0563-part-8-2-s-unknown-holder-is-a-state-the-code-cannot-reach.md) — [Part 8.2's `UNKNOWN` holder is a state the code cannot reach](docs/backlog/scenarios/UX-0563-part-8-2-s-unknown-holder-is-a-state-the-code-cannot-reach.md)
- [UX-564](docs/backlog/scenarios/UX-0564-parts-23-and-27-exist-in-the-spec-and-nowhere-else.md) — [Parts 23 and 27 exist in the spec and nowhere else](docs/backlog/scenarios/UX-0564-parts-23-and-27-exist-in-the-spec-and-nowhere-else.md)
- [UX-565](docs/backlog/scenarios/UX-0565-part-29-is-wired-to-none-while-the-store-holds-the-series-it-needs.md) — [Part 29 is wired to `None` while the store holds the series it needs](docs/backlog/scenarios/UX-0565-part-29-is-wired-to-none-while-the-store-holds-the-series-it-needs.md)
- [UX-593](docs/backlog/scenarios/UX-0593-the-regression-verdict-carries-no-evidence-chain.md) — [the regression verdict carries no evidence chain](docs/backlog/scenarios/UX-0593-the-regression-verdict-carries-no-evidence-chain.md)
- [UX-596](docs/backlog/scenarios/UX-0596-build-time-in-the-team-s-units.md) — [build time in the team's units](docs/backlog/scenarios/UX-0596-build-time-in-the-team-s-units.md)
- [UX-611](docs/backlog/scenarios/UX-0611-whatifs-saving-is-still-in-build-seconds.md) — [what-if's saving is still in build seconds](docs/backlog/scenarios/UX-0611-whatifs-saving-is-still-in-build-seconds.md)
- [UX-641](docs/backlog/scenarios/UX-0641-the-levels-key-is-the-identity-function.md) — [the levels key is the identity function](docs/backlog/scenarios/UX-0641-the-levels-key-is-the-identity-function.md)
- [UX-676](docs/backlog/scenarios/UX-0676-the-utilization-envelope-and-the-intervals-that-violate-it.md) — [the utilization envelope, and the intervals that violate it](docs/backlog/scenarios/UX-0676-the-utilization-envelope-and-the-intervals-that-violate-it.md)
- [UX-681](docs/backlog/scenarios/UX-0681-fan-in-what-an-element-depends-on-ranked.md) — [fan-in — what an element depends on, ranked](docs/backlog/scenarios/UX-0681-fan-in-what-an-element-depends-on-ranked.md)
- [UX-724](docs/backlog/scenarios/UX-0724-the-diagnostics-blocks-vanish-on-a-fully-cached-run.md) — [the diagnostics blocks vanish on a fully cached run](docs/backlog/scenarios/UX-0724-the-diagnostics-blocks-vanish-on-a-fully-cached-run.md)
- [UX-719](docs/backlog/scenarios/UX-0719-the-bottleneck-fan-in-and-fan-out-labels-are-swapped.md) — [the bottleneck fan-in and fan-out labels are swapped](docs/backlog/scenarios/UX-0719-the-bottleneck-fan-in-and-fan-out-labels-are-swapped.md)
- [UX-733](docs/backlog/scenarios/UX-0733-the-two-fan-averages-are-the-same-number-and-both-described-wrong.md) — [the two fan averages are the same number, and both described wrong](docs/backlog/scenarios/UX-0733-the-two-fan-averages-are-the-same-number-and-both-described-wrong.md)
- [UX-677](docs/backlog/scenarios/UX-0677-the-max-jobs-advisor-per-element-under-a-no-overcommit-constraint.md) — [the max-jobs advisor — per element, under a no-overcommit constraint](docs/backlog/scenarios/UX-0677-the-max-jobs-advisor-per-element-under-a-no-overcommit-constraint.md)
- [UX-740](docs/backlog/scenarios/UX-0740-a-span-under-the-epsilon-grid-becomes-a-zero-width-segment-and-nothing-says-so.md) — [a span under the epsilon grid becomes a zero-width segment, and nothing says so](docs/backlog/scenarios/UX-0740-a-span-under-the-epsilon-grid-becomes-a-zero-width-segment-and-nothing-says-so.md)
- [UX-682](docs/backlog/scenarios/UX-0682-change-frequency-and-co-change-from-the-logs-the-project-already-keeps.md) — [change frequency and co-change, from the logs the project already keeps](docs/backlog/scenarios/UX-0682-change-frequency-and-co-change-from-the-logs-the-project-already-keeps.md)
- [UX-683](docs/backlog/scenarios/UX-0683-the-foundation-tier-is-declared-and-the-kind-based-exemption-misses-it.md) — [the foundation tier is declared, and the kind-based exemption misses it](docs/backlog/scenarios/UX-0683-the-foundation-tier-is-declared-and-the-kind-based-exemption-misses-it.md)
- [UX-678](docs/backlog/scenarios/UX-0678-memory-joins-the-sweep-and-the-queue-model.md) — [memory joins the sweep and the queue model](docs/backlog/scenarios/UX-0678-memory-joins-the-sweep-and-the-queue-model.md)
- [UX-684](docs/backlog/scenarios/UX-0684-the-cached-build-verdict-does-the-graph-rebuild-the-cheapest-subgraph.md) — [the cached-build verdict — does the graph rebuild the cheapest subgraph?](docs/backlog/scenarios/UX-0684-the-cached-build-verdict-does-the-graph-rebuild-the-cheapest-subgraph.md)
- [UX-680](docs/backlog/scenarios/UX-0680-remote-execution-is-priced-not-built.md) — [remote execution is priced, not built](docs/backlog/scenarios/UX-0680-remote-execution-is-priced-not-built.md)
- [UX-808](docs/backlog/scenarios/UX-0808-the-max-jobs-advice-lists-one-row-per-task-not-per-element.md) — [the max-jobs advice lists one row per task, not per element](docs/backlog/scenarios/UX-0808-the-max-jobs-advice-lists-one-row-per-task-not-per-element.md)
- [UX-739](docs/backlog/scenarios/UX-0739-the-max-jobs-advice-is-not-priced-nothing-says-what-the-build-drops-to.md) — [the max-jobs advice is not priced — nothing says what the build drops to](docs/backlog/scenarios/UX-0739-the-max-jobs-advice-is-not-priced-nothing-says-what-the-build-drops-to.md)
- [UX-809](docs/backlog/scenarios/UX-0809-the-price-s-two-assumptions-are-on-the-payload-not-in-the-text.md) — [the price's two assumptions are on the payload, not in the text](docs/backlog/scenarios/UX-0809-the-price-s-two-assumptions-are-on-the-payload-not-in-the-text.md)

**capture**

- [UX-594](docs/backlog/scenarios/UX-0594-a-capture-cannot-say-when-the-build-was-requested.md) — [a capture cannot say when the build was requested](docs/backlog/scenarios/UX-0594-a-capture-cannot-say-when-the-build-was-requested.md)
- [UX-612](docs/backlog/scenarios/UX-0612-the-start-clock-has-no-provenance.md) — [the start clock has no provenance](docs/backlog/scenarios/UX-0612-the-start-clock-has-no-provenance.md)
- [UX-675](docs/backlog/scenarios/UX-0675-the-host-series-has-memory-and-no-cores.md) — [the host series has memory and no cores](docs/backlog/scenarios/UX-0675-the-host-series-has-memory-and-no-cores.md)
- [UX-726](docs/backlog/scenarios/UX-0726-no-flag-omits-plane-2-and-the-empty-one-says-nothing.md) — [no flag omits Plane 2, and the empty one says nothing](docs/backlog/scenarios/UX-0726-no-flag-omits-plane-2-and-the-empty-one-says-nothing.md)
- [UX-738](docs/backlog/scenarios/UX-0738-a-build-that-could-not-write-reports-as-a-clean-run-and-exit-255.md) — [a build that could not write reports as a clean run and exit 255](docs/backlog/scenarios/UX-0738-a-build-that-could-not-write-reports-as-a-clean-run-and-exit-255.md)
- [UX-805](docs/backlog/scenarios/UX-0805-the-doctor-s-chain-probe-drops-the-user-s-cache-config-with-its-home.md) — [the doctor's chain probe drops the user's cache config with its HOME](docs/backlog/scenarios/UX-0805-the-doctor-s-chain-probe-drops-the-user-s-cache-config-with-its-home.md)
- [UX-679](docs/backlog/scenarios/UX-0679-a-jobserver-every-sandbox-joins-the-prototype-bga-can-run.md) — [a jobserver every sandbox joins — the prototype bga can run](docs/backlog/scenarios/UX-0679-a-jobserver-every-sandbox-joins-the-prototype-bga-can-run.md)

**viewer**

- [UX-545](docs/backlog/scenarios/UX-0545-a-refused-timeline-says-the-wrong-thing.md) — [a refused timeline tells the reader the snapshot has no build log](docs/backlog/scenarios/UX-0545-a-refused-timeline-says-the-wrong-thing.md)
- [UX-555](docs/backlog/scenarios/UX-0555-with-trace-false-blames-a-missing-plane-2.md) — [`--no-trace` tells a two-plane run it kept no Plane 2 log](docs/backlog/scenarios/UX-0555-with-trace-false-blames-a-missing-plane-2.md)
- [UX-559](docs/backlog/scenarios/UX-0559-serve-leaks-a-scratch-directory-per-run.md) — [`bga view --serve` leaks a scratch directory per served run](docs/backlog/scenarios/UX-0559-serve-leaks-a-scratch-directory-per-run.md)
- [UX-640](docs/backlog/scenarios/UX-0640-the-rail-names-the-key-the-heading-asks-the-question.md) — [the rail names the key, the heading asks the question](docs/backlog/scenarios/UX-0640-the-rail-names-the-key-the-heading-asks-the-question.md)
- [UX-642](docs/backlog/scenarios/UX-0642-a-structured-fold-forgets-it-was-open.md) — [a structured fold forgets it was open](docs/backlog/scenarios/UX-0642-a-structured-fold-forgets-it-was-open.md)
- [UX-638](docs/backlog/scenarios/UX-0638-table-focus-destroys-the-reading-position.md) — [table focus destroys the reading position](docs/backlog/scenarios/UX-0638-table-focus-destroys-the-reading-position.md)
- [UX-639](docs/backlog/scenarios/UX-0639-the-rail-is-dead-while-a-table-is-focused.md) — [the rail is dead while a table is focused](docs/backlog/scenarios/UX-0639-the-rail-is-dead-while-a-table-is-focused.md)
- [UX-648](docs/backlog/scenarios/UX-0648-the-jump-box-names-sections-the-old-way.md) — [the jump box names sections the old way](docs/backlog/scenarios/UX-0648-the-jump-box-names-sections-the-old-way.md)
- [UX-643](docs/backlog/scenarios/UX-0643-a-reader-role-that-demotes-rather-than-hides.md) — [a reader role that demotes rather than hides](docs/backlog/scenarios/UX-0643-a-reader-role-that-demotes-rather-than-hides.md)
- [UX-647](docs/backlog/scenarios/UX-0647-a-rail-click-never-reaches-the-view-state-writer.md) — [a rail click never reaches the view-state writer](docs/backlog/scenarios/UX-0647-a-rail-click-never-reaches-the-view-state-writer.md)
- [UX-646](docs/backlog/scenarios/UX-0646-the-fragment-is-one-event-behind-the-fold.md) — [the fragment is one event behind the fold](docs/backlog/scenarios/UX-0646-the-fragment-is-one-event-behind-the-fold.md)
- [UX-650](docs/backlog/scenarios/UX-0650-nine-page-built-sections-declare-no-reader.md) — [nine page-built sections declare no reader](docs/backlog/scenarios/UX-0650-nine-page-built-sections-declare-no-reader.md)
- [UX-654](docs/backlog/scenarios/UX-0654-the-vocabulary-module-still-says-nine-hints.md) — [the vocabulary module still says nine hints](docs/backlog/scenarios/UX-0654-the-vocabulary-module-still-says-nine-hints.md)
- [UX-672](docs/backlog/scenarios/UX-0672-a-blocked-pop-up-s-refusal-never-renders.md) — [a blocked pop-up's refusal never renders](docs/backlog/scenarios/UX-0672-a-blocked-pop-up-s-refusal-never-renders.md)
- [UX-673](docs/backlog/scenarios/UX-0673-sixteen-tables-offer-a-top-10-they-cannot-fill.md) — [sixteen tables offer a Top 10 they cannot fill](docs/backlog/scenarios/UX-0673-sixteen-tables-offer-a-top-10-they-cannot-fill.md)
- [UX-669](docs/backlog/scenarios/UX-0669-a-runbook-is-a-shape-the-next-steps-rendered-once-as-steps.md) — [a runbook is a shape — the next steps rendered once, as steps](docs/backlog/scenarios/UX-0669-a-runbook-is-a-shape-the-next-steps-rendered-once-as-steps.md)
- [UX-670](docs/backlog/scenarios/UX-0670-the-first-rail-click-into-a-folded-chapter-lands-687-px-above-its-sect.md) — [the first rail click into a folded chapter lands 687 px above its section](docs/backlog/scenarios/UX-0670-the-first-rail-click-into-a-folded-chapter-lands-687-px-above-its-sect.md)
- [UX-721](docs/backlog/scenarios/UX-0721-an-aliased-import-is-silently-dropped-by-the-export.md) — [an aliased import is silently dropped by the export](docs/backlog/scenarios/UX-0721-an-aliased-import-is-silently-dropped-by-the-export.md)
- [UX-722](docs/backlog/scenarios/UX-0722-a-rail-target-inside-a-scrolling-table-lands-under-the-header.md) — [a rail target inside a scrolling table lands under the header](docs/backlog/scenarios/UX-0722-a-rail-target-inside-a-scrolling-table-lands-under-the-header.md)
- [UX-729](docs/backlog/scenarios/UX-0729-two-modules-declare-one-name-and-the-satellite-bundle-would-take-both.md) — [two modules declare one name, and the satellite bundle would take both](docs/backlog/scenarios/UX-0729-two-modules-declare-one-name-and-the-satellite-bundle-would-take-both.md)
- [UX-717](docs/backlog/scenarios/UX-0717-the-host-series-is-on-the-trace-and-in-no-question.md) — [the host series is on the trace and in no question](docs/backlog/scenarios/UX-0717-the-host-series-is-on-the-trace-and-in-no-question.md)
- [UX-667](docs/backlog/scenarios/UX-0667-the-rail-is-a-source-list-chapters-disclose-and-the-mark-stays-in-view.md) — [the rail is a source list — chapters disclose, and the mark stays in view](docs/backlog/scenarios/UX-0667-the-rail-is-a-source-list-chapters-disclose-and-the-mark-stays-in-view.md)
- [UX-699](docs/backlog/scenarios/UX-0699-the-viewer-linted-as-one-module-graph.md) — [the viewer linted as one module graph](docs/backlog/scenarios/UX-0699-the-viewer-linted-as-one-module-graph.md)
- [UX-674](docs/backlog/scenarios/UX-0674-eighteen-font-sizes-an-h3-larger-than-its-h2-and-130-character-lines.md) — [eighteen font sizes, an h3 larger than its h2, and 130-character lines](docs/backlog/scenarios/UX-0674-eighteen-font-sizes-an-h3-larger-than-its-h2-and-130-character-lines.md)
- [UX-753](docs/backlog/scenarios/UX-0753-the-flow-axis-is-drawn-by-one-row-and-read-by-none.md) — [the flow axis is drawn by one row and read by none](docs/backlog/scenarios/UX-0753-the-flow-axis-is-drawn-by-one-row-and-read-by-none.md)
- [UX-758](docs/backlog/scenarios/UX-0758-the-edge-mark-test-reads-a-merged-name-and-never-matches.md) — [the edge-mark test reads a merged name and never matches](docs/backlog/scenarios/UX-0758-the-edge-mark-test-reads-a-merged-name-and-never-matches.md)
- [UX-668](docs/backlog/scenarios/UX-0668-a-reader-is-a-shape-not-a-hue-and-the-selector-lives-in-the-header.md) — [a reader is a shape, not a hue — and the selector lives in the header](docs/backlog/scenarios/UX-0668-a-reader-is-a-shape-not-a-hue-and-the-selector-lives-in-the-header.md)
- [UX-671](docs/backlog/scenarios/UX-0671-the-rail-acts-on-the-view-and-the-url-does-not-follow.md) — [the rail acts on the view, and the URL does not follow](docs/backlog/scenarios/UX-0671-the-rail-acts-on-the-view-and-the-url-does-not-follow.md)
- [UX-800](docs/backlog/scenarios/UX-0800-the-rail-landing-counts-frames-and-the-count-moved-with-the-header.md) — [the rail landing counts frames, and the count moved with the header](docs/backlog/scenarios/UX-0800-the-rail-landing-counts-frames-and-the-count-moved-with-the-header.md)

**store**

- [UX-577](docs/backlog/scenarios/UX-0577-the-committed-example-s-own-next-step-refuses.md) — [the committed example's own next step refuses](docs/backlog/scenarios/UX-0577-the-committed-example-s-own-next-step-refuses.md)
- [UX-595](docs/backlog/scenarios/UX-0595-the-capacity-model-has-a-fact-base-and-no-model.md) — [the capacity model has a fact base and no model](docs/backlog/scenarios/UX-0595-the-capacity-model-has-a-fact-base-and-no-model.md)

**guards**

- [UX-544](docs/backlog/scenarios/UX-0544-the-node-census-has-a-hole.md) — [the hand-built *node* census has a hole the document census does not](docs/backlog/scenarios/UX-0544-the-node-census-has-a-hole.md)
- [UX-547](docs/backlog/scenarios/UX-0547-the-fixture-differ-cannot-see-key-order.md) — [the fixture differ compares parsed JSON, so key order drifts unseen](docs/backlog/scenarios/UX-0547-the-fixture-differ-cannot-see-key-order.md)
- [UX-554](docs/backlog/scenarios/UX-0554-a-failed-suite-takes-its-junit-with-it.md) — [a failed CI suite takes the record of what failed with it](docs/backlog/scenarios/UX-0554-a-failed-suite-takes-its-junit-with-it.md)
- [UX-543](docs/backlog/scenarios/UX-0543-a-second-ranking-clause-under-contention.md) — [a second clause of the answer key ranks under contention](docs/backlog/scenarios/UX-0543-a-second-ranking-clause-under-contention.md)
- [UX-546](docs/backlog/scenarios/UX-0546-the-fetch-guard-is-flaky-under-load.md) — [the fetch-counting handoff guard is flaky under the full suite](docs/backlog/scenarios/UX-0546-the-fetch-guard-is-flaky-under-load.md)
- [UX-557](docs/backlog/scenarios/UX-0557-the-cause-filter-admits-the-whole-suite.md) — [the drift gate's cause filter admits all 424 files](docs/backlog/scenarios/UX-0557-the-cause-filter-admits-the-whole-suite.md)
- [UX-558](docs/backlog/scenarios/UX-0558-the-failure-name-is-3800-lines-from-the-end.md) — [the failure's name is 3,800 lines from the end of the 3.11 job](docs/backlog/scenarios/UX-0558-the-failure-name-is-3800-lines-from-the-end.md)
- [UX-560](docs/backlog/scenarios/UX-0560-a-worktree-track-starts-from-origin-main.md) — [a worktree track starts from `origin/main`, whatever base its brief names](docs/backlog/scenarios/UX-0560-a-worktree-track-starts-from-origin-main.md)
- [UX-561](docs/backlog/scenarios/UX-0561-a-track-cannot-pass-its-own-commit-hook.md) — [a track that closes an item cannot pass its own pre-commit selector](docs/backlog/scenarios/UX-0561-a-track-cannot-pass-its-own-commit-hook.md)
- [UX-562](docs/backlog/scenarios/UX-0562-the-empty-backlog-reds-its-own-topic-guard.md) — [the guard that reds when the backlog it reads reaches zero open rows](docs/backlog/scenarios/UX-0562-the-empty-backlog-reds-its-own-topic-guard.md)
- [UX-586](docs/backlog/scenarios/UX-0586-the-premise-detector-reads-a-proxy.md) — [the premise detector reads a proxy](docs/backlog/scenarios/UX-0586-the-premise-detector-reads-a-proxy.md)
- [UX-587](docs/backlog/scenarios/UX-0587-the-reference-goes-stale-as-the-backlog-it-walks-grows.md) — [a guard whose cost is the backlog's size drifts past a reference `--adopt` cannot refresh](docs/backlog/scenarios/UX-0587-the-reference-goes-stale-as-the-backlog-it-walks-grows.md)
- [UX-579](docs/backlog/scenarios/UX-0579-the-docs-guard-reads-command-words-not-commands.md) — [the docs guard reads command words, not commands](docs/backlog/scenarios/UX-0579-the-docs-guard-reads-command-words-not-commands.md)
- [UX-588](docs/backlog/scenarios/UX-0588-the-python-floor-is-in-the-matrix-and-in-no-guard.md) — [the Python floor is in the CI matrix and in no guard](docs/backlog/scenarios/UX-0588-the-python-floor-is-in-the-matrix-and-in-no-guard.md)
- [UX-573](docs/backlog/scenarios/UX-0573-the-context-map-cannot-see-below-tools.md) — [the context map cannot see below `tools/`](docs/backlog/scenarios/UX-0573-the-context-map-cannot-see-below-tools.md)
- [UX-592](docs/backlog/scenarios/UX-0592-two-rail-harnesses-press-before-the-mark-they-depend-on.md) — [two rail harnesses press before the mark they depend on](docs/backlog/scenarios/UX-0592-two-rail-harnesses-press-before-the-mark-they-depend-on.md)
- [UX-585](docs/backlog/scenarios/UX-0585-the-card-s-guard-column-is-counted-not-read.md) — [the card's guard column is counted, not read](docs/backlog/scenarios/UX-0585-the-card-s-guard-column-is-counted-not-read.md)
- [UX-567](docs/backlog/scenarios/UX-0567-two-invariants-have-no-guard-and-one-has-no-code.md) — [two invariants have no guard, and one has no code](docs/backlog/scenarios/UX-0567-two-invariants-have-no-guard-and-one-has-no-code.md)
- [UX-568](docs/backlog/scenarios/UX-0568-the-spec-has-no-index-of-which-part-a-guard-holds.md) — [the spec has no index of which Part a guard holds](docs/backlog/scenarios/UX-0568-the-spec-has-no-index-of-which-part-a-guard-holds.md)
- [UX-589](docs/backlog/scenarios/UX-0589-the-namer-reads-a-junit-the-run-did-not-write.md) — [the failure namer reads a junit the run did not write](docs/backlog/scenarios/UX-0589-the-namer-reads-a-junit-the-run-did-not-write.md)
- [UX-605](docs/backlog/scenarios/UX-0605-the-touching-map-adopted-a-selection-that-is-everything.md) — [the touching map adopted a selection that is everything](docs/backlog/scenarios/UX-0605-the-touching-map-adopted-a-selection-that-is-everything.md)
- [UX-599](docs/backlog/scenarios/UX-0599-a-guard-pins-a-contract-version-by-typing-it.md) — [a guard pins a contract version by typing it](docs/backlog/scenarios/UX-0599-a-guard-pins-a-contract-version-by-typing-it.md)
- [UX-600](docs/backlog/scenarios/UX-0600-the-rules-card-has-one-guard-it-cannot-mark.md) — [the rules card has one guard it cannot mark](docs/backlog/scenarios/UX-0600-the-rules-card-has-one-guard-it-cannot-mark.md)
- [UX-590](docs/backlog/scenarios/UX-0590-the-context-map-s-non-path-claims-are-unguarded.md) — [the context map's non-path claims are unguarded](docs/backlog/scenarios/UX-0590-the-context-map-s-non-path-claims-are-unguarded.md)
- [UX-606](docs/backlog/scenarios/UX-0606-the-selectors-bound-is-measured-on-one-module.md) — [the selector's bound is measured on one module](docs/backlog/scenarios/UX-0606-the-selectors-bound-is-measured-on-one-module.md)
- [UX-609](docs/backlog/scenarios/UX-0609-the-invariants-docstring-lists-five-of-six-gates.md) — [the invariants docstring lists five of six gates](docs/backlog/scenarios/UX-0609-the-invariants-docstring-lists-five-of-six-gates.md)
- [UX-604](docs/backlog/scenarios/UX-0604-the-verification-log-clause-reads-the-entry-below.md) — [the verification-log clause reads the entry below it](docs/backlog/scenarios/UX-0604-the-verification-log-clause-reads-the-entry-below.md)
- [UX-618](docs/backlog/scenarios/UX-0618-the-step-that-fails-most-writes-no-record.md) — [the step that fails most writes no record](docs/backlog/scenarios/UX-0618-the-step-that-fails-most-writes-no-record.md)
- [UX-620](docs/backlog/scenarios/UX-0620-a-derived-count-re-dates-the-document-it-grounds.md) — [a derived count re-dates the document it grounds](docs/backlog/scenarios/UX-0620-a-derived-count-re-dates-the-document-it-grounds.md)
- [UX-619](docs/backlog/scenarios/UX-0619-four-small-tier-failures-nobody-can-name.md) — [four small-tier failures nobody can name](docs/backlog/scenarios/UX-0619-four-small-tier-failures-nobody-can-name.md)
- [UX-617](docs/backlog/scenarios/UX-0617-the-derived-count-cannot-see-an-unstaged-row.md) — [the derived count cannot see an unstaged row](docs/backlog/scenarios/UX-0617-the-derived-count-cannot-see-an-unstaged-row.md)
- [UX-614](docs/backlog/scenarios/UX-0614-a-track-starts-on-the-default-branch.md) — [a track starts on the default branch, not the round's](docs/backlog/scenarios/UX-0614-a-track-starts-on-the-default-branch.md)
- [UX-615](docs/backlog/scenarios/UX-0615-the-scratchpad-is-shared-between-tracks.md) — [the scratchpad is shared between tracks](docs/backlog/scenarios/UX-0615-the-scratchpad-is-shared-between-tracks.md)
- [UX-621](docs/backlog/scenarios/UX-0621-a-drift-gate-red-nobody-can-read.md) — [a drift-gate red nobody can read](docs/backlog/scenarios/UX-0621-a-drift-gate-red-nobody-can-read.md)
- [UX-624](docs/backlog/scenarios/UX-0624-the-cap-dropped-a-guard-that-was-not-noise.md) — [the cap dropped a guard that was not noise](docs/backlog/scenarios/UX-0624-the-cap-dropped-a-guard-that-was-not-noise.md)
- [UX-623](docs/backlog/scenarios/UX-0623-a-track-cannot-read-the-tree-it-was-copied-from.md) — [a track cannot read the tree it was copied from](docs/backlog/scenarios/UX-0623-a-track-cannot-read-the-tree-it-was-copied-from.md)
- [UX-626](docs/backlog/scenarios/UX-0626-a-brief-names-a-commit-nobody-resolved.md) — [a brief names a commit nobody resolved](docs/backlog/scenarios/UX-0626-a-brief-names-a-commit-nobody-resolved.md)
- [UX-625](docs/backlog/scenarios/UX-0625-reverting-a-mutation-can-discard-the-work.md) — [reverting a mutation can discard the work](docs/backlog/scenarios/UX-0625-reverting-a-mutation-can-discard-the-work.md)
- [UX-622](docs/backlog/scenarios/UX-0622-the-derived-count-and-its-guard-read-two-populations.md) — [the derived count and its guard read two populations](docs/backlog/scenarios/UX-0622-the-derived-count-and-its-guard-read-two-populations.md)
- [UX-627](docs/backlog/scenarios/UX-0627-closing-a-row-writes-done-open.md) — [closing a row writes `🟢 Done Open`](docs/backlog/scenarios/UX-0627-closing-a-row-writes-done-open.md)
- [UX-644](docs/backlog/scenarios/UX-0644-main-is-red-a-map-entry-under-the-cap-widened-a-module.md) — [main is red — a map entry under the cap widened a module](docs/backlog/scenarios/UX-0644-main-is-red-a-map-entry-under-the-cap-widened-a-module.md)
- [UX-649](docs/backlog/scenarios/UX-0649-the-spread-bound-was-set-on-one-machine.md) — [the spread bound was set on one machine](docs/backlog/scenarios/UX-0649-the-spread-bound-was-set-on-one-machine.md)
- [UX-645](docs/backlog/scenarios/UX-0645-the-census-floor-spends-half-the-width-bound.md) — [the census floor spends half the width bound](docs/backlog/scenarios/UX-0645-the-census-floor-spends-half-the-width-bound.md)
- [UX-656](docs/backlog/scenarios/UX-0656-main-is-red-a-closed-outcome-is-eight-lines-over-the-cap.md) — [main is red: a closed outcome is eight lines over the cap](docs/backlog/scenarios/UX-0656-main-is-red-a-closed-outcome-is-eight-lines-over-the-cap.md)
- [UX-657](docs/backlog/scenarios/UX-0657-the-priority-column-has-no-guard.md) — [the priority column has no guard](docs/backlog/scenarios/UX-0657-the-priority-column-has-no-guard.md)
- [UX-658](docs/backlog/scenarios/UX-0658-a-ninth-topic-exists-that-no-open-row-may-carry.md) — [a ninth topic exists that no open row may carry](docs/backlog/scenarios/UX-0658-a-ninth-topic-exists-that-no-open-row-may-carry.md)
- [UX-704](docs/backlog/scenarios/UX-0704-check-lists-the-backlog-once-per-row.md) — [`--check` lists the backlog once per row](docs/backlog/scenarios/UX-0704-check-lists-the-backlog-once-per-row.md)
- [UX-706](docs/backlog/scenarios/UX-0706-a-task-s-shape-is-derived-from-its-text-and-names-the-model-that-runs-it.md) — [a task's shape is derived from its text, and names the model that runs it](docs/backlog/scenarios/UX-0706-a-task-s-shape-is-derived-from-its-text-and-names-the-model-that-runs-it.md)
- [UX-693](docs/backlog/scenarios/UX-0693-the-lint-rule-set-widened-by-layer-in-one-auto-fix-commit-with-the-too.md) — [the lint rule set widened by layer, in one auto-fix commit, with the tools pinned](docs/backlog/scenarios/UX-0693-the-lint-rule-set-widened-by-layer-in-one-auto-fix-commit-with-the-too.md)
- [UX-700](docs/backlog/scenarios/UX-0700-the-symbol-index-and-codeql-declined-for-navigation.md) — [the symbol index — and CodeQL declined for navigation](docs/backlog/scenarios/UX-0700-the-symbol-index-and-codeql-declined-for-navigation.md)
- [UX-707](docs/backlog/scenarios/UX-0707-the-orchestrator-s-rebuilds-are-counted-and-priced-per-session.md) — [the orchestrator's rebuilds are counted and priced, per session](docs/backlog/scenarios/UX-0707-the-orchestrator-s-rebuilds-are-counted-and-priced-per-session.md)
- [UX-709](docs/backlog/scenarios/UX-0709-close-a-batch-of-ids-in-one-move.md) — [close a batch of ids in one `--move`](docs/backlog/scenarios/UX-0709-close-a-batch-of-ids-in-one-move.md)
- [UX-694](docs/backlog/scenarios/UX-0694-a-finding-baseline-and-a-size-ledger-for-what-has-no-identity.md) — [a finding baseline, and a size ledger for what has no identity](docs/backlog/scenarios/UX-0694-a-finding-baseline-and-a-size-ledger-for-what-has-no-identity.md)
- [UX-662](docs/backlog/scenarios/UX-0662-the-adopted-map-made-the-selector-guard-a-hundred-times-dearer.md) — [the adopted touching map made the selector guard a hundred times dearer](docs/backlog/scenarios/UX-0662-the-adopted-map-made-the-selector-guard-a-hundred-times-dearer.md)
- [UX-661](docs/backlog/scenarios/UX-0661-the-fourth-copy-of-the-topic-set-orders-a-release.md) — [the second copy of the topic set orders a release body](docs/backlog/scenarios/UX-0661-the-fourth-copy-of-the-topic-set-orders-a-release.md)
- [UX-687](docs/backlog/scenarios/UX-0687-the-impact-set-is-derived-by-one-tool-not-five-greps.md) — [the impact set is derived by one tool, not five greps](docs/backlog/scenarios/UX-0687-the-impact-set-is-derived-by-one-tool-not-five-greps.md)
- [UX-718](docs/backlog/scenarios/UX-0718-the-census-omits-the-guard-its-own-docstring-names.md) — [the census omits the guard its own docstring names](docs/backlog/scenarios/UX-0718-the-census-omits-the-guard-its-own-docstring-names.md)
- [UX-665](docs/backlog/scenarios/UX-0665-the-page-s-census-is-a-tool-so-a-walk-reads-it-instead-of-driving-it.md) — [the page's census is a tool, so a walk reads it instead of driving it](docs/backlog/scenarios/UX-0665-the-page-s-census-is-a-tool-so-a-walk-reads-it-instead-of-driving-it.md)
- [UX-685](docs/backlog/scenarios/UX-0685-exploration-is-a-seeded-scenario-and-every-finding-grows-the-answer-ke.md) — [exploration is a seeded scenario, and every finding grows the answer key](docs/backlog/scenarios/UX-0685-exploration-is-a-seeded-scenario-and-every-finding-grows-the-answer-ke.md)
- [UX-723](docs/backlog/scenarios/UX-0723-the-scenario-recipe-prints-commands-that-do-not-run.md) — [the scenario recipe prints commands that do not run](docs/backlog/scenarios/UX-0723-the-scenario-recipe-prints-commands-that-do-not-run.md)
- [UX-727](docs/backlog/scenarios/UX-0727-a-design-review-report-has-no-shape-a-guard-can-read.md) — [a design review report has no shape a guard can read](docs/backlog/scenarios/UX-0727-a-design-review-report-has-no-shape-a-guard-can-read.md)
- [UX-732](docs/backlog/scenarios/UX-0732-the-verification-logs-anchor-cannot-survive-a-merge.md) — [the verification log's anchor cannot survive a merge](docs/backlog/scenarios/UX-0732-the-verification-logs-anchor-cannot-survive-a-merge.md)
- [UX-731](docs/backlog/scenarios/UX-0731-a-ratio-guard-with-a-two-millisecond-denominator.md) — [a ratio guard with a two-millisecond denominator](docs/backlog/scenarios/UX-0731-a-ratio-guard-with-a-two-millisecond-denominator.md)
- [UX-736](docs/backlog/scenarios/UX-0736-the-architectures-status-table-is-a-third-copy-of-a-guarded-fact.md) — [the architecture's status table is a third copy of a guarded fact](docs/backlog/scenarios/UX-0736-the-architectures-status-table-is-a-third-copy-of-a-guarded-fact.md)
- [UX-730](docs/backlog/scenarios/UX-0730-a-derived-figure-over-the-whole-test-tree-has-no-refresh-route.md) — [a derived figure over the whole test tree has no refresh route](docs/backlog/scenarios/UX-0730-a-derived-figure-over-the-whole-test-tree-has-no-refresh-route.md)
- [UX-728](docs/backlog/scenarios/UX-0728-a-tracks-repro-runs-the-sessions-checkout-not-its-worktree.md) — [a track's repro runs the session's checkout, not its worktree](docs/backlog/scenarios/UX-0728-a-tracks-repro-runs-the-sessions-checkout-not-its-worktree.md)
- [UX-737](docs/backlog/scenarios/UX-0737-the-census-detectors-other-half-thirteen-guards-a-subprocess-hides.md) — [the census detector's other half — thirteen guards a subprocess hides](docs/backlog/scenarios/UX-0737-the-census-detectors-other-half-thirteen-guards-a-subprocess-hides.md)
- [UX-716](docs/backlog/scenarios/UX-0716-a-guard-whose-cost-is-its-population-has-no-refresh-route.md) — [a guard whose cost is its population has no refresh route](docs/backlog/scenarios/UX-0716-a-guard-whose-cost-is-its-population-has-no-refresh-route.md)
- [UX-692](docs/backlog/scenarios/UX-0692-the-invariants-hold-for-any-shape-a-seeded-sweep-over-generated-projec.md) — [the invariants hold for any shape — a seeded sweep over generated projects](docs/backlog/scenarios/UX-0692-the-invariants-hold-for-any-shape-a-seeded-sweep-over-generated-projec.md)
- [UX-691](docs/backlog/scenarios/UX-0691-a-flake-ledger-so-an-excursion-is-counted-before-it-is-a-flake.md) — [a flake ledger, so an excursion is counted before it is a flake](docs/backlog/scenarios/UX-0691-a-flake-ledger-so-an-excursion-is-counted-before-it-is-a-flake.md)
- [UX-702](docs/backlog/scenarios/UX-0702-a-performance-ratchet-at-the-gate.md) — [a performance ratchet at the gate](docs/backlog/scenarios/UX-0702-a-performance-ratchet-at-the-gate.md)
- [UX-712](docs/backlog/scenarios/UX-0712-the-size-ledger-for-what-has-no-finding-identity.md) — [the size ledger, for what has no finding identity](docs/backlog/scenarios/UX-0712-the-size-ledger-for-what-has-no-finding-identity.md)
- [UX-703](docs/backlog/scenarios/UX-0703-a-mutation-run-on-the-touched-modules-weekly.md) — [a mutation run on the touched modules, weekly](docs/backlog/scenarios/UX-0703-a-mutation-run-on-the-touched-modules-weekly.md)
- [UX-743](docs/backlog/scenarios/UX-0743-the-small-tier-backstop-was-sized-against-a-suite-half-this-size.md) — [the small tier's backstop was sized against a suite half this size](docs/backlog/scenarios/UX-0743-the-small-tier-backstop-was-sized-against-a-suite-half-this-size.md)
- [UX-696](docs/backlog/scenarios/UX-0696-the-register-s-unguarded-rows-no-round-in-code-a-dated-count-the-commi.md) — [the register's unguarded rows — no round in code, a dated count, the commit body](docs/backlog/scenarios/UX-0696-the-register-s-unguarded-rows-no-round-in-code-a-dated-count-the-commi.md)
- [UX-742](docs/backlog/scenarios/UX-0742-the-viewer-s-dead-exports-need-a-detector-eslint-cannot-be.md) — [the viewer's dead exports need a detector eslint cannot be](docs/backlog/scenarios/UX-0742-the-viewer-s-dead-exports-need-a-detector-eslint-cannot-be.md)
- [UX-705](docs/backlog/scenarios/UX-0705-the-burn-down-runs-on-the-reporters-model-a-batch-a-commit-never-a-supp.md) — [the burn-down runs on the reporters' model — a batch a commit, never a suppression](docs/backlog/scenarios/UX-0705-the-burn-down-runs-on-the-reporters-model-a-batch-a-commit-never-a-supp.md)
- [UX-747](docs/backlog/scenarios/UX-0747-the-derive-skill-s-own-example-crashes-the-tool-it-documents.md) — [the `derive` skill's own example crashes the tool it documents](docs/backlog/scenarios/UX-0747-the-derive-skill-s-own-example-crashes-the-tool-it-documents.md)
- [UX-745](docs/backlog/scenarios/UX-0745-a-track-can-authorise-its-own-baseline-growth-and-did.md) — [a track can authorise its own baseline growth, and did](docs/backlog/scenarios/UX-0745-a-track-can-authorise-its-own-baseline-growth-and-did.md)
- [UX-748](docs/backlog/scenarios/UX-0748-three-guards-read-a-narrower-population-than-the-sentence-they-check.md) — [three guards read a narrower population than the sentence they check](docs/backlog/scenarios/UX-0748-three-guards-read-a-narrower-population-than-the-sentence-they-check.md)
- [UX-752](docs/backlog/scenarios/UX-0752-the-guard-s-spelling-table-ran-out-at-forty.md) — [the guard's spelling table ran out at forty](docs/backlog/scenarios/UX-0752-the-guard-s-spelling-table-ran-out-at-forty.md)
- [UX-754](docs/backlog/scenarios/UX-0754-the-derived-figure-exclusion-cannot-read-a-merge.md) — [the derived-figure exclusion cannot read a merge](docs/backlog/scenarios/UX-0754-the-derived-figure-exclusion-cannot-read-a-merge.md)
- [UX-750](docs/backlog/scenarios/UX-0750-the-map-s-one-count-is-the-one-noun-the-guard-does-not-list.md) — [the map's one count is the one noun the guard does not list](docs/backlog/scenarios/UX-0750-the-map-s-one-count-is-the-one-noun-the-guard-does-not-list.md)
- [UX-751](docs/backlog/scenarios/UX-0751-the-landed-clause-reads-endpoints-where-the-open-clause-reads-the-range.md) — [the landed clause reads endpoints where the open clause reads the range](docs/backlog/scenarios/UX-0751-the-landed-clause-reads-endpoints-where-the-open-clause-reads-the-range.md)
- [UX-755](docs/backlog/scenarios/UX-0755-the-gate-and-ci-disagree-and-the-gate-is-the-one-that-is-wrong.md) — [the gate and CI disagree, and the gate is the one that is wrong](docs/backlog/scenarios/UX-0755-the-gate-and-ci-disagree-and-the-gate-is-the-one-that-is-wrong.md)
- [UX-762](docs/backlog/scenarios/UX-0762-the-gate-binds-to-a-branch-not-to-the-commit-that-is-pushed.md) — [the gate binds to a branch, not to the commit that is pushed](docs/backlog/scenarios/UX-0762-the-gate-binds-to-a-branch-not-to-the-commit-that-is-pushed.md)
- [UX-769](docs/backlog/scenarios/UX-0769-the-count-guard-matches-a-task-id.md) — [the count guard matches a task id, not a count](docs/backlog/scenarios/UX-0769-the-count-guard-matches-a-task-id.md)
- [UX-770](docs/backlog/scenarios/UX-0770-the-cost-row-median-sits-on-a-tie.md) — [the cost row's median sits on a tie, and the population moves under it](docs/backlog/scenarios/UX-0770-the-cost-row-median-sits-on-a-tie.md)
- [UX-768](docs/backlog/scenarios/UX-0768-the-closing-note-is-a-shell-argument-and-its-backticks-run.md) — [the closing note is a shell argument, and its backticks run](docs/backlog/scenarios/UX-0768-the-closing-note-is-a-shell-argument-and-its-backticks-run.md)
- [UX-766](docs/backlog/scenarios/UX-0766-the-forced-baseline-is-loud-only-until-it-is-committed.md) — [the forced baseline is loud only until it is committed](docs/backlog/scenarios/UX-0766-the-forced-baseline-is-loud-only-until-it-is-committed.md)
- [UX-767](docs/backlog/scenarios/UX-0767-the-push-gate-sees-one-channel-and-the-round-used-another.md) — [the push gate sees one channel, and the round used another](docs/backlog/scenarios/UX-0767-the-push-gate-sees-one-channel-and-the-round-used-another.md)
- [UX-759](docs/backlog/scenarios/UX-0759-the-register-s-id-column-loses-a-subset-in-silence.md) — [the register's id column loses a subset in silence](docs/backlog/scenarios/UX-0759-the-register-s-id-column-loses-a-subset-in-silence.md)
- [UX-760](docs/backlog/scenarios/UX-0760-six-more-files-build-against-the-broken-reserve.md) — [six more files build against the broken reserve](docs/backlog/scenarios/UX-0760-six-more-files-build-against-the-broken-reserve.md)
- [UX-776](docs/backlog/scenarios/UX-0776-a-derivation-from-git-history-is-a-property-of-the-clone.md) — [a derivation from git history is a property of the clone](docs/backlog/scenarios/UX-0776-a-derivation-from-git-history-is-a-property-of-the-clone.md)
- [UX-771](docs/backlog/scenarios/UX-0771-two-more-documents-number-sections-and-no-guard-reads-them.md) — [two more documents number sections, and no guard reads them](docs/backlog/scenarios/UX-0771-two-more-documents-number-sections-and-no-guard-reads-them.md)
- [UX-772](docs/backlog/scenarios/UX-0772-the-first-date-in-a-document-is-not-its-dateline.md) — [the first date in a document is not its dateline](docs/backlog/scenarios/UX-0772-the-first-date-in-a-document-is-not-its-dateline.md)
- [UX-773](docs/backlog/scenarios/UX-0773-a-killed-worker-leaks-a-browser-and-its-profile.md) — [a killed worker leaks a browser and its profile](docs/backlog/scenarios/UX-0773-a-killed-worker-leaks-a-browser-and-its-profile.md)
- [UX-781](docs/backlog/scenarios/UX-0781-ci-truncates-the-history-it-just-fetched-in-full.md) — [CI truncates the history it just fetched in full](docs/backlog/scenarios/UX-0781-ci-truncates-the-history-it-just-fetched-in-full.md)
- [UX-783](docs/backlog/scenarios/UX-0783-two-tier-rules-disagree-and-a-sweep-does-not-wait.md) — [two tier rules disagree about one file, and a sweep does not wait for what it killed](docs/backlog/scenarios/UX-0783-two-tier-rules-disagree-and-a-sweep-does-not-wait.md)
- [UX-784](docs/backlog/scenarios/UX-0784-one-fetch-depth-anywhere-satisfied-a-sentence-about-every-job.md) — [one `fetch-depth: 0` anywhere satisfied a sentence about every job](docs/backlog/scenarios/UX-0784-one-fetch-depth-anywhere-satisfied-a-sentence-about-every-job.md)
- [UX-698](docs/backlog/scenarios/UX-0698-the-gate-only-shelf-on-github-code-scanning-a-lockfile-and-audit-depen.md) — [the gate-only shelf on GitHub — code scanning, a lockfile and audit, Dependabot, secret scanning](docs/backlog/scenarios/UX-0698-the-gate-only-shelf-on-github-code-scanning-a-lockfile-and-audit-depen.md)
- [UX-793](docs/backlog/scenarios/UX-0793-a-retrospective-verifier-reads-the-tracks-tip-and-not-the-suite.md) — [a retrospective verifier reads the track's tip, and not the suite](docs/backlog/scenarios/UX-0793-a-retrospective-verifier-reads-the-tracks-tip-and-not-the-suite.md)
- [UX-785](docs/backlog/scenarios/UX-0785-the-flake-census-clears-any-file-a-task-ever-mentioned.md) — [the flake census clears any file a task ever mentioned](docs/backlog/scenarios/UX-0785-the-flake-census-clears-any-file-a-task-ever-mentioned.md)
- [UX-786](docs/backlog/scenarios/UX-0786-the-flake-ledgers-adopt-is-never-run-against-a-non-empty-ledger.md) — [the flake ledger's adopt is never run against a non-empty ledger](docs/backlog/scenarios/UX-0786-the-flake-ledgers-adopt-is-never-run-against-a-non-empty-ledger.md)
- [UX-792](docs/backlog/scenarios/UX-0792-the-perf-carry-key-is-scoped-to-a-branch-by-nothing.md) — [the perf-carry key is scoped to a branch by nothing](docs/backlog/scenarios/UX-0792-the-perf-carry-key-is-scoped-to-a-branch-by-nothing.md)
- [UX-787](docs/backlog/scenarios/UX-0787-the-size-ledger-cannot-record-a-shrink-while-any-cell-grew.md) — [the size ledger cannot record a shrink while any cell grew](docs/backlog/scenarios/UX-0787-the-size-ledger-cannot-record-a-shrink-while-any-cell-grew.md)
- [UX-788](docs/backlog/scenarios/UX-0788-the-size-ledger-trusts-a-broken-pylint.md) — [the size ledger trusts a broken pylint](docs/backlog/scenarios/UX-0788-the-size-ledger-trusts-a-broken-pylint.md)
- [UX-794](docs/backlog/scenarios/UX-0794-the-ledgers-count-word-stopped-at-ninety-nine.md) — [the ledger's count word stopped at ninety-nine](docs/backlog/scenarios/UX-0794-the-ledgers-count-word-stopped-at-ninety-nine.md)
- [UX-697](docs/backlog/scenarios/UX-0697-a-type-error-ratchet-contracts-first.md) — [a type-error ratchet, contracts first](docs/backlog/scenarios/UX-0697-a-type-error-ratchet-contracts-first.md)
- [UX-790](docs/backlog/scenarios/UX-0790-the-mutation-runs-classifier-has-no-fast-guard.md) — [the mutation run's classifier has no fast guard](docs/backlog/scenarios/UX-0790-the-mutation-runs-classifier-has-no-fast-guard.md)
- [UX-764](docs/backlog/scenarios/UX-0764-two-register-caps-are-guarded-and-two-are-honour-system.md) — [two Register caps are guarded and two are honour-system](docs/backlog/scenarios/UX-0764-two-register-caps-are-guarded-and-two-are-honour-system.md)
- [UX-795](docs/backlog/scenarios/UX-0795-the-focus-guard-measures-after-a-fixed-sleep-and-one-runner-was-slower.md) — [the focus guard measures after a fixed sleep, and one runner was slower](docs/backlog/scenarios/UX-0795-the-focus-guard-measures-after-a-fixed-sleep-and-one-runner-was-slower.md)
- [UX-789](docs/backlog/scenarios/UX-0789-a-baseline-entry-carries-a-key-the-tool-never-reads.md) — [a baseline entry carries a key the tool never reads](docs/backlog/scenarios/UX-0789-a-baseline-entry-carries-a-key-the-tool-never-reads.md)
- [UX-775](docs/backlog/scenarios/UX-0775-two-files-still-build-against-the-ambient-home.md) — [two files still build against the ambient HOME](docs/backlog/scenarios/UX-0775-two-files-still-build-against-the-ambient-home.md)
- [UX-741](docs/backlog/scenarios/UX-0741-the-spine-s-ground-truth-reads-wall-clock-and-a-loaded-host-reds-it.md) — [the spine's ground truth reads wall clock, and a loaded host reds it](docs/backlog/scenarios/UX-0741-the-spine-s-ground-truth-reads-wall-clock-and-a-loaded-host-reds-it.md)
- [UX-690](docs/backlog/scenarios/UX-0690-the-suite-has-a-shape-budget-and-a-feature-files-its-test-analysis.md) — [the suite has a shape budget, and a feature files its test analysis](docs/backlog/scenarios/UX-0690-the-suite-has-a-shape-budget-and-a-feature-files-its-test-analysis.md)
- [UX-796](docs/backlog/scenarios/UX-0796-the-host-sampler-claims-more-busy-cores-than-the-host-has-under-load.md) — [the host sampler claims more busy cores than the host has, under load](docs/backlog/scenarios/UX-0796-the-host-sampler-claims-more-busy-cores-than-the-host-has-under-load.md)
- [UX-801](docs/backlog/scenarios/UX-0801-bst-show-writes-the-cas-and-two-files-still-run-it-in-the-ambient-home.md) — [`bst show` writes the CAS, and two files still run it in the ambient HOME](docs/backlog/scenarios/UX-0801-bst-show-writes-the-cas-and-two-files-still-run-it-in-the-ambient-home.md)
- [UX-802](docs/backlog/scenarios/UX-0802-the-baseline-guard-files-spawn-pyright-sixteen-times.md) — [the baseline guard files spawn pyright sixteen times](docs/backlog/scenarios/UX-0802-the-baseline-guard-files-spawn-pyright-sixteen-times.md)
- [UX-803](docs/backlog/scenarios/UX-0803-a-step-change-in-a-file-s-cost-takes-three-main-pushes-to-reach-the-reference.md) — [a step change in a file's cost takes three main pushes to reach the reference](docs/backlog/scenarios/UX-0803-a-step-change-in-a-file-s-cost-takes-three-main-pushes-to-reach-the-reference.md)
- [UX-782](docs/backlog/scenarios/UX-0782-the-register-derives-its-rounds-from-git-log.md) — [the register derives its rounds from `git log`, which is a property of the clone](docs/backlog/scenarios/UX-0782-the-register-derives-its-rounds-from-git-log.md)
- [UX-797](docs/backlog/scenarios/UX-0797-eight-identical-sleeps-spread-past-a-tenth-under-organic-load.md) — [eight identical sleeps spread past a tenth, under organic load](docs/backlog/scenarios/UX-0797-eight-identical-sleeps-spread-past-a-tenth-under-organic-load.md)
- [UX-804](docs/backlog/scenarios/UX-0804-the-diagnostics-performance-guard-is-a-typed-ten-seconds-of-wall-clock.md) — [the diagnostics performance guard is a typed ten seconds of wall clock](docs/backlog/scenarios/UX-0804-the-diagnostics-performance-guard-is-a-typed-ten-seconds-of-wall-clock.md)
- [UX-811](docs/backlog/scenarios/UX-0811-the-commit-body-gate-reads-dependabot-s-generated-bodies.md) — [the commit-body gate reads Dependabot's generated bodies](docs/backlog/scenarios/UX-0811-the-commit-body-gate-reads-dependabot-s-generated-bodies.md)
- [UX-812](docs/backlog/scenarios/UX-0812-the-impact-guard-needs-an-open-analysis-row-to-be-green.md) — [the impact guard needs an open analysis row to be green](docs/backlog/scenarios/UX-0812-the-impact-guard-needs-an-open-analysis-row-to-be-green.md)
- [UX-813](docs/backlog/scenarios/UX-0813-the-history-row-s-count-is-right-because-two-errors-cancel.md) — [the history row's count is right because two errors cancel](docs/backlog/scenarios/UX-0813-the-history-row-s-count-is-right-because-two-errors-cancel.md)

**docs**

- [UX-548](docs/backlog/scenarios/UX-0548-round-80s-viewer-axis-reaches-no-guide.md) — [five mechanisms round 80 shipped, and no guide names one](docs/backlog/scenarios/UX-0548-round-80s-viewer-axis-reaches-no-guide.md)
- [UX-552](docs/backlog/scenarios/UX-0552-the-alias-table-is-two-rows-short.md) — [the CLI guide's alias table is two rows short](docs/backlog/scenarios/UX-0552-the-alias-table-is-two-rows-short.md)
- [UX-549](docs/backlog/scenarios/UX-0549-five-counted-figures-a-reader-reads-as-current.md) — [five counted figures, read as current, wrong](docs/backlog/scenarios/UX-0549-five-counted-figures-a-reader-reads-as-current.md)
- [UX-551](docs/backlog/scenarios/UX-0551-the-loop-is-planned-against-a-suite-that-is-gone.md) — [every session plans its loop against a suite 62% faster than the real one](docs/backlog/scenarios/UX-0551-the-loop-is-planned-against-a-suite-that-is-gone.md)
- [UX-556](docs/backlog/scenarios/UX-0556-the-spec-carries-the-sentence-ux-549-fixed.md) — [the spec still says "the last four are written but not printable"](docs/backlog/scenarios/UX-0556-the-spec-carries-the-sentence-ux-549-fixed.md)
- [UX-566](docs/backlog/scenarios/UX-0566-two-recommended-parts-describe-a-tool-that-was-never-built-that-way.md) — [two "recommended" Parts describe a tool that was never built that way](docs/backlog/scenarios/UX-0566-two-recommended-parts-describe-a-tool-that-was-never-built-that-way.md)
- [UX-576](docs/backlog/scenarios/UX-0576-the-question-count-is-stated-three-ways.md) — [the question count is stated three ways](docs/backlog/scenarios/UX-0576-the-question-count-is-stated-three-ways.md)
- [UX-570](docs/backlog/scenarios/UX-0570-the-capture-workflow-document-describes-a-workflow-that-has-moved-on.md) — [the capture workflow document describes a workflow that has moved on](docs/backlog/scenarios/UX-0570-the-capture-workflow-document-describes-a-workflow-that-has-moved-on.md)
- [UX-572](docs/backlog/scenarios/UX-0572-by-construction-survived-the-construction-it-now-depends-on.md) — ["by construction" survived the construction it now depends on](docs/backlog/scenarios/UX-0572-by-construction-survived-the-construction-it-now-depends-on.md)
- [UX-571](docs/backlog/scenarios/UX-0571-the-ingestion-facts-were-confirmed-on-a-buildstream-this-machine-no-lo.md) — [the ingestion facts were confirmed on a BuildStream this machine no longer has](docs/backlog/scenarios/UX-0571-the-ingestion-facts-were-confirmed-on-a-buildstream-this-machine-no-lo.md)
- [UX-582](docs/backlog/scenarios/UX-0582-the-styleguide-s-ledger-says-seven-sections-have-no-guard.md) — [the styleguide's ledger says seven sections have no guard](docs/backlog/scenarios/UX-0582-the-styleguide-s-ledger-says-seven-sections-have-no-guard.md)
- [UX-583](docs/backlog/scenarios/UX-0583-the-round-history-is-typed-and-three-rounds-are-missing-from-it.md) — [the round history is typed, and three rounds are missing from it](docs/backlog/scenarios/UX-0583-the-round-history-is-typed-and-three-rounds-are-missing-from-it.md)
- [UX-581](docs/backlog/scenarios/UX-0581-a-direction-has-no-status-so-a-tail-goes-silent.md) — [a direction has no status, so a tail goes silent](docs/backlog/scenarios/UX-0581-a-direction-has-no-status-so-a-tail-goes-silent.md)
- [UX-580](docs/backlog/scenarios/UX-0580-the-roles-table-says-nothing-aggregates-across-builds.md) — [the roles table says nothing aggregates across builds](docs/backlog/scenarios/UX-0580-the-roles-table-says-nothing-aggregates-across-builds.md)
- [UX-569](docs/backlog/scenarios/UX-0569-the-architecture-document-s-prose-is-not-what-its-guards-read.md) — [the architecture document's prose is not what its guards read](docs/backlog/scenarios/UX-0569-the-architecture-document-s-prose-is-not-what-its-guards-read.md)
- [UX-578](docs/backlog/scenarios/UX-0578-the-verbatim-blocks-that-are-neither-dated-nor-fresh.md) — [the verbatim blocks that are neither dated nor fresh](docs/backlog/scenarios/UX-0578-the-verbatim-blocks-that-are-neither-dated-nor-fresh.md)
- [UX-584](docs/backlog/scenarios/UX-0584-the-figures-nothing-reads-thirteen-stale-numbers-in-the-process-layer.md) — [the figures nothing reads — thirteen stale numbers in the process layer](docs/backlog/scenarios/UX-0584-the-figures-nothing-reads-thirteen-stale-numbers-in-the-process-layer.md)
- [UX-591](docs/backlog/scenarios/UX-0591-the-architecture-review-log-is-in-no-index.md) — [the architecture review log is in no index](docs/backlog/scenarios/UX-0591-the-architecture-review-log-is-in-no-index.md)
- [UX-603](docs/backlog/scenarios/UX-0603-the-python-floor-reaches-no-reader.md) — [the Python floor reaches no reader](docs/backlog/scenarios/UX-0603-the-python-floor-reaches-no-reader.md)
- [UX-607](docs/backlog/scenarios/UX-0607-a-paragraph-in-the-guide-is-a-two-file-change.md) — [a paragraph in the guide is a two-file change](docs/backlog/scenarios/UX-0607-a-paragraph-in-the-guide-is-a-two-file-change.md)
- [UX-608](docs/backlog/scenarios/UX-0608-fifteen-commands-the-context-map-never-names.md) — [fifteen commands the context map never names](docs/backlog/scenarios/UX-0608-fifteen-commands-the-context-map-never-names.md)
- [UX-601](docs/backlog/scenarios/UX-0601-two-guard-ledgers-of-the-same-kind.md) — [two guard ledgers of the same kind, two mechanisms](docs/backlog/scenarios/UX-0601-two-guard-ledgers-of-the-same-kind.md)
- [UX-616](docs/backlog/scenarios/UX-0616-the-coupling-runs-the-other-way-too.md) — [the coupling runs the other way too](docs/backlog/scenarios/UX-0616-the-coupling-runs-the-other-way-too.md)
- [UX-597](docs/backlog/scenarios/UX-0597-three-release-rows-and-no-tag.md) — [three release rows and no tag](docs/backlog/scenarios/UX-0597-three-release-rows-and-no-tag.md)
- [UX-634](docs/backlog/scenarios/UX-0634-the-tag-is-cut-and-nothing-is-published.md) — [the tag is cut and nothing is published](docs/backlog/scenarios/UX-0634-the-tag-is-cut-and-nothing-is-published.md)
- [UX-633](docs/backlog/scenarios/UX-0633-a-release-tag-names-a-commit-main-cannot-reach.md) — [a release tag names a commit `main` cannot reach](docs/backlog/scenarios/UX-0633-a-release-tag-names-a-commit-main-cannot-reach.md)
- [UX-630](docs/backlog/scenarios/UX-0630-two-environment-variables-no-inventory-sees.md) — [two environment variables no inventory sees](docs/backlog/scenarios/UX-0630-two-environment-variables-no-inventory-sees.md)
- [UX-631](docs/backlog/scenarios/UX-0631-the-context-map-guard-cannot-see-a-package-file.md) — [the context map's guard cannot see a file inside a package](docs/backlog/scenarios/UX-0631-the-context-map-guard-cannot-see-a-package-file.md)
- [UX-632](docs/backlog/scenarios/UX-0632-the-touching-figure-is-the-sample-its-own-round-disproved.md) — [the touching figure is the sample its own round disproved](docs/backlog/scenarios/UX-0632-the-touching-figure-is-the-sample-its-own-round-disproved.md)
- [UX-635](docs/backlog/scenarios/UX-0635-the-inventory-stops-at-one-namespace.md) — [the environment inventory stops at one namespace](docs/backlog/scenarios/UX-0635-the-inventory-stops-at-one-namespace.md)
- [UX-636](docs/backlog/scenarios/UX-0636-eighty-published-keys-no-document-names.md) — [eighty published keys no document names](docs/backlog/scenarios/UX-0636-eighty-published-keys-no-document-names.md)
- [UX-651](docs/backlog/scenarios/UX-0651-the-spec-s-part-32-block-is-two-ids-behind.md) — [the spec's Part 32 block is two ids behind](docs/backlog/scenarios/UX-0651-the-spec-s-part-32-block-is-two-ids-behind.md)
- [UX-652](docs/backlog/scenarios/UX-0652-the-currency-guard-resolves-to-a-day-and-a-day-holds-three-rounds.md) — [the currency guard resolves to a day, and a day holds three rounds](docs/backlog/scenarios/UX-0652-the-currency-guard-resolves-to-a-day-and-a-day-holds-three-rounds.md)
- [UX-653](docs/backlog/scenarios/UX-0653-a-contract-bump-rewrites-the-record-of-what-it-superseded.md) — [a contract bump rewrites the record of what it superseded](docs/backlog/scenarios/UX-0653-a-contract-bump-rewrites-the-record-of-what-it-superseded.md)
- [UX-655](docs/backlog/scenarios/UX-0655-a-contract-bump-landed-one-level-below-the-key-population.md) — [a contract bump landed one level below the key population](docs/backlog/scenarios/UX-0655-a-contract-bump-landed-one-level-below-the-key-population.md)
- [UX-663](docs/backlog/scenarios/UX-0663-reading-and-checking-run-on-a-smaller-model-and-the-frontmatter-says-s.md) — [reading and checking run on a smaller model, and the frontmatter says so](docs/backlog/scenarios/UX-0663-reading-and-checking-run-on-a-smaller-model-and-the-frontmatter-says-s.md)
- [UX-664](docs/backlog/scenarios/UX-0664-the-walk-and-the-design-review-are-protocols-not-prompts.md) — [the walk and the design review are protocols, not prompts](docs/backlog/scenarios/UX-0664-the-walk-and-the-design-review-are-protocols-not-prompts.md)
- [UX-710](docs/backlog/scenarios/UX-0710-a-ledger-row-is-derived-from-the-transcript-not-typed.md) — [a ledger row is derived from the transcript, not typed](docs/backlog/scenarios/UX-0710-a-ledger-row-is-derived-from-the-transcript-not-typed.md)
- [UX-660](docs/backlog/scenarios/UX-0660-one-sentence-two-figures-one-guarded.md) — [one sentence, two line numbers, and only one of them is guarded](docs/backlog/scenarios/UX-0660-one-sentence-two-figures-one-guarded.md)
- [UX-711](docs/backlog/scenarios/UX-0711-a-tool-result-longer-than-a-screen-goes-to-a-file.md) — [a tool result longer than a screen goes to a file](docs/backlog/scenarios/UX-0711-a-tool-result-longer-than-a-screen-goes-to-a-file.md)
- [UX-701](docs/backlog/scenarios/UX-0701-the-self-review-skill-the-existing-policy-on-the-diff-on-the-reporters.md) — [the `self-review` skill — the existing policy on the diff, on the reporters' model](docs/backlog/scenarios/UX-0701-the-self-review-skill-the-existing-policy-on-the-diff-on-the-reporters.md)
- [UX-688](docs/backlog/scenarios/UX-0688-every-task-carries-an-area-and-the-area-pages-are-generated.md) — [every task carries an area, and the area pages are generated](docs/backlog/scenarios/UX-0688-every-task-carries-an-area-and-the-area-pages-are-generated.md)
- [UX-686](docs/backlog/scenarios/UX-0686-a-release-waits-for-the-walk-that-read-its-candidate.md) — [a release waits for the walk that read its candidate](docs/backlog/scenarios/UX-0686-a-release-waits-for-the-walk-that-read-its-candidate.md)
- [UX-713](docs/backlog/scenarios/UX-0713-the-skill-that-runs-the-review-is-named-by-neither-document.md) — [the skill that runs the review is named by neither document](docs/backlog/scenarios/UX-0713-the-skill-that-runs-the-review-is-named-by-neither-document.md)
- [UX-714](docs/backlog/scenarios/UX-0714-the-orchestrators-share-is-a-bare-figure-that-has-moved.md) — [the orchestrator's share is a bare figure that has moved](docs/backlog/scenarios/UX-0714-the-orchestrators-share-is-a-bare-figure-that-has-moved.md)
- [UX-715](docs/backlog/scenarios/UX-0715-fifteen-viewer-modules-in-a-passage-with-no-date.md) — [fifteen viewer modules, in a passage with no date](docs/backlog/scenarios/UX-0715-fifteen-viewer-modules-in-a-passage-with-no-date.md)
- [UX-734](docs/backlog/scenarios/UX-0734-three-counted-figures-in-three-documents-and-no-guard-reads-any.md) — [three counted figures in three documents, and no guard reads any](docs/backlog/scenarios/UX-0734-three-counted-figures-in-three-documents-and-no-guard-reads-any.md)
- [UX-735](docs/backlog/scenarios/UX-0735-the-attachment-guides-export-size-measures-a-capture-not-in-the-tree.md) — [the attachment guide's export size measures a capture not in the tree](docs/backlog/scenarios/UX-0735-the-attachment-guides-export-size-measures-a-capture-not-in-the-tree.md)
- [UX-666](docs/backlog/scenarios/UX-0666-a-subagent-s-cost-is-written-down-and-its-friction-with-it.md) — [a subagent's cost is written down, and its friction with it](docs/backlog/scenarios/UX-0666-a-subagent-s-cost-is-written-down-and-its-friction-with-it.md)
- [UX-708](docs/backlog/scenarios/UX-0708-the-first-batch-under-the-pipeline-priced-per-shape.md) — [the first batch under the pipeline, priced per shape](docs/backlog/scenarios/UX-0708-the-first-batch-under-the-pipeline-priced-per-shape.md)
- [UX-746](docs/backlog/scenarios/UX-0746-four-workflows-are-on-no-map-and-the-map-s-guard-cannot-see-them.md) — [four workflows are on no map, and the map's guard cannot see them](docs/backlog/scenarios/UX-0746-four-workflows-are-on-no-map-and-the-map-s-guard-cannot-see-them.md)
- [UX-749](docs/backlog/scenarios/UX-0749-a-citation-that-looks-like-a-path-and-a-count-of-branches-that-moved.md) — [a citation that looks like a path, and a count of branches that moved](docs/backlog/scenarios/UX-0749-a-citation-that-looks-like-a-path-and-a-count-of-branches-that-moved.md)
- [UX-756](docs/backlog/scenarios/UX-0756-the-spread-rule-names-a-new-file-when-an-import-is-enough.md) — [the spread rule names a new file when an import is enough](docs/backlog/scenarios/UX-0756-the-spread-rule-names-a-new-file-when-an-import-is-enough.md)
- [UX-761](docs/backlog/scenarios/UX-0761-the-verifier-is-mandated-in-the-one-document-the-guide-outranks.md) — [the verifier is mandated in the one document the guide outranks](docs/backlog/scenarios/UX-0761-the-verifier-is-mandated-in-the-one-document-the-guide-outranks.md)
- [UX-757](docs/backlog/scenarios/UX-0757-the-four-rounds-the-register-names-have-no-document.md) — [the four rounds the register names have no document](docs/backlog/scenarios/UX-0757-the-four-rounds-the-register-names-have-no-document.md)
- [UX-763](docs/backlog/scenarios/UX-0763-no-document-says-what-closing-a-round-owes.md) — [no document says what closing a round owes](docs/backlog/scenarios/UX-0763-no-document-says-what-closing-a-round-owes.md)
- [UX-765](docs/backlog/scenarios/UX-0765-two-process-cross-references-point-at-numbers-that-are-not-there.md) — [two process cross-references point at numbers that are not there](docs/backlog/scenarios/UX-0765-two-process-cross-references-point-at-numbers-that-are-not-there.md)
- [UX-791](docs/backlog/scenarios/UX-0791-an-orphan-row-in-the-architecture-table-is-invisible.md) — [an orphan row in the architecture table is invisible](docs/backlog/scenarios/UX-0791-an-orphan-row-in-the-architecture-table-is-invisible.md)
- [UX-778](docs/backlog/scenarios/UX-0778-the-docs-index-counts-two-guards-where-four-fire.md) — [the docs index counts two guards where four fire](docs/backlog/scenarios/UX-0778-the-docs-index-counts-two-guards-where-four-fire.md)
- [UX-744](docs/backlog/scenarios/UX-0744-no-register-says-which-rounds-exist-and-four-records-disagree.md) — [no register says which rounds exist, and four records disagree](docs/backlog/scenarios/UX-0744-no-register-says-which-rounds-exist-and-four-records-disagree.md)
- [UX-779](docs/backlog/scenarios/UX-0779-the-readme-prints-two-wall-clocks-the-guide-says-are-not-the-suites.md) — [the README prints two wall clocks the guide says are not the suite's](docs/backlog/scenarios/UX-0779-the-readme-prints-two-wall-clocks-the-guide-says-are-not-the-suites.md)
- [UX-777](docs/backlog/scenarios/UX-0777-the-nine-page-built-sections-are-thirteen-in-two-documents.md) — [the nine page-built sections are thirteen, in two documents](docs/backlog/scenarios/UX-0777-the-nine-page-built-sections-are-thirteen-in-two-documents.md)
- [UX-780](docs/backlog/scenarios/UX-0780-the-map-says-a-shelf-shipped-and-one-linter-did.md) — [the map says a shelf shipped, and one linter did](docs/backlog/scenarios/UX-0780-the-map-says-a-shelf-shipped-and-one-linter-did.md)
- [UX-774](docs/backlog/scenarios/UX-0774-the-guide-is-at-its-band-ceiling-and-every-round-pays-a-trim.md) — [the guide is at its band ceiling, and every round pays a trim](docs/backlog/scenarios/UX-0774-the-guide-is-at-its-band-ceiling-and-every-round-pays-a-trim.md)
- [UX-798](docs/backlog/scenarios/UX-0798-the-directions-row-counts-a-round-s-closes-by-hand.md) — [the directions row counts a round's closes by hand](docs/backlog/scenarios/UX-0798-the-directions-row-counts-a-round-s-closes-by-hand.md)
- [UX-799](docs/backlog/scenarios/UX-0799-the-map-row-for-the-baseline-tool-names-one-of-its-two-modes.md) — [the map row for the baseline tool names one of its two modes](docs/backlog/scenarios/UX-0799-the-map-row-for-the-baseline-tool-names-one-of-its-two-modes.md)
- [UX-695](docs/backlog/scenarios/UX-0695-the-refactor-stream-takes-the-ledger-s-top-row-renderers-first.md) — [the refactor stream takes the ledger's top row — renderers first](docs/backlog/scenarios/UX-0695-the-refactor-stream-takes-the-ledger-s-top-row-renderers-first.md)
- [UX-806](docs/backlog/scenarios/UX-0806-the-plane-2-chapter-moves-into-the-native-trace-area-page.md) — [the Plane 2 chapter moves into the native-trace area page](docs/backlog/scenarios/UX-0806-the-plane-2-chapter-moves-into-the-native-trace-area-page.md)
- [UX-807](docs/backlog/scenarios/UX-0807-the-projection-chapter-moves-into-the-replay-area-page.md) — [the projection chapter moves into the replay area page](docs/backlog/scenarios/UX-0807-the-projection-chapter-moves-into-the-replay-area-page.md)
- [UX-810](docs/backlog/scenarios/UX-0810-the-plane-3-chapter-moves-into-the-tools-area-page.md) — [the Plane 3 chapter moves into the tools area page](docs/backlog/scenarios/UX-0810-the-plane-3-chapter-moves-into-the-tools-area-page.md)
- [UX-814](docs/backlog/scenarios/UX-0814-the-map-s-commit-body-row-is-behind-the-app-author-skip.md) — [the map's commit-body row is behind the App-author skip](docs/backlog/scenarios/UX-0814-the-map-s-commit-body-row-is-behind-the-app-author-skip.md)
- [UX-815](docs/backlog/scenarios/UX-0815-the-ingestion-path-chapter-moves-into-the-tools-area-page.md) — [the ingestion-path chapter moves into the tools area page](docs/backlog/scenarios/UX-0815-the-ingestion-path-chapter-moves-into-the-tools-area-page.md)
- [UX-816](docs/backlog/scenarios/UX-0816-the-bga-area-s-five-chapters-move-into-its-page.md) — [the bga area's five chapters move into its page](docs/backlog/scenarios/UX-0816-the-bga-area-s-five-chapters-move-into-its-page.md)
- [UX-689](docs/backlog/scenarios/UX-0689-the-architecture-document-moves-into-the-area-pages-one-track-at-a-tim.md) — [the architecture document moves into the area pages, one track at a time](docs/backlog/scenarios/UX-0689-the-architecture-document-moves-into-the-area-pages-one-track-at-a-tim.md)

<!-- /generated -->

## 0.4.0 — a capture you can carry (2026-09-03)

Named for what it makes possible: a capture leaves the machine that
took it. `bga bundle --export` writes an archive with a manifest of
every member's path, presence and contract version; `--load` refuses a
bundle it cannot read in full rather than half-reading it. The two
contracts under that — the capture directory itself, written down as
`capture-layout/v1`, and the host's own memory while the build ran —
are what made the archive derivable rather than a list someone keeps
current.

The state below is also the first one this ledger has recorded
honestly. `0.3.0`'s block was edited five times after it was written,
which is how five contracts that did not exist on 2026-08-27 came to
sit inside a row dated that day. `UX-550` restored it and froze it: a
superseded release row now carries a digest of its own state, and the
guard reddens on an edit instead of accepting it.

**Contract delta:** two bumped and three new, which makes the row
`breaking`. `analyze/v4 → v5` (`UX-535`) removes
`graph_summary.total_elements`, `.critical_path_length` and
`.max_parallelism`, three facts the same document already published
under `graph_metrics`. `plane2/v2 → v3` (`UX-384`) drops the element
names embedded in every redundancy finding — 78% of that section at 40
elements and 99% at 1,200. New: `capture-layout/v1` (`UX-381`, the
capture directory as a contract, specification 32.6),
`host-samples/v1` (`UX-378`, the host's memory and swap while the
build ran) and `bundle-manifest/v1` (`UX-520`). One new command,
`bundle`; none removed or renamed. `analyze/v4` and `plane2/v2` join
the read-never-written set, so an older store still analyzes.
`UX-540` registered the three *input* shapes this tool reads and never
writes — `graph/v9`, `run-context/v9`, `trace/v9` — which
`bga.contracts.reads()` now answers for; they are not in the set
below, because that set is what a release **emits**.

**Upgrade note:** a parser reading `graph_summary.total_elements`,
`graph_summary.critical_path_length` or `graph_summary.max_parallelism`
from `analyze` output reads them from `graph_metrics.num_elements`,
`.critical_path_length` and `.max_parallelism` instead — same numbers,
one carrier. A reader of `plane2.json`'s redundancy findings gets the
count and the row rather than the element list. Nothing else moved.

**Carried findings.** Architecture review 12 (closed-row marker 537)
filed five: `UX-548`, `UX-549`, `UX-550`, `UX-551` and `UX-552`.
`UX-550` is this row. The rest are open at this release and named here
so "we knew" is on the record rather than in someone's memory, along
with the thirteen backlog rows open at the cut.

```text state
digest: 32a915ff3719
contracts: analyze/v2 analyze/v3 analyze/v4 analyze/v5 analyze/v6 blast/v1 blast/v2 bundle-manifest/v1 capacity-model/v1 capture-layout/v1 compare/v1 compare/v2 correlate/v1 correlate/v2 host-samples/v1 host/v1 host/v2 plane2/v1 plane2/v2 plane2/v3 sources/v1 store-aggregate/v1 store/v1 sweep/v1 whatif/v1
commands: analyze baseline blast bundle cache-logs cache-trend capture checkout-cost chrome-to-trace compare correlate cross-check diagnostics doctor extract floors gen-synthetic graph graph-from-show log-to-chrome native-to-chrome rebuild-set release-notes replay run-context snapshot sweep timeline utilisation view whatif wrap
```

### What landed

<!-- generated: UX-252 332→537 -->
205 scenarios closed (closed-row markers 332 → 537).

**contracts**

- [UX-343](docs/backlog/scenarios/UX-0343-seven-in-ten-numbers-carry-no-declared-unit.md) — [half the numbers carry no unit at all](docs/backlog/scenarios/UX-0343-seven-in-ten-numbers-carry-no-declared-unit.md)
- [UX-341](docs/backlog/scenarios/UX-0341-one-unit-per-dimension.md) — [one unit per dimension](docs/backlog/scenarios/UX-0341-one-unit-per-dimension.md)
- [UX-345](docs/backlog/scenarios/UX-0345-the-chains-length-is-a-duration-wearing-a-counts-declaration.md) — [the chain's length is a duration wearing a count's declaration](docs/backlog/scenarios/UX-0345-the-chains-length-is-a-duration-wearing-a-counts-declaration.md)
- [UX-344](docs/backlog/scenarios/UX-0344-the-payload-is-six-deep-and-two-of-them-are-namespaces.md) — [the payload is six deep, and two of them are namespaces](docs/backlog/scenarios/UX-0344-the-payload-is-six-deep-and-two-of-them-are-namespaces.md)
- [UX-354](docs/backlog/scenarios/UX-0354-the-workflow-reads-the-payload-and-no-guard-reads-the-workflow.md) — [the workflow reads the payload, and no guard reads the workflow](docs/backlog/scenarios/UX-0354-the-workflow-reads-the-payload-and-no-guard-reads-the-workflow.md)
- [UX-382](docs/backlog/scenarios/UX-0382-the-element-entity-has-two-shapes-sharing-one-attribute.md) — [the element entity has two shapes, and they share one attribute](docs/backlog/scenarios/UX-0382-the-element-entity-has-two-shapes-sharing-one-attribute.md)
- [UX-381](docs/backlog/scenarios/UX-0381-the-capture-directory-is-a-contract-nothing-writes-down.md) — [the capture directory is a contract nothing writes down](docs/backlog/scenarios/UX-0381-the-capture-directory-is-a-contract-nothing-writes-down.md)
- [UX-384](docs/backlog/scenarios/UX-0384-a-redundancy-finding-still-carries-every-element-it-spans.md) — [a redundancy finding still carries every element it spans](docs/backlog/scenarios/UX-0384-a-redundancy-finding-still-carries-every-element-it-spans.md)
- [UX-386](docs/backlog/scenarios/UX-0386-plane2-v2-is-described-as-per-element-and-is-mostly-not.md) — [`plane2/v2` is described as per-element, and mostly is not](docs/backlog/scenarios/UX-0386-plane2-v2-is-described-as-per-element-and-is-mostly-not.md)
- [UX-408](docs/backlog/scenarios/UX-0408-serialized-pairs-described-as-its-own-opposite.md) — [`serialized_pairs` is described as its own opposite](docs/backlog/scenarios/UX-0408-serialized-pairs-described-as-its-own-opposite.md)
- [UX-431](docs/backlog/scenarios/UX-0431-the-arrow-count-reports-zero-losses-having-dropped-most.md) — [the arrow count reports zero losses, having drawn no arrows](docs/backlog/scenarios/UX-0431-the-arrow-count-reports-zero-losses-having-dropped-most.md)
- [UX-438](docs/backlog/scenarios/UX-0438-the-page-guesses-a-unit-and-says-so.md) — [the page guesses a unit on a real capture, and says so on the console](docs/backlog/scenarios/UX-0438-the-page-guesses-a-unit-and-says-so.md)
- [UX-440](docs/backlog/scenarios/UX-0440-two-rankings-over-one-order.md) — [two rankings over one order, and nothing says why there are two](docs/backlog/scenarios/UX-0440-two-rankings-over-one-order.md)
- [UX-452](docs/backlog/scenarios/UX-0452-the-legacy-chrome-trace-is-written-and-never-read.md) — [every capture writes a legacy Chrome trace that no reader opens](docs/backlog/scenarios/UX-0452-the-legacy-chrome-trace-is-written-and-never-read.md)
- [UX-466](docs/backlog/scenarios/UX-0466-what-the-capture-holds-and-the-trace-drops.md) — [nothing measures which captured field reaches a Perfetto slice](docs/backlog/scenarios/UX-0466-what-the-capture-holds-and-the-trace-drops.md)
- [UX-469](docs/backlog/scenarios/UX-0469-fields-the-capture-holds-and-the-trace-drops.md) — [the resource a task held reaches no Perfetto carrier](docs/backlog/scenarios/UX-0469-fields-the-capture-holds-and-the-trace-drops.md)
- [UX-483](docs/backlog/scenarios/UX-0483-a-provenance-record-inlines-the-whole-population-it-cites.md) — [a provenance record inlines whatever its path resolves to, and only convention keeps that from being a whole population](docs/backlog/scenarios/UX-0483-a-provenance-record-inlines-the-whole-population-it-cites.md)
- [UX-485](docs/backlog/scenarios/UX-0485-the-census-cannot-tell-a-carried-value-from-a-borrowed-one.md) — [the trace census cannot tell a field that arrived from one whose values another field brought](docs/backlog/scenarios/UX-0485-the-census-cannot-tell-a-carried-value-from-a-borrowed-one.md)

**analysis**

- [UX-365](docs/backlog/scenarios/UX-0365-the-finding-that-claims-the-superlative-is-the-small-one.md) — [the finding that claims the superlative is the small one](docs/backlog/scenarios/UX-0365-the-finding-that-claims-the-superlative-is-the-small-one.md)
- [UX-409](docs/backlog/scenarios/UX-0409-the-configure-tax-names-one-payer-twice.md) — [the configure tax names one payer twice](docs/backlog/scenarios/UX-0409-the-configure-tax-names-one-payer-twice.md)
- [UX-407](docs/backlog/scenarios/UX-0407-the-finding-that-is-the-answer-stays-at-the-terminal.md) — [the finding that *is* the answer stays at the terminal](docs/backlog/scenarios/UX-0407-the-finding-that-is-the-answer-stays-at-the-terminal.md)
- [UX-439](docs/backlog/scenarios/UX-0439-the-blast-radius-ranking-ties-and-the-tie-break-is-unstable.md) — [the blast-radius ranking ties, and the tie-break is unstable](docs/backlog/scenarios/UX-0439-the-blast-radius-ranking-ties-and-the-tie-break-is-unstable.md)
- [UX-467](docs/backlog/scenarios/UX-0467-does-the-shape-conclusion-support-a-decision.md) — [the graph-shape conclusions have no negative case](docs/backlog/scenarios/UX-0467-does-the-shape-conclusion-support-a-decision.md)
- [UX-477](docs/backlog/scenarios/UX-0477-the-chain-share-denominator-carries-a-constant.md) — [one graph, two verdicts — the chain-bound line is decided by how long the build is](docs/backlog/scenarios/UX-0477-the-chain-share-denominator-carries-a-constant.md)
- [UX-479](docs/backlog/scenarios/UX-0479-a-chain-bound-build-publishes-no-blast-radius.md) — [a chain-bound build publishes no blast radius, so the recipe-author never learns what their element reaches](docs/backlog/scenarios/UX-0479-a-chain-bound-build-publishes-no-blast-radius.md)
- [UX-475](docs/backlog/scenarios/UX-0475-mesh-graph-calls-a-linear-chain-a-mesh.md) — [`mesh-graph` calls a five-element linear chain "a mesh of near-equal chains"](docs/backlog/scenarios/UX-0475-mesh-graph-calls-a-linear-chain-a-mesh.md)
- [UX-478](docs/backlog/scenarios/UX-0478-the-graph-owner-vanishes-on-a-graph-problem.md) — [the graph-owner is not offered a reader on the one build whose defect is the graph](docs/backlog/scenarios/UX-0478-the-graph-owner-vanishes-on-a-graph-problem.md)
- [UX-474](docs/backlog/scenarios/UX-0474-the-blast-ranking-publishes-a-list-of-zeros.md) — ["Elements Most Worth Optimizing First (by blast radius)" ranks three elements whose blast radius is zero](docs/backlog/scenarios/UX-0474-the-blast-ranking-publishes-a-list-of-zeros.md)
- [UX-481](docs/backlog/scenarios/UX-0481-the-replay-lets-a-build-start-before-its-dependency-is-pulled.md) — [the replay starts a build before the artifacts it consumes have been pulled](docs/backlog/scenarios/UX-0481-the-replay-lets-a-build-start-before-its-dependency-is-pulled.md)
- [UX-531](docs/backlog/scenarios/UX-0531-bga-analyze-is-superlinear-and-the-page-pays.md) — [`bga analyze` is superlinear, and the page pays for it](docs/backlog/scenarios/UX-0531-bga-analyze-is-superlinear-and-the-page-pays.md)
- [UX-539](docs/backlog/scenarios/UX-0539-two-superlinear-terms-analyze-still-has.md) — [the two superlinear terms UX-531 measured and did not take](docs/backlog/scenarios/UX-0539-two-superlinear-terms-analyze-still-has.md)

**capture**

- [UX-333](docs/backlog/scenarios/UX-0333-the-name-is-the-whole-command.md) — [the name is the whole command](docs/backlog/scenarios/UX-0333-the-name-is-the-whole-command.md)
- [UX-379](docs/backlog/scenarios/UX-0379-the-hook-reads-a-rusage-struct-and-publishes-three-fields.md) — [the hook reads a rusage struct and publishes three of its fields](docs/backlog/scenarios/UX-0379-the-hook-reads-a-rusage-struct-and-publishes-three-fields.md)
- [UX-378](docs/backlog/scenarios/UX-0378-the-hosts-memory-is-a-number-from-before-the-build.md) — [the host's memory is a number from before the build, and an OOM leaves no trace](docs/backlog/scenarios/UX-0378-the-hosts-memory-is-a-number-from-before-the-build.md)
- [UX-375](docs/backlog/scenarios/UX-0375-the-plane-2-report-has-one-uncapped-population.md) — [the Plane 2 report has one uncapped population](docs/backlog/scenarios/UX-0375-the-plane-2-report-has-one-uncapped-population.md)
- [UX-377](docs/backlog/scenarios/UX-0377-the-run-and-the-graph-disagree-about-max-jobs.md) — [the run and the graph disagree about max-jobs, and on a default capture neither has it](docs/backlog/scenarios/UX-0377-the-run-and-the-graph-disagree-about-max-jobs.md)
- [UX-376](docs/backlog/scenarios/UX-0376-the-census-cannot-see-a-tool-this-build-produced.md) — [the census cannot see a tool this build produced, and the spine policy believes it](docs/backlog/scenarios/UX-0376-the-census-cannot-see-a-tool-this-build-produced.md)
- [UX-385](docs/backlog/scenarios/UX-0385-a-capture-cannot-detect-the-binary-it-never-saw.md) — [a capture cannot detect the binary it never saw](docs/backlog/scenarios/UX-0385-a-capture-cannot-detect-the-binary-it-never-saw.md)
- [UX-405](docs/backlog/scenarios/UX-0405-a-relative-project-forfeits-plane-2-in-silence.md) — [a relative `--project` forfeits Plane 2 in silence](docs/backlog/scenarios/UX-0405-a-relative-project-forfeits-plane-2-in-silence.md)
- [UX-410](docs/backlog/scenarios/UX-0410-a-project-flag-that-is-not-a-project-builds-one-anyway.md) — [a `--project` that is not a project builds one anyway](docs/backlog/scenarios/UX-0410-a-project-flag-that-is-not-a-project-builds-one-anyway.md)
- [UX-406](docs/backlog/scenarios/UX-0406-the-spine-counts-every-process-twice-in-the-trace.md) — [the spine counts every process twice in the trace](docs/backlog/scenarios/UX-0406-the-spine-counts-every-process-twice-in-the-trace.md)
- [UX-395](docs/backlog/scenarios/UX-0395-format-chrome-silently-drops-the-flows-and-counters.md) — [`--format chrome` silently drops the flows and counters](docs/backlog/scenarios/UX-0395-format-chrome-silently-drops-the-flows-and-counters.md)
- [UX-465](docs/backlog/scenarios/UX-0465-a-project-generator-for-real-builds.md) — [nothing generates a BuildStream project, so axes D, F and G are hand-authored or absent](docs/backlog/scenarios/UX-0465-a-project-generator-for-real-builds.md)
- [UX-470](docs/backlog/scenarios/UX-0470-what-the-planes-could-capture-and-do-not.md) — [nothing compares a plane's capability with the records it writes](docs/backlog/scenarios/UX-0470-what-the-planes-could-capture-and-do-not.md)
- [UX-487](docs/backlog/scenarios/UX-0487-a-spine-only-process-has-no-fault-or-io-counts.md) — [a spine-only process has no fault counts and no I/O, from a /proc read the spine already does](docs/backlog/scenarios/UX-0487-a-spine-only-process-has-no-fault-or-io-counts.md)
- [UX-518](docs/backlog/scenarios/UX-0518-one-buildstream-startup-per-element.md) — [the snapshot's tail pays one BuildStream startup per element](docs/backlog/scenarios/UX-0518-one-buildstream-startup-per-element.md)
- [UX-519](docs/backlog/scenarios/UX-0519-the-snapshot-tail-goes-quiet.md) — [the snapshot's tail goes quiet in the one phase that has no line](docs/backlog/scenarios/UX-0519-the-snapshot-tail-goes-quiet.md)
- [UX-514](docs/backlog/scenarios/UX-0514-the-schedule-can-never-capture-a-second-commit.md) — [the capture schedule can never produce a second commit](docs/backlog/scenarios/UX-0514-the-schedule-can-never-capture-a-second-commit.md)
- [UX-530](docs/backlog/scenarios/UX-0530-a-real-capture-reaches-the-track-ceiling-and-loses-the-timeline.md) — [a real capture reaches the track ceiling, and the timeline is dropped whole](docs/backlog/scenarios/UX-0530-a-real-capture-reaches-the-track-ceiling-and-loses-the-timeline.md)

**viewer**

- [UX-342](docs/backlog/scenarios/UX-0342-the-export-ships-six-schemas-nothing-can-resolve.md) — [the export ships six schemas nothing can resolve](docs/backlog/scenarios/UX-0342-the-export-ships-six-schemas-nothing-can-resolve.md)
- [UX-346](docs/backlog/scenarios/UX-0346-two-thirds-of-the-page-is-the-schemas-own-sentences.md) — [two thirds of the page is the schema's own sentences](docs/backlog/scenarios/UX-0346-two-thirds-of-the-page-is-the-schemas-own-sentences.md)
- [UX-347](docs/backlog/scenarios/UX-0347-the-click-budget-is-satisfied-by-never-folding.md) — [the click budget is satisfied by never folding](docs/backlog/scenarios/UX-0347-the-click-budget-is-satisfied-by-never-folding.md)
- [UX-348](docs/backlog/scenarios/UX-0348-the-two-capabilities-the-tool-is-for-are-a-closed-fold-and-a-stub.md) — [the two capabilities the tool is for are a closed fold and a stub](docs/backlog/scenarios/UX-0348-the-two-capabilities-the-tool-is-for-are-a-closed-fold-and-a-stub.md)
- [UX-351](docs/backlog/scenarios/UX-0351-the-label-prints-the-unit-the-value-already-carries.md) — [the label prints the unit the value already carries](docs/backlog/scenarios/UX-0351-the-label-prints-the-unit-the-value-already-carries.md)
- [UX-350](docs/backlog/scenarios/UX-0350-the-shape-channel-is-written-and-unbuilt.md) — [the shape channel is written and unbuilt](docs/backlog/scenarios/UX-0350-the-shape-channel-is-written-and-unbuilt.md)
- [UX-349](docs/backlog/scenarios/UX-0349-the-table-tools-do-not-scale-with-the-table.md) — [the table tools do not scale with the table](docs/backlog/scenarios/UX-0349-the-table-tools-do-not-scale-with-the-table.md)
- [UX-355](docs/backlog/scenarios/UX-0355-a-fold-that-expands-nothing-and-a-copy-that-says-nothing.md) — [a fold that expands nothing, and a copy that says nothing](docs/backlog/scenarios/UX-0355-a-fold-that-expands-nothing-and-a-copy-that-says-nothing.md)
- [UX-356](docs/backlog/scenarios/UX-0356-the-merge-keeps-four-of-twenty-eight-fields.md) — [the element join is "merged into the element table", and the merge keeps four of its twenty-eight fields](docs/backlog/scenarios/UX-0356-the-merge-keeps-four-of-twenty-eight-fields.md)
- [UX-357](docs/backlog/scenarios/UX-0357-the-provenance-shows-the-claim-and-withholds-the-rule.md) — [the provenance section shows the claim and withholds the rule](docs/backlog/scenarios/UX-0357-the-provenance-shows-the-claim-and-withholds-the-rule.md)
- [UX-361](docs/backlog/scenarios/UX-0361-the-drawing-vocabulary-is-two-shapes.md) — [the drawing vocabulary is two shapes, and the tool's central claim has neither](docs/backlog/scenarios/UX-0361-the-drawing-vocabulary-is-two-shapes.md)
- [UX-360](docs/backlog/scenarios/UX-0360-folding-paid-the-distance-and-the-volume-grew.md) — [folding paid the distance, and the volume grew by a third](docs/backlog/scenarios/UX-0360-folding-paid-the-distance-and-the-volume-grew.md)
- [UX-362](docs/backlog/scenarios/UX-0362-the-absence-sentence-claims-a-plane-it-does-not-own.md) — [the Plane 2 absence sentence claims a timeline it does not own](docs/backlog/scenarios/UX-0362-the-absence-sentence-claims-a-plane-it-does-not-own.md)
- [UX-364](docs/backlog/scenarios/UX-0364-the-perfetto-lead-promises-a-plane-the-trace-does-not-carry.md) — [the Perfetto lead promises a plane the trace does not carry](docs/backlog/scenarios/UX-0364-the-perfetto-lead-promises-a-plane-the-trace-does-not-carry.md)
- [UX-369](docs/backlog/scenarios/UX-0369-the-query-library-substitutes-one-projects-element.md) — [the query library substitutes one project's element name](docs/backlog/scenarios/UX-0369-the-query-library-substitutes-one-projects-element.md)
- [UX-367](docs/backlog/scenarios/UX-0367-the-volume-budget-is-enforced-at-eleven-elements.md) — [the volume budget is enforced at eleven elements](docs/backlog/scenarios/UX-0367-the-volume-budget-is-enforced-at-eleven-elements.md)
- [UX-368](docs/backlog/scenarios/UX-0368-no-finding-carries-a-perfetto-query.md) — [no finding carries a Perfetto query](docs/backlog/scenarios/UX-0368-no-finding-carries-a-perfetto-query.md)
- [UX-366](docs/backlog/scenarios/UX-0366-all-rows-shows-twenty-five-of-twelve-hundred.md) — ["All rows" shows 25 of 1,202](docs/backlog/scenarios/UX-0366-all-rows-shows-twenty-five-of-twelve-hundred.md)
- [UX-370](docs/backlog/scenarios/UX-0370-plane-twos-frequency-and-time-do-not-reach-the-page.md) — [Plane 2's frequency and time do not reach the page](docs/backlog/scenarios/UX-0370-plane-twos-frequency-and-time-do-not-reach-the-page.md)
- [UX-371](docs/backlog/scenarios/UX-0371-a-fifth-of-the-page-is-repeated-text.md) — [a fifth of the page is repeated text](docs/backlog/scenarios/UX-0371-a-fifth-of-the-page-is-repeated-text.md)
- [UX-372](docs/backlog/scenarios/UX-0372-the-page-has-one-reader.md) — [the page has one reader](docs/backlog/scenarios/UX-0372-the-page-has-one-reader.md)
- [UX-373](docs/backlog/scenarios/UX-0373-two-satellite-pages-for-one-handoff.md) — [two satellite pages for one handoff](docs/backlog/scenarios/UX-0373-two-satellite-pages-for-one-handoff.md)
- [UX-374](docs/backlog/scenarios/UX-0374-the-page-renames-the-readers-elements.md) — [the page renames the reader's elements and programs](docs/backlog/scenarios/UX-0374-the-page-renames-the-readers-elements.md)
- [UX-380](docs/backlog/scenarios/UX-0380-the-trace-says-what-an-element-is-never-where-it-sits.md) — [the trace says what an element is, never where it sits](docs/backlog/scenarios/UX-0380-the-trace-says-what-an-element-is-never-where-it-sits.md)
- [UX-383](docs/backlog/scenarios/UX-0383-plane-2s-per-element-blocks-reach-the-terminal-not-the-page.md) — [Plane 2's per-element blocks reach the terminal, not the page](docs/backlog/scenarios/UX-0383-plane-2s-per-element-blocks-reach-the-terminal-not-the-page.md)
- [UX-398](docs/backlog/scenarios/UX-0398-the-library-question-measured-against-the-factory.md) — [the library question, measured against the factory](docs/backlog/scenarios/UX-0398-the-library-question-measured-against-the-factory.md)
- [UX-399](docs/backlog/scenarios/UX-0399-the-browser-is-the-library.md) — [the browser is the library](docs/backlog/scenarios/UX-0399-the-browser-is-the-library.md)
- [UX-388](docs/backlog/scenarios/UX-0388-an-empty-population-disappears-without-a-word.md) — [an empty population disappears without a word](docs/backlog/scenarios/UX-0388-an-empty-population-disappears-without-a-word.md)
- [UX-391](docs/backlog/scenarios/UX-0391-wall-clock-share-shows-the-reader-a-composite-key.md) — [`wall_clock_share_us` shows the reader a composite key](docs/backlog/scenarios/UX-0391-wall-clock-share-shows-the-reader-a-composite-key.md)
- [UX-389](docs/backlog/scenarios/UX-0389-fourteen-plane-two-blocks-reach-no-browser.md) — [fourteen of twenty-five Plane 2 blocks reach no browser](docs/backlog/scenarios/UX-0389-fourteen-plane-two-blocks-reach-no-browser.md)
- [UX-390](docs/backlog/scenarios/UX-0390-attribution-and-its-hints-are-one-population-in-two-sections.md) — [attribution and its hints are one population in two sections](docs/backlog/scenarios/UX-0390-attribution-and-its-hints-are-one-population-in-two-sections.md)
- [UX-392](docs/backlog/scenarios/UX-0392-thirty-one-tables-and-one-search-box.md) — [thirty-one tables, one search box](docs/backlog/scenarios/UX-0392-thirty-one-tables-and-one-search-box.md)
- [UX-393](docs/backlog/scenarios/UX-0393-nothing-moves-to-the-next-section-or-back-to-the-top.md) — [nothing moves to the next section, or back to the top](docs/backlog/scenarios/UX-0393-nothing-moves-to-the-next-section-or-back-to-the-top.md)
- [UX-396](docs/backlog/scenarios/UX-0396-sixteen-of-forty-four-sections-draw-something.md) — [sixteen of forty-four sections draw something](docs/backlog/scenarios/UX-0396-sixteen-of-forty-four-sections-draw-something.md)
- [UX-397](docs/backlog/scenarios/UX-0397-the-perfetto-handoff-sits-outside-the-pinned-rail.md) — [the Perfetto handoff sits outside the pinned rail](docs/backlog/scenarios/UX-0397-the-perfetto-handoff-sits-outside-the-pinned-rail.md)
- [UX-394](docs/backlog/scenarios/UX-0394-nothing-in-the-page-moves-between-runs.md) — [nothing in the page moves between runs](docs/backlog/scenarios/UX-0394-nothing-in-the-page-moves-between-runs.md)
- [UX-413](docs/backlog/scenarios/UX-0413-a-population-with-nothing-to-rank-by-is-never-bounded.md) — [a population with nothing to rank by is never bounded](docs/backlog/scenarios/UX-0413-a-population-with-nothing-to-rank-by-is-never-bounded.md)
- [UX-412](docs/backlog/scenarios/UX-0412-a-table-of-one-says-one-rows.md) — [a table of one says "1 rows"](docs/backlog/scenarios/UX-0412-a-table-of-one-says-one-rows.md)
- [UX-414](docs/backlog/scenarios/UX-0414-two-sections-fall-into-everything-else.md) — [two sections fall into "Everything else", and the guard's fixture cannot see it](docs/backlog/scenarios/UX-0414-two-sections-fall-into-everything-else.md)
- [UX-411](docs/backlog/scenarios/UX-0411-a-ranked-map-has-no-instrument.md) — [a ranked map has no instrument](docs/backlog/scenarios/UX-0411-a-ranked-map-has-no-instrument.md)
- [UX-419](docs/backlog/scenarios/UX-0419-a-map-population-is-bounded-by-nothing.md) — [a map population is bounded by nothing](docs/backlog/scenarios/UX-0419-a-map-population-is-bounded-by-nothing.md)
- [UX-434](docs/backlog/scenarios/UX-0434-the-graph-shape-query-collapses-every-level.md) — [the graph-shape query collapses every level into one row](docs/backlog/scenarios/UX-0434-the-graph-shape-query-collapses-every-level.md)
- [UX-430](docs/backlog/scenarios/UX-0430-the-trace-budget-counts-bytes-and-perfetto-spends-tracks.md) — [the trace budget counts bytes, and Perfetto spends tracks](docs/backlog/scenarios/UX-0430-the-trace-budget-counts-bytes-and-perfetto-spends-tracks.md)
- [UX-433](docs/backlog/scenarios/UX-0433-nothing-pivots-by-executable.md) — [nothing pivots by executable, because no annotation names one](docs/backlog/scenarios/UX-0433-nothing-pivots-by-executable.md)
- [UX-429](docs/backlog/scenarios/UX-0429-a-command-is-rendered-as-a-list-of-its-words.md) — [a command is rendered as a list of its words](docs/backlog/scenarios/UX-0429-a-command-is-rendered-as-a-list-of-its-words.md)
- [UX-436](docs/backlog/scenarios/UX-0436-the-page-has-no-control-style.md) — [forty-four controls are the browser's, not the page's](docs/backlog/scenarios/UX-0436-the-page-has-no-control-style.md)
- [UX-435](docs/backlog/scenarios/UX-0435-the-handoff-box-is-measured-in-the-mode-it-is-smallest.md) — [the handoff box is measured in the mode where it is smallest](docs/backlog/scenarios/UX-0435-the-handoff-box-is-measured-in-the-mode-it-is-smallest.md)
- [UX-437](docs/backlog/scenarios/UX-0437-the-host-series-is-captured-and-read-by-nobody.md) — [the host memory series is captured every run and read by nobody](docs/backlog/scenarios/UX-0437-the-host-series-is-captured-and-read-by-nobody.md)
- [UX-443](docs/backlog/scenarios/UX-0443-the-served-handoff-cannot-count-its-own-edges.md) — [the served handoff cannot count its own edges](docs/backlog/scenarios/UX-0443-the-served-handoff-cannot-count-its-own-edges.md)
- [UX-448](docs/backlog/scenarios/UX-0448-the-element-scoped-pivot-has-no-finding-to-arrive-from.md) — [the element-scoped pivot has no finding to arrive from](docs/backlog/scenarios/UX-0448-the-element-scoped-pivot-has-no-finding-to-arrive-from.md)
- [UX-451](docs/backlog/scenarios/UX-0451-the-handoff-refusal-sentence-has-the-rails-width.md) — [the hand-off's refusal sentence is written into a 208px column](docs/backlog/scenarios/UX-0451-the-handoff-refusal-sentence-has-the-rails-width.md)
- [UX-521](docs/backlog/scenarios/UX-0521-the-handoff-goes-quiet-for-minutes.md) — [the Perfetto handoff goes quiet, and cannot tell working from refused](docs/backlog/scenarios/UX-0521-the-handoff-goes-quiet-for-minutes.md)
- [UX-532](docs/backlog/scenarios/UX-0532-the-table-tools-read-the-nested-tables-rows-as-their-own.md) — [the table tools read the nested tables' rows as their own](docs/backlog/scenarios/UX-0532-the-table-tools-read-the-nested-tables-rows-as-their-own.md)
- [UX-534](docs/backlog/scenarios/UX-0534-focus-answers-far-above-the-button.md) — [Focus answers 25,501 px above the button](docs/backlog/scenarios/UX-0534-focus-answers-far-above-the-button.md)
- [UX-536](docs/backlog/scenarios/UX-0536-four-controls-that-say-less-than-they-do.md) — [four controls that say less than they do](docs/backlog/scenarios/UX-0536-four-controls-that-say-less-than-they-do.md)
- [UX-527](docs/backlog/scenarios/UX-0527-one-control-has-an-option-per-element.md) — [one control has an option per element](docs/backlog/scenarios/UX-0527-one-control-has-an-option-per-element.md)
- [UX-528](docs/backlog/scenarios/UX-0528-the-served-store-section-grows-with-every-snapshot.md) — [the served store section and run picker grow with every snapshot](docs/backlog/scenarios/UX-0528-the-served-store-section-grows-with-every-snapshot.md)
- [UX-535](docs/backlog/scenarios/UX-0535-one-fact-published-twice-drawn-twice-listed-twice.md) — [one fact published twice, drawn twice, listed twice](docs/backlog/scenarios/UX-0535-one-fact-published-twice-drawn-twice-listed-twice.md)
- [UX-533](docs/backlog/scenarios/UX-0533-the-served-page-is-the-capture-time-analysis.md) — [the served page is the capture-time analysis, and cannot say so](docs/backlog/scenarios/UX-0533-the-served-page-is-the-capture-time-analysis.md)
- [UX-529](docs/backlog/scenarios/UX-0529-the-export-data-half-is-unbounded-and-holds-each-row-twice.md) — [the export's data half is unbounded, and holds each row twice](docs/backlog/scenarios/UX-0529-the-export-data-half-is-unbounded-and-holds-each-row-twice.md)

**store**

- [UX-96](docs/backlog/scenarios/UX-0096-the-baseline-set-exists-but-assembling-it-is-a-scavenger-hunt.md) — [the baseline set exists, but assembling it is a scavenger hunt](docs/backlog/scenarios/UX-0096-the-baseline-set-exists-but-assembling-it-is-a-scavenger-hunt.md)
- [UX-92](docs/backlog/scenarios/UX-0092-cache-effectiveness-is-invisible-to-the-tool.md) — [cache effectiveness — hits, misses, churn, trends — is invisible to the tool](docs/backlog/scenarios/UX-0092-cache-effectiveness-is-invisible-to-the-tool.md)
- [UX-520](docs/backlog/scenarios/UX-0520-a-run-bundle-you-can-carry.md) — [a capture you can carry to another machine in one command](docs/backlog/scenarios/UX-0520-a-run-bundle-you-can-carry.md)

**guards**

- [UX-337](docs/backlog/scenarios/UX-0337-the-two-viewer-modules-split-along-their-seams.md) — [the two viewer modules split along their seams](docs/backlog/scenarios/UX-0337-the-two-viewer-modules-split-along-their-seams.md)
- [UX-340](docs/backlog/scenarios/UX-0340-the-graph-was-derived-with-a-broken-instrument.md) — [the graph was derived with a broken instrument](docs/backlog/scenarios/UX-0340-the-graph-was-derived-with-a-broken-instrument.md)
- [UX-359](docs/backlog/scenarios/UX-0359-every-guard-measures-a-plane-2-stripped-page.md) — [every guard measures a page with Plane 2 stripped out of it](docs/backlog/scenarios/UX-0359-every-guard-measures-a-plane-2-stripped-page.md)
- [UX-358](docs/backlog/scenarios/UX-0358-no-fixture-can-render-a-timeline.md) — [no committed fixture can render a timeline, so the handoff the tool is for is never exercised](docs/backlog/scenarios/UX-0358-no-fixture-can-render-a-timeline.md)
- [UX-363](docs/backlog/scenarios/UX-0363-the-small-tier-budget-is-nine-tenths-headroom.md) — [the small tier's budget is nine-tenths headroom](docs/backlog/scenarios/UX-0363-the-small-tier-budget-is-nine-tenths-headroom.md)
- [UX-387](docs/backlog/scenarios/UX-0387-the-close-check-is-blind-to-the-mismatch-it-exists-for.md) — [the close check is blind to the mismatch it exists for](docs/backlog/scenarios/UX-0387-the-close-check-is-blind-to-the-mismatch-it-exists-for.md)
- [UX-400](docs/backlog/scenarios/UX-0400-every-population-is-tested-at-zero-one-and-many.md) — [every population is tested at zero, one and many](docs/backlog/scenarios/UX-0400-every-population-is-tested-at-zero-one-and-many.md)
- [UX-401](docs/backlog/scenarios/UX-0401-no-key-is-terminal-only-in-silence.md) — [no key is terminal-only in silence](docs/backlog/scenarios/UX-0401-no-key-is-terminal-only-in-silence.md)
- [UX-404](docs/backlog/scenarios/UX-0404-the-unit-census-stops-at-the-analyze-door.md) — [the unit census stops at the analyze door](docs/backlog/scenarios/UX-0404-the-unit-census-stops-at-the-analyze-door.md)
- [UX-402](docs/backlog/scenarios/UX-0402-the-journey-is-a-guard-with-an-answer-key.md) — [the journey is a guard with an answer key](docs/backlog/scenarios/UX-0402-the-journey-is-a-guard-with-an-answer-key.md)
- [UX-403](docs/backlog/scenarios/UX-0403-the-guard-census.md) — [the guard census — every guard proves it can fail](docs/backlog/scenarios/UX-0403-the-guard-census.md)
- [UX-415](docs/backlog/scenarios/UX-0415-the-shared-probe-is-always-served.md) — [the shared node probe says `file:` and always measures `http:`](docs/backlog/scenarios/UX-0415-the-shared-probe-is-always-served.md)
- [UX-418](docs/backlog/scenarios/UX-0418-a-slow-file-is-small-until-ci-times-out.md) — [a slow file is small until CI times out](docs/backlog/scenarios/UX-0418-a-slow-file-is-small-until-ci-times-out.md)
- [UX-420](docs/backlog/scenarios/UX-0420-ci-cannot-check-tier-drift-without-its-own-clock.md) — [CI cannot check tier drift without a reference of its own](docs/backlog/scenarios/UX-0420-ci-cannot-check-tier-drift-without-its-own-clock.md)
- [UX-424](docs/backlog/scenarios/UX-0424-the-bulk-add-hook-reads-command-text.md) — [the bulk-add hook matches command text, not command effect](docs/backlog/scenarios/UX-0424-the-bulk-add-hook-reads-command-text.md)
- [UX-423](docs/backlog/scenarios/UX-0423-the-drift-shift-is-a-median-taken-at-the-noise-floor.md) — [the drift shift is a median taken at the noise floor](docs/backlog/scenarios/UX-0423-the-drift-shift-is-a-median-taken-at-the-noise-floor.md)
- [UX-421](docs/backlog/scenarios/UX-0421-the-small-tier-budget-window-is-a-second-wide.md) — [the small tier's budget window is a second wide](docs/backlog/scenarios/UX-0421-the-small-tier-budget-window-is-a-second-wide.md)
- [UX-422](docs/backlog/scenarios/UX-0422-the-layout-ratio-guard-measures-the-runner-too.md) — [the layout-cost guard measures the runner as well as the page](docs/backlog/scenarios/UX-0422-the-layout-ratio-guard-measures-the-runner-too.md)
- [UX-427](docs/backlog/scenarios/UX-0427-the-reference-can-be-recorded-but-never-refreshed.md) — [the CI reference can be recorded but never refreshed](docs/backlog/scenarios/UX-0427-the-reference-can-be-recorded-but-never-refreshed.md)
- [UX-428](docs/backlog/scenarios/UX-0428-the-run-picker-probe-reads-before-the-page-renders.md) — [the run-picker probe reads the page before it has rendered](docs/backlog/scenarios/UX-0428-the-run-picker-probe-reads-before-the-page-renders.md)
- [UX-432](docs/backlog/scenarios/UX-0432-the-question-library-had-never-been-run.md) — [the question library had never been run](docs/backlog/scenarios/UX-0432-the-question-library-had-never-been-run.md)
- [UX-441](docs/backlog/scenarios/UX-0441-the-reference-dump-buries-the-failure-it-follows.md) — [the reference dump buries the failure it follows](docs/backlog/scenarios/UX-0441-the-reference-dump-buries-the-failure-it-follows.md)
- [UX-442](docs/backlog/scenarios/UX-0442-one-slow-sample-reddens-ci.md) — [one slow sample reddens CI, and nothing asks it to repeat](docs/backlog/scenarios/UX-0442-one-slow-sample-reddens-ci.md)
- [UX-444](docs/backlog/scenarios/UX-0444-the-page-budget-and-the-data-ratio-have-converged.md) — [the page budget and the data ratio have converged](docs/backlog/scenarios/UX-0444-the-page-budget-and-the-data-ratio-have-converged.md)
- [UX-445](docs/backlog/scenarios/UX-0445-the-track-bound-is-one-sample.md) — [the track bound is one sample, and nothing has measured the cost it stands for](docs/backlog/scenarios/UX-0445-the-track-bound-is-one-sample.md)
- [UX-453](docs/backlog/scenarios/UX-0453-the-clock-bracket-compares-a-rounded-stamp.md) — [the clock bracket compares a rounded stamp with unrounded readings](docs/backlog/scenarios/UX-0453-the-clock-bracket-compares-a-rounded-stamp.md)
- [UX-454](docs/backlog/scenarios/UX-0454-closing-a-task-twice-doubles-its-status-word.md) — [closing a task twice doubles its status word](docs/backlog/scenarios/UX-0454-closing-a-task-twice-doubles-its-status-word.md)
- [UX-449](docs/backlog/scenarios/UX-0449-a-skip-reason-is-only-checked-where-the-skip-happens.md) — [a skip reason is only checked where the skip happens](docs/backlog/scenarios/UX-0449-a-skip-reason-is-only-checked-where-the-skip-happens.md)
- [UX-450](docs/backlog/scenarios/UX-0450-two-viewer-modules-sit-exactly-on-the-ceiling.md) — [two viewer modules sit exactly on the line-count ceiling](docs/backlog/scenarios/UX-0450-two-viewer-modules-sit-exactly-on-the-ceiling.md)
- [UX-457](docs/backlog/scenarios/UX-0457-the-reference-refresh-artifact-is-unreachable.md) — [the reference can only be refreshed from a host the round cannot reach](docs/backlog/scenarios/UX-0457-the-reference-refresh-artifact-is-unreachable.md)
- [UX-455](docs/backlog/scenarios/UX-0455-two-files-drift-past-their-tier-and-the-parse-is-red.md) — [two files have grown past the tier they are listed in](docs/backlog/scenarios/UX-0455-two-files-drift-past-their-tier-and-the-parse-is-red.md)
- [UX-456](docs/backlog/scenarios/UX-0456-two-bst-gated-guards-are-at-the-noise-floor.md) — [two bst-gated guards fail on the runner and not on the diff](docs/backlog/scenarios/UX-0456-two-bst-gated-guards-are-at-the-noise-floor.md)
- [UX-462](docs/backlog/scenarios/UX-0462-following-the-examples-readme-reddens-the-suite.md) — [following `examples/README.md` reddens the suite](docs/backlog/scenarios/UX-0462-following-the-examples-readme-reddens-the-suite.md)
- [UX-463](docs/backlog/scenarios/UX-0463-which-topologies-do-we-actually-need.md) — [which topologies we actually need, and why that set](docs/backlog/scenarios/UX-0463-which-topologies-do-we-actually-need.md)
- [UX-464](docs/backlog/scenarios/UX-0464-the-curated-covering-set.md) — [the curated covering set — T1, T2, T3 and half of T4](docs/backlog/scenarios/UX-0464-the-curated-covering-set.md)
- [UX-458](docs/backlog/scenarios/UX-0458-the-drift-factor-was-never-sized-from-data.md) — [the drift factor is a starting value nothing has re-measured](docs/backlog/scenarios/UX-0458-the-drift-factor-was-never-sized-from-data.md)
- [UX-480](docs/backlog/scenarios/UX-0480-the-bst-tier-pin-is-written-twice-and-read-once.md) — [the bst-tier pin is written twice and the guard read the half that does not decide](docs/backlog/scenarios/UX-0480-the-bst-tier-pin-is-written-twice-and-read-once.md)
- [UX-482](docs/backlog/scenarios/UX-0482-the-browser-harness-waits-a-duration-not-a-condition.md) — [the browser harness waited a duration where it meant a condition](docs/backlog/scenarios/UX-0482-the-browser-harness-waits-a-duration-not-a-condition.md)
- [UX-459](docs/backlog/scenarios/UX-0459-seven-examples-keep-nothing-analysable.md) — [eight findings are reachable by nothing a clone has](docs/backlog/scenarios/UX-0459-seven-examples-keep-nothing-analysable.md)
- [UX-460](docs/backlog/scenarios/UX-0460-no-guard-says-which-findings-a-fixture-produces.md) — [nothing says which findings the fixtures can actually produce](docs/backlog/scenarios/UX-0460-no-guard-says-which-findings-a-fixture-produces.md)
- [UX-473](docs/backlog/scenarios/UX-0473-ci-never-builds-a-generated-project.md) — [nothing in CI builds a generated project](docs/backlog/scenarios/UX-0473-ci-never-builds-a-generated-project.md)
- [UX-484](docs/backlog/scenarios/UX-0484-the-step-that-must-not-use-set-e-was-given-it-by-the-runner.md) — [the step that must not use `set -e` was given it by the runner, and its guard read the wrong half](docs/backlog/scenarios/UX-0484-the-step-that-must-not-use-set-e-was-given-it-by-the-runner.md)
- [UX-476](docs/backlog/scenarios/UX-0476-an-untouched-file-crossed-on-two-consecutive-runs.md) — [the falsifier `UX-458` named arrived on the very next run](docs/backlog/scenarios/UX-0476-an-untouched-file-crossed-on-two-consecutive-runs.md)
- [UX-486](docs/backlog/scenarios/UX-0486-a-committed-analysis-fixture-drifts-from-the-analyzer.md) — [a committed analysis fixture drifts from the analyzer, and one clause out of many noticed](docs/backlog/scenarios/UX-0486-a-committed-analysis-fixture-drifts-from-the-analyzer.md)
- [UX-488](docs/backlog/scenarios/UX-0488-the-wholesale-re-record-the-drift-rule-change-has-to-follow.md) — [the reference is five hand-appends deep, and the re-record has to come after the rule change](docs/backlog/scenarios/UX-0488-the-wholesale-re-record-the-drift-rule-change-has-to-follow.md)
- [UX-494](docs/backlog/scenarios/UX-0494-the-explanation-filter-names-the-whole-suite.md) — [the drift gate's explanation filter names the whole suite, so it explains nothing](docs/backlog/scenarios/UX-0494-the-explanation-filter-names-the-whole-suite.md)
- [UX-497](docs/backlog/scenarios/UX-0497-the-register-is-a-budget.md) — [the register is a budget, not a preference](docs/backlog/scenarios/UX-0497-the-register-is-a-budget.md)
- [UX-503](docs/backlog/scenarios/UX-0503-a-new-test-file-records-itself.md) — [a new test file records itself in the CI reference](docs/backlog/scenarios/UX-0503-a-new-test-file-records-itself.md)
- [UX-508](docs/backlog/scenarios/UX-0508-a-stale-verdict-fires-on-one-sample.md) — [the whole-runner verdict fires on one sample](docs/backlog/scenarios/UX-0508-a-stale-verdict-fires-on-one-sample.md)
- [UX-504](docs/backlog/scenarios/UX-0504-an-implementer-agent-that-may-edit-in-a-worktree.md) — [an implementer agent that may edit, in a worktree only](docs/backlog/scenarios/UX-0504-an-implementer-agent-that-may-edit-in-a-worktree.md)
- [UX-509](docs/backlog/scenarios/UX-0509-the-agent-worktree-is-inside-the-lint.md) — [a parallel track's worktree is inside the tree that lints it](docs/backlog/scenarios/UX-0509-the-agent-worktree-is-inside-the-lint.md)
- [UX-490](docs/backlog/scenarios/UX-0490-the-clone-guard-cannot-see-an-absolute-path.md) — [the guard against one-machine data cannot see an absolute path](docs/backlog/scenarios/UX-0490-the-clone-guard-cannot-see-an-absolute-path.md)
- [UX-491](docs/backlog/scenarios/UX-0491-the-gate-line-has-no-route-for-a-reader-without-the-log.md) — [the drift gate's own line has no route a reader can reach](docs/backlog/scenarios/UX-0491-the-gate-line-has-no-route-for-a-reader-without-the-log.md)
- [UX-495](docs/backlog/scenarios/UX-0495-three-browser-guards-swing-under-parallel-load.md) — [three browser guards swing 1.5-2.3x under parallel load](docs/backlog/scenarios/UX-0495-three-browser-guards-swing-under-parallel-load.md)
- [UX-496](docs/backlog/scenarios/UX-0496-a-one-run-re-record-bakes-in-one-sample-per-file.md) — [a wholesale re-record samples every file once, and the drift factor has never been sized against that](docs/backlog/scenarios/UX-0496-a-one-run-re-record-bakes-in-one-sample-per-file.md)
- [UX-489](docs/backlog/scenarios/UX-0489-the-answer-key-asserts-a-ranking-with-no-margin.md) — [the answer key asserts a ranking with no margin, on a build it runs for real](docs/backlog/scenarios/UX-0489-the-answer-key-asserts-a-ranking-with-no-margin.md)
- [UX-512](docs/backlog/scenarios/UX-0512-an-exemption-for-a-build-artifact.md) — [a guard is red on any tree whose `__pycache__` was cleared](docs/backlog/scenarios/UX-0512-an-exemption-for-a-build-artifact.md)
- [UX-515](docs/backlog/scenarios/UX-0515-a-guard-that-ci-turns-red-by-adopting.md) — [a guard the reference-adopt commit turns red](docs/backlog/scenarios/UX-0515-a-guard-that-ci-turns-red-by-adopting.md)
- [UX-513](docs/backlog/scenarios/UX-0513-two-guards-are-red-until-you-commit.md) — [two guards are red while a tier edit is uncommitted](docs/backlog/scenarios/UX-0513-two-guards-are-red-until-you-commit.md)
- [UX-510](docs/backlog/scenarios/UX-0510-a-track-starts-from-a-stale-base.md) — [a parallel track starts from a base the orchestrator has left behind](docs/backlog/scenarios/UX-0510-a-track-starts-from-a-stale-base.md)
- [UX-523](docs/backlog/scenarios/UX-0523-forty-files-boot-the-same-page.md) — [forty files boot the same page](docs/backlog/scenarios/UX-0523-forty-files-boot-the-same-page.md)
- [UX-522](docs/backlog/scenarios/UX-0522-the-selector-runs-last-and-carries-the-census.md) — [the selector runs last, and carries the census](docs/backlog/scenarios/UX-0522-the-selector-runs-last-and-carries-the-census.md)
- [UX-524](docs/backlog/scenarios/UX-0524-the-touching-map-is-measured-in-ci.md) — [the touching map is measured in CI, not grepped](docs/backlog/scenarios/UX-0524-the-touching-map-is-measured-in-ci.md)
- [UX-526](docs/backlog/scenarios/UX-0526-the-large-budget-class-is-breached-at-its-top.md) — [the large budget class is measured at its bottom and breached at its top](docs/backlog/scenarios/UX-0526-the-large-budget-class-is-breached-at-its-top.md)
- [UX-538](docs/backlog/scenarios/UX-0538-a-ranking-guard-under-contention.md) — [a guard that ranks a real build's seconds cannot hold under load](docs/backlog/scenarios/UX-0538-a-ranking-guard-under-contention.md)
- [UX-537](docs/backlog/scenarios/UX-0537-forty-eight-documents-and-one-shim.md) — [forty-eight hand-built documents, and the shared shim they were to become](docs/backlog/scenarios/UX-0537-forty-eight-documents-and-one-shim.md)

**docs**

- [UX-331](docs/backlog/scenarios/UX-0331-the-readme-excerpt-and-the-sentence-that-contradicts-itself.md) — [the README excerpt, and the sentence that contradicts itself](docs/backlog/scenarios/UX-0331-the-readme-excerpt-and-the-sentence-that-contradicts-itself.md)
- [UX-330](docs/backlog/scenarios/UX-0330-the-stranger-needs-a-seed.md) — [the stranger needs a seed](docs/backlog/scenarios/UX-0330-the-stranger-needs-a-seed.md)
- [UX-353](docs/backlog/scenarios/UX-0353-the-roles-table-serves-a-contract-nothing-writes.md) — [the roles table serves a contract nothing writes](docs/backlog/scenarios/UX-0353-the-roles-table-serves-a-contract-nothing-writes.md)
- [UX-352](docs/backlog/scenarios/UX-0352-the-architecture-counts-seven-chapters-and-the-page-has-eight.md) — [the architecture counts seven chapters and the page has eight](docs/backlog/scenarios/UX-0352-the-architecture-counts-seven-chapters-and-the-page-has-eight.md)
- [UX-417](docs/backlog/scenarios/UX-0417-the-export-figures-are-four-rounds-stale.md) — [the guide's export figures are stale by 3.2x](docs/backlog/scenarios/UX-0417-the-export-figures-are-four-rounds-stale.md)
- [UX-416](docs/backlog/scenarios/UX-0416-the-page-moves-between-runs-and-no-document-says-so.md) — [the page moves between runs, and no document says so](docs/backlog/scenarios/UX-0416-the-page-moves-between-runs-and-no-document-says-so.md)
- [UX-425](docs/backlog/scenarios/UX-0425-the-proxy-instrument-class-is-in-no-rule-document.md) — [the defect class this repository hits most often is in no rule document](docs/backlog/scenarios/UX-0425-the-proxy-instrument-class-is-in-no-rule-document.md)
- [UX-426](docs/backlog/scenarios/UX-0426-ci-is-the-only-instrument-for-some-claims.md) — [the sessions' loop does not know that CI is sometimes the only instrument](docs/backlog/scenarios/UX-0426-ci-is-the-only-instrument-for-some-claims.md)
- [UX-446](docs/backlog/scenarios/UX-0446-a-third-ceiling-no-reader-facing-document-has.md) — [a third ceiling, and no reader-facing document has it](docs/backlog/scenarios/UX-0446-a-third-ceiling-no-reader-facing-document-has.md)
- [UX-447](docs/backlog/scenarios/UX-0447-the-reference-refresh-route-is-in-no-contributor-document.md) — [the reference-refresh route is in no contributor document](docs/backlog/scenarios/UX-0447-the-reference-refresh-route-is-in-no-contributor-document.md)
- [UX-468](docs/backlog/scenarios/UX-0468-the-guided-walk-against-a-planted-defect.md) — [no walk of the guides has ever started from a defect somebody planted](docs/backlog/scenarios/UX-0468-the-guided-walk-against-a-planted-defect.md)
- [UX-471](docs/backlog/scenarios/UX-0471-the-day-one-summary-counts-421-of-468.md) — [the day-one summary counts 421 task files and the tree has 468](docs/backlog/scenarios/UX-0471-the-day-one-summary-counts-421-of-468.md)
- [UX-472](docs/backlog/scenarios/UX-0472-the-architecture-has-no-paragraph-for-the-generators.md) — [the architecture says one script needs no `bst`, and now three tools do not fit the sentence](docs/backlog/scenarios/UX-0472-the-architecture-has-no-paragraph-for-the-generators.md)
- [UX-498](docs/backlog/scenarios/UX-0498-a-filing-is-decomposed-before-it-is-coded.md) — [a filing is decomposed before it is coded](docs/backlog/scenarios/UX-0498-a-filing-is-decomposed-before-it-is-coded.md)
- [UX-499](docs/backlog/scenarios/UX-0499-where-is-it-costs-one-line-not-one-file.md) — ["where is it" costs one line, not one file](docs/backlog/scenarios/UX-0499-where-is-it-costs-one-line-not-one-file.md)
- [UX-501](docs/backlog/scenarios/UX-0501-the-index-is-derived-not-merged.md) — [the index is derived, not merged](docs/backlog/scenarios/UX-0501-the-index-is-derived-not-merged.md)
- [UX-505](docs/backlog/scenarios/UX-0505-the-rules-card.md) — [the rules card — the guide's rules on one page, its reasons behind it](docs/backlog/scenarios/UX-0505-the-rules-card.md)
- [UX-506](docs/backlog/scenarios/UX-0506-the-outcome-skeleton-fits-the-register.md) — [the Outcome skeleton fits the register](docs/backlog/scenarios/UX-0506-the-outcome-skeleton-fits-the-register.md)
- [UX-502](docs/backlog/scenarios/UX-0502-the-comment-that-tells-the-story.md) — [the comment that tells the story](docs/backlog/scenarios/UX-0502-the-comment-that-tells-the-story.md)
- [UX-492](docs/backlog/scenarios/UX-0492-the-readme-verbatim-block-is-no-longer-verbatim.md) — [the README's "verbatim" real-project block prints a sentence the tool can no longer produce](docs/backlog/scenarios/UX-0492-the-readme-verbatim-block-is-no-longer-verbatim.md)
- [UX-493](docs/backlog/scenarios/UX-0493-a-moved-bound-left-an-earlier-task-file-asserting-the-old-one.md) — [a bound moved and the task file that presents it as current was not annotated](docs/backlog/scenarios/UX-0493-a-moved-bound-left-an-earlier-task-file-asserting-the-old-one.md)
- [UX-511](docs/backlog/scenarios/UX-0511-the-real-project-guide-teaches-a-retired-reading.md) — [the guide the README sends readers to teaches a retired reading as current](docs/backlog/scenarios/UX-0511-the-real-project-guide-teaches-a-retired-reading.md)
- [UX-507](docs/backlog/scenarios/UX-0507-the-unclassified-bucket.md) — [223 closed rows are in no topic](docs/backlog/scenarios/UX-0507-the-unclassified-bucket.md)
- [UX-516](docs/backlog/scenarios/UX-0516-the-ci-owners-page-teaches-a-command-that-exits-6.md) — [the CI owner's page teaches a command that exits 6 on this repository's own refs](docs/backlog/scenarios/UX-0516-the-ci-owners-page-teaches-a-command-that-exits-6.md)
- [UX-517](docs/backlog/scenarios/UX-0517-a-closed-outcome-quotes-a-bucket-that-is-now-empty.md) — [a closed Outcome quotes a bucket that is now empty](docs/backlog/scenarios/UX-0517-a-closed-outcome-quotes-a-bucket-that-is-now-empty.md)
- [UX-525](docs/backlog/scenarios/UX-0525-a-track-costs-tokens-and-nobody-knows-where.md) — [a track costs 81k-131k tokens, and nobody knows where](docs/backlog/scenarios/UX-0525-a-track-costs-tokens-and-nobody-knows-where.md)
- [UX-500](docs/backlog/scenarios/UX-0500-the-batch-gate-measured-against-the-per-item-suite.md) — [the batch gate, measured against the per-item suite](docs/backlog/scenarios/UX-0500-the-batch-gate-measured-against-the-per-item-suite.md)

<!-- /generated -->

## 0.3.0 — every document says what shape it is (2026-08-27)

Named for the rule it finally finishes. `UX-190` said it in round 19:
**every document `bga` writes carries a schema id, and the tool can
print that contract.** Four emitters had outgrown it since, and one of
them answered with a contract its own output did not satisfy.

`bga whatif`, `bga snapshot --list` and `bga snapshot --aggregate`
printed a `schema:` id and answered *"produces no versioned JSON
output"* when asked which — a refusal falsified by their own output
two lines up. `bga sweep` was worse: it printed `analyze/v2` for a
document carrying **zero of that contract's four required keys**. All
four answer now, `sweep/v1` is published, and the set of commands
exempted from the rule is empty.

The half that keeps it that way is structural rather than a second
list, because a list of enrolled commands is exactly what fell behind:
what is *emitted* (each command run over a fixture, the id read from
its own stdout), what is *answerable* (`--schema` really run), and
what is *written into a run directory* must union to the inventory
`bga.contracts` derives from the package. The next emitter either
answers, is declared, or reddens.

**Contract delta:** one new contract, `sweep/v1`, and five bumped —
`analyze/v3`, `compare/v2`, `blast/v2`, `correlate/v2` and `host/v2`
(`UX-341`), which makes the row `breaking` rather than `extending`.
`UX-345` removes one key from `analyze/v3` and renames another
(`signals.critical_path_length`, a duration published under a count's
declaration, and `signals.wall_clock_share` -> `wall_clock_share_us`);
both fold into the same unshipped `v3` rather than a fourth version,
since no release has ever written `v3`.
`UX-344` does **not** fold in: it removes the `signals` and
`structural` namespaces (every table they held is a top-level key,
`metrics` and `summary` renamed `graph_metrics` and `graph_summary`,
the six element-keyed maps grouped under `elements`), publishes
`provenance` once per claim instead of writing it into every finding,
the headline and each top action, and drops
`findings[].evidence.blast_radius`, a slice of a population published
in full beside it. That is `analyze/v4`, and `analyze/v3` joins the
read-never-written set. Measured on the two fixtures: leaves deeper
than three levels fell from 57% to 40% and from 67% to 53%, and the
golden report's deepest path from six levels to five.
The five predecessors stay in the set as **read, never written**: an
older store still analyzes, and `host/v1`'s `memory_mb` is converted
on the way in so an old baseline still compares rather than reading as
a different machine. No command or flag was added, renamed or removed.
Three existing contracts (`store/v1`, `store-aggregate/v1`,
`whatif/v1`) became printable by `--schema`, which changes what the
tool can *say* rather than what it writes.

**Upgrade note:** `bga sweep --format json` now emits a `schema` key
as the first key of its document. A parser that iterates keys or
rejects unknown ones will see it; one that reads the fields it wants
by name is unaffected. Nothing else in any document moved.

**Carried findings.** None from the reviews: all nine findings the
four architecture reviews filed (`UX-245`/`246`/`247`,
`UX-273`/`274`, `UX-294`/`295`, `UX-322`/`323`) are closed. Six
backlog rows are open at this release and named here so "we knew" is
on the record rather than in someone's memory — `UX-92` and `UX-96`
(long-running store items), `UX-330` and `UX-331` (docs), `UX-333`
(the capture name is the whole command) and `UX-337` (the two viewer
modules split along their seams).

```text state
digest: 2b0a95deffe4
contracts: analyze/v2 analyze/v3 analyze/v4 blast/v1 blast/v2 compare/v1 compare/v2 correlate/v1 correlate/v2 host/v1 host/v2 plane2/v1 plane2/v2 sources/v1 store-aggregate/v1 store/v1 sweep/v1 whatif/v1
commands: analyze baseline blast cache-logs cache-trend capture checkout-cost chrome-to-trace compare correlate cross-check diagnostics doctor extract floors gen-synthetic graph graph-from-show log-to-chrome native-to-chrome rebuild-set release-notes replay run-context snapshot sweep timeline utilisation view whatif wrap
```

### What landed

<!-- generated: UX-252 243→332 -->
89 scenarios closed (closed-row markers 243 → 332).

**contracts**

- [UX-259](docs/backlog/scenarios/UX-0259-a-blast-number-has-no-scale.md) — `753 downstream` is p99.9 in a 1,202-element graph and unremarkable in a graph of forty thousand — and the number is what travels into a ticket while the rank stays behind.
- [UX-253](docs/backlog/scenarios/UX-0253-the-aggregate-mixes-contract-sets-without-saying-so.md) — `UX-250` settled the two-run rule and its clause 2 asked for the many-run case, which was deliberately not implemented: with thirty runs there can be three contract sets and the questions that follow…
- [UX-260](docs/backlog/scenarios/UX-0260-the-other-quantities-that-need-a-scale.md) — Where else a percentile belongs, argued per quantity rather than applied everywhere - `UX-259` gave blast radius a scale and the same question stood for duration, sandbox tax and process count
- [UX-288](docs/backlog/scenarios/UX-0288-the-contract-publishes-membership-three-ways.md) — `analyze/v1` published the same leaf membership three times and the same critical path twice, each a subset of the one element table, and no guard said the copies must agree
- [UX-291](docs/backlog/scenarios/UX-0291-a-finding-carries-its-numbers-three-times.md) — twenty-three numbers across nine findings, ten carried a second time in `provenance.evidence[].value` and twenty a third time in `copy_text` - with no rule saying they must agree
- [UX-275](docs/backlog/scenarios/UX-0275-the-capacity-recommendation-is-text-only.md) — the tool's answer to the question this backlog opened with - what should `--builders` be, and which constraint is the reason - was computed, rendered by the text report, and dropped by the JSON…
- [UX-290](docs/backlog/scenarios/UX-0290-the-schema-does-not-describe-its-tuples.md) — `[["app.bst", 8], …]` was described by nothing, so the page named its columns after their *position* - 78 of the report's headers named a place in a data structure rather than a measure
- [UX-328](docs/backlog/scenarios/UX-0328-schema-answers-for-everything-that-emits-one.md) — [--schema answers for everything that emits one](docs/backlog/scenarios/UX-0328-schema-answers-for-everything-that-emits-one.md)
- [UX-339](docs/backlog/scenarios/UX-0339-the-capacity-sweep-has-no-contract.md) — [the capacity sweep has no contract](docs/backlog/scenarios/UX-0339-the-capacity-sweep-has-no-contract.md)

**cli**

- [UX-326](docs/backlog/scenarios/UX-0326-the-tools-own-sentences-are-contracts.md) — the "Next:" block printed `bga snapshot /abs/path/to/project`, which crashed when run verbatim, and `bga compare @prev @last` printed "(--allow-mismatch was given)" with no flags passed

**analysis**

- [UX-258](docs/backlog/scenarios/UX-0258-the-blast-ranking-tells-you-to-optimize-the-base-image.md) — The blast ranking put `toolchain.bst` first — an `import` element with 1,201 dependents, `is_structural_kind: true` on the very entry the ranking ordered.
- [UX-329](docs/backlog/scenarios/UX-0329-the-terminal-and-the-viewer-disagree-about-plane-2.md) — [the terminal and the viewer disagree about Plane 2](docs/backlog/scenarios/UX-0329-the-terminal-and-the-viewer-disagree-about-plane-2.md)

**capture**

- [UX-313](docs/backlog/scenarios/UX-0313-the-record-list-is-the-floor-that-is-left.md) — `UX-297` left the record list as extraction's floor - 185.8 MB of a 221.1 MB peak on a 200,000-process trace - and asked whether a bounded reorder window could replace it, making extraction…
- [UX-324](docs/backlog/scenarios/UX-0324-a-capture-that-cannot-start-says-so-and-leaves-nothing.md) — on a machine without `bst`, `bga snapshot -- bst build all.bst` - the README's own first command - died in a 32-line `FileNotFoundError` traceback and left a debris snapshot behind, while `bga…
- [UX-297](docs/backlog/scenarios/UX-0297-extraction-streams-and-the-monolith-retires.md) — `summarize()` embedded the whole per-process record list in plane2.json - ~95% of a 1.5 GB monolith that no production reader consumed - and extraction then held the whole event list in RAM to…
- [UX-308](docs/backlog/scenarios/UX-0308-a-slice-that-says-what-bga-knows-about-it.md) — a slice said one thing - its name - and for Plane 2 that name is the command truncated to 120 characters, so the argv tail that tells two compiler invocations apart was not in the trace at all, while…
- [UX-310](docs/backlog/scenarios/UX-0310-the-counters-the-reserved-constant-was-waiting-for.md) — UX-298 pinned TYPE_COUNTER with the comment "reserved rather than used", and the three series the capture could fold went undrawn
- [UX-311](docs/backlog/scenarios/UX-0311-a-trace-that-knows-whose-build-it-was.md) — a trace file leaves the machine that made it and carried no identity at all - not which run, not which host, not whether the capture was complete - while the lane order was discovery order
- [UX-309](docs/backlog/scenarios/UX-0309-the-arrows-that-answer-why-now.md) — the dependency question is the one a timeline is *for* - an element ends, another begins, and whether that adjacency is causation is exactly what graph.json knows and the trace did not say;
- [UX-298](docs/backlog/scenarios/UX-0298-the-timeline-speaks-perfetto-natively.md) — the timeline was legacy Chrome JSON - a shape Perfetto tolerates rather than reads - assembled whole in memory and regenerated from the raw log on every handoff;

**viewer**

- [UX-254](docs/backlog/scenarios/UX-0254-the-contents-take-two-thirds-of-the-first-screen.md) — Reported from a real run: the contents occupy most of the first screen and read as content.
- [UX-255](docs/backlog/scenarios/UX-0255-the-heading-is-below-the-navigation.md) — The heading arrived at y=630, *after* the navigation, and carried less than the footer did - two lines of identity and nothing that qualifies the run
- [UX-262](docs/backlog/scenarios/UX-0262-a-long-critical-path-grows-a-section-without-bound.md) — `UX-187` capped the tables that grow with element count;
- [UX-263](docs/backlog/scenarios/UX-0263-the-pages-own-policy-refuses-its-drawings.md) — Reported from a real project: Chrome logs "Refused to apply inline style ...
- [UX-265](docs/backlog/scenarios/UX-0265-the-handoff-answers-the-read-but-not-the-preflight.md) — Reported from a real project: the Perfetto hand-off stopped working in latest Chrome, with "blocked by cors policy, no access control allow origin header is present on the requested resource"
- [UX-261](docs/backlog/scenarios/UX-0261-the-first-view-ranks-what-is-big.md) — The first screen met the reader with eleven near-identical blast counts;
- [UX-266](docs/backlog/scenarios/UX-0266-two-of-three-pages-run-nothing.md) — Reported from a real run: a CSP problem on `sql.html`.
- [UX-267](docs/backlog/scenarios/UX-0267-every-object-is-a-details-called-object.md) — Every object *and every array* rendered as `<details><summary>object</summary><pre>{raw JSON}</pre>` - 34 such cells and 32,393 characters of `<pre>` on a 44-element run, the largest 8,191 and…
- [UX-268](docs/backlog/scenarios/UX-0268-six-maps-are-one-table.md) — Six of the seven wide `signals` maps are the same element list rendered six times;
- [UX-269](docs/backlog/scenarios/UX-0269-a-long-field-shows-all-of-itself.md) — Field contents measured per field: 678 chars of `copy_text`, 572 of `capacity_model_note`, 293 of `attribution_hints.resource_wait_us` - all shown in full, always
- [UX-270](docs/backlog/scenarios/UX-0270-the-critical-path-is-its-own-section.md) — The critical path - the run's most important list - was a row inside a section named after a schema key
- [UX-271](docs/backlog/scenarios/UX-0271-the-rail-is-flat.md) — The rail is one flat list and the report renders 30+ sections;
- [UX-272](docs/backlog/scenarios/UX-0272-the-header-is-four-stacked-paragraphs.md) — The header stacks four block elements and was reported as too long
- [UX-277](docs/backlog/scenarios/UX-0277-every-table-cell-stringifies-its-own-structure.md) — `UX-267`'s width-not-depth rule was wired into `renderPairs` (which draws `<dd>` cells) and never into `buildTable` (which draws every `<td>`), so 6 cells rendered raw JSON, 11 joined arrays, one…
- [UX-289](docs/backlog/scenarios/UX-0289-one-element-table-many-presets.md) — the page drew 19 element tables over 13 populations and the one table every element is in carried 13 columns, because it served every question at once - and it had bounds and filters but **zero named…
- [UX-292](docs/backlog/scenarios/UX-0292-thirteen-tables-share-one-view-state-key.md) — `UX-211` keys a table's view state by the table's name and `renderStructured` named every nested table `value`, so thirteen tables answered to `f.value` - a filter typed into one landed, on the other…
- [UX-278](docs/backlog/scenarios/UX-0278-the-magnifier-opens-nothing-for-most-elements.md) — a magnifier that consumes the click and does nothing: the detail cap excluded 1,178 of 1,202 elements, so the affordance was absent for 98% of the run and dead where it was present
- [UX-279](docs/backlog/scenarios/UX-0279-forty-three-copy-controls-and-no-way-to-know-what-they-copy.md) — 43 copy controls, three vocabularies, `Copy` fourteen times over two different payloads, and not one `title` among them
- [UX-280](docs/backlog/scenarios/UX-0280-copy-as-markdown.md) — JSON pastes into a ticket as a code block somebody has to read
- [UX-284](docs/backlog/scenarios/UX-0284-the-table-tools-are-below-the-table-and-scroll-away.md) — the table tools sat below their table and scrolled away: 28 of 43 inputs started below the table they belong to, all 43 were `position: static`, and the jump box was at y=1236 on a page whose fold is…
- [UX-281](docs/backlog/scenarios/UX-0281-the-satellite-pages-are-dead-ends.md) — both satellite pages were dead ends;
- [UX-282](docs/backlog/scenarios/UX-0282-the-perfetto-fallback-is-below-the-button-that-fails.md) — *"Nothing opened? Use the direct link"* sat three paragraphs under the button it is about, read only by somebody who has just watched that button fail
- [UX-283](docs/backlog/scenarios/UX-0283-the-bottleneck-view-names-elements-you-cannot-reach.md) — the bottleneck block rendered all seven of its members and carried **zero** links out of the entire `structural` section - nine choke points, none clickable
- [UX-286](docs/backlog/scenarios/UX-0286-the-report-is-forty-eight-fragments-with-no-chapters.md) — forty-eight sections averaging 0.24 screens with nothing grouping them: a report read by scrolling past fragments, and a rail of thirty-one top-level entries
- [UX-285](docs/backlog/scenarios/UX-0285-the-identity-blocks-are-split-and-the-blast-box-is-last.md) — three identity blocks answering one question, split across the page - `summary` and `run_instance` at screens 1.4 and 1.6, `producer` at 10.9 of 18.8 - and the blast control, an interactive query, as…
- [UX-296](docs/backlog/scenarios/UX-0296-the-view-that-parses-nothing.md) — `bga view` on a real ~2 GB dual-plane snapshot froze in parsing and died of memory near server start: `serve()` built every payload before the socket existed, running every whole-file load path in…
- [UX-312](docs/backlog/scenarios/UX-0312-questions-for-the-trace-that-can-finally-answer-them.md) — the canned SQL library was track-scoped by `UX-210` and arg-scoped by `UX-204`, both against the legacy Chrome JSON trace;
- [UX-314](docs/backlog/scenarios/UX-0314-the-deep-link-perfetto-refuses-to-follow.md) — the `?url=` deep link was refused by ui.perfetto.dev's own `connect-src` on every port `bga view` binds, so the handoff that `UX-299` made the only transport above 4 MiB failed silently in the field
- [UX-316](docs/backlog/scenarios/UX-0316-exhibits-drawn-at-annotation-size.md) — every drawing shared one geometry - `SPARK_HEIGHT = 20` / `STRIP_HEIGHT = 8`, calibrated for the sparkline beside a table cell - so the three drawings that are their section's whole answer drew at…
- [UX-318](docs/backlog/scenarios/UX-0318-the-rabbit-hole-announces-its-depth.md) — a fold said how *wide* it was and nothing about how deep, and a nested table's own scroll sat inside a scrolling parent - so the reader could neither see the rabbit hole's depth nor reach all the…
- [UX-317](docs/backlog/scenarios/UX-0317-apparatus-in-its-place.md) — the save-the-trace sentence rendered in the sticky header, two blocks above the control it explains and paid for on every screen;
- [UX-319](docs/backlog/scenarios/UX-0319-the-chain-folds-and-the-clicks-are-counted.md) — the critical chain's element listing rendered whole - `UX-187` had folded the text report's chain and `UX-196` the drawn strip, and the third surface got neither - and nobody had ever measured what…
- [UX-321](docs/backlog/scenarios/UX-0321-the-question-that-can-never-answer.md) — `element-commands` filtered Plane 2 slices on `debug.element`, a key only Plane 1 carried, so it returned zero rows on every trace this emitter can write - silently, and the dictionary guard could…
- [UX-320](docs/backlog/scenarios/UX-0320-the-page-conforms-to-its-new-sections.md) — round 44 extended the visual contract with four sections, and the `UX-305` precedent says an extension is not real until the existing page is audited against it and the audit is a guard
- [UX-315](docs/backlog/scenarios/UX-0315-the-canned-why-renders-with-doubled-spaces.md) — every canned question's `why` renders with doubled spaces: the library concatenates each `why` across source lines and the file's convention began every continuation with a space while the previous…
- [UX-307](docs/backlog/scenarios/UX-0307-the-export-ships-the-source-comments.md) — the export inlines every viewer module and this project's modules are commented by design, so the argument for each rule was believed to ride into every attachment - 175 KB of a 196 KB page
- [UX-299](docs/backlog/scenarios/UX-0299-a-handoff-that-does-not-carry-the-trace-in-its-hands.md) — the tab-to-tab handoff fetches the whole trace into the report page, posts it to Perfetto's window and was measured at 25 KB - and it is the same design at 1.5 GB, where the browser tab meets the…
- [UX-305](docs/backlog/scenarios/UX-0305-emphasis-is-a-budget.md) — styleguide §4 budgets emphasis - one emphasized element per block, one accent, text in ink never in status tone - and the page had grown section by section without ever being read against it
- [UX-303](docs/backlog/scenarios/UX-0303-the-shape-before-the-rows.md) — styleguide §2 asks that a value which *is* a shape draws as its shape first;
- [UX-304](docs/backlog/scenarios/UX-0304-dark-first-with-two-grades-of-token.md) — the page was authored light-first with a dark media override and the reader it was built for reads dark;
- [UX-302](docs/backlog/scenarios/UX-0302-the-mapping-made-law.md) — round 41's style guide made §1 a dispatch table on paper;
- [UX-301](docs/backlog/scenarios/UX-0301-the-ordering-authority-moved-and-left-its-old-uniform.md) — round 40 ran `UX-235`'s own acceptance mutation - `root.prepend(decision)` to `append` - and the booted page did not change: `UX-286`'s chapter pass had become the ordering authority, leaving five…
- [UX-334](docs/backlog/scenarios/UX-0334-a-console-the-page-keeps-clean.md) — [a console the page keeps clean](docs/backlog/scenarios/UX-0334-a-console-the-page-keeps-clean.md)
- [UX-335](docs/backlog/scenarios/UX-0335-reading-start-time-of-undefined.md) — [reading 'start_time' of undefined](docs/backlog/scenarios/UX-0335-reading-start-time-of-undefined.md)
- [UX-338](docs/backlog/scenarios/UX-0338-the-page-draws-the-element-population-twice.md) — [the page draws the element population twice](docs/backlog/scenarios/UX-0338-the-page-draws-the-element-population-twice.md)

**store**

- [UX-325](docs/backlog/scenarios/UX-0325-aggregate-crashes-on-every-user-install.md) — `bga snapshot --aggregate` - named in `docs/README.md` as one of the commands to know - died with `ModuleNotFoundError: No module named 'tools'` on every plain `pip install`, so the feature had never…
- [UX-300](docs/backlog/scenarios/UX-0300-what-a-two-gigabyte-snapshot-does-to-a-store.md) — one field snapshot reached ~2 GB and the store's retention thinking dated from kilobyte captures: the raw log kept by default on an 8-12% measurement, pruning that thinks in age and count, and…

**guards**

- [UX-256](docs/backlog/scenarios/UX-0256-the-default-open-state-is-a-policy-nobody-checks.md) — "A checker if everything is really collapsed by default".
- [UX-257](docs/backlog/scenarios/UX-0257-nothing-reads-the-pages-geometry.md) — Every geometric claim about the viewer - "nothing overlaps", "the first content is above the fold" - was measured by hand and then held by nothing, because the shim the guards run on has no layout…
- [UX-264](docs/backlog/scenarios/UX-0264-the-dom-shim-is-copied-twenty-five-times.md) — The DOM shim every viewer guard runs on was written inline **25 times**, so each of three fidelity defects had to be found in the page and then fixed twenty-five times - and `UX-263`'s seven-file fix…
- [UX-274](docs/backlog/scenarios/UX-0274-the-context-map-is-guarded-on-one-half-of-the-tree.md) — the context map's guard globbed `bga/` and `tools/` only, so the `tests/` half had drifted to 5 of 12 entries with every figure stale
- [UX-276](docs/backlog/scenarios/UX-0276-a-guard-can-rest-on-a-path-no-clone-has.md) — round 37's two new guards rested on a `bga snapshot` store that is ignored by design, so they passed on one machine and failed CI on all four Python versions before an assertion ran
- [UX-293](docs/backlog/scenarios/UX-0293-a-ci-check-pins-a-contract-version.md) — `UX-288` moved `analyze/v1` to `analyze/v2` on purpose, the suite was green at 3463 passed and `make lint` clean - and CI went red on a packaging smoke test that pinned the contract literally, in the…
- [UX-287](docs/backlog/scenarios/UX-0287-the-export-ceiling-is-measured-on-a-four-element-run.md) — the export's byte ceiling was asserted against a **four-element** run, so it bounded the one quantity that barely varies while the content that drives the size went unwatched - the committed…
- [UX-336](docs/backlog/scenarios/UX-0336-the-loop-that-got-slow.md) — [the loop that got slow, measured and re-tooled](docs/backlog/scenarios/UX-0336-the-loop-that-got-slow.md)
- [UX-332](docs/backlog/scenarios/UX-0332-the-cascade-beats-the-first-match.md) — [the cascade beats the first match, and two record nits](docs/backlog/scenarios/UX-0332-the-cascade-beats-the-first-match.md)

**docs**

- [UX-242](docs/backlog/scenarios/UX-0242-the-capacity-recommendation-is-documented-nowhere.md) — `bga analyze` computes `capacity_recommendation` and no instructional document named it;
- [UX-243](docs/backlog/scenarios/UX-0243-the-memory-envelope-reaches-no-reader.md) — `memory_envelope` decides whether `--builders` can go up and reached no reader;
- [UX-244](docs/backlog/scenarios/UX-0244-whatifs-convention-lives-in-its-own-docstring.md) — `bga whatif` publishes a projected makespan and what "fixed" means lived only in `whatif.py`'s `CONVENTION`
- [UX-245](docs/backlog/scenarios/UX-0245-the-architectures-cli-table-is-two-commands-behind.md) — the chapter titled "Real current CLI surface" was missing `bga blast` (ten rounds shipped) and `bga whatif`, and named `--explain` nowhere
- [UX-246](docs/backlog/scenarios/UX-0246-the-journey-guide-never-reaches-whatif.md) — the end-to-end journey walks capture → read → go inside → join → act → gate and named `bga whatif` nowhere in the act step
- [UX-273](docs/backlog/scenarios/UX-0273-the-rule-that-draws-a-nested-value-lives-in-one-task-file.md) — the width-not-depth rule governs every nested value in the report and `git grep` found it in exactly one task file
- [UX-247](docs/backlog/scenarios/UX-0247-the-architectures-verification-log-is-stale-about-itself.md) — a document's claim about its own currency, false: the Verification Log said 2026-08-18 while five commits had touched the file since
- [UX-322](docs/backlog/scenarios/UX-0322-the-cli-table-has-lost-the-viewer.md) — the architecture's command table had 18 rows against a tool with 31 commands, and the two a reader looks for first - `bga view`, the entry point for the whole viewer axis, and `bga timeline` - were…
- [UX-323](docs/backlog/scenarios/UX-0323-round-41s-audit-still-asserts-what-round-44-falsified.md) — `docs/audits/round-41.md` still asserted that "175 KB of the 196 KB page is commented JavaScript, because `--export` inlines modules verbatim" - the claim `UX-320` falsified and `UX-307` measured out…
- [UX-327](docs/backlog/scenarios/UX-0327-four-documented-invocations-that-do-not-exist.md) — the guides printed `bga` invocations the tool refuses, and the docs guard checked command *names* only - flags, subcommands and positional meaning were never checked
- [UX-294](docs/backlog/scenarios/UX-0294-eleven-viewer-modules-are-named-in-no-document.md) — review 3 found the viewer's fifteen ES modules named a handful of times in the architecture - `views.js` at 2,400 lines, `nav.js`, and `viewstate.js` at **zero** - so a reader opening `bga/viewer/`…
- [UX-295](docs/backlog/scenarios/UX-0295-whatif-v1-is-in-no-guide.md) — review 3 counted contract homes and found `whatif/v1` named four times across the spec, the architecture and a direction, and **zero** times in `docs/guides/` - the command documented, the document…
- [UX-306](docs/backlog/scenarios/UX-0306-the-guide-joins-the-tree.md) — round 41 wrote the web report's visual contract and left it beside the tree it governs;

<!-- /generated -->

## 0.2.0 — the build that says what it is (2026-08-24)

The first recorded release, and it is named for what it adds rather
than for what it fixes: **an artifact now says which build produced
it.**

`bga` reads its own past output as input — `@last`/`@prev`, the
baseline set, `cache-trend`, `store-aggregate` all open artifacts
written by whatever `bga` was installed at the time. Until this
release, nothing in those artifacts said which build that was:
`__version__` was read in two places, both the `--version` string, and
written into nothing. A run directory from the first week and one from
last week were indistinguishable to the tool reading them both.

**Contract delta:** none. All nine contracts stay at `v1`, and no
command or flag was added, renamed or removed. The version moves
because `0.1.0` had never moved and therefore could not signal that
anything had — and because from here the number is derived from this
recorded state rather than chosen.

**Upgrade note:** none required. Artifacts written by older builds
carry no producer stamp, and that absence reads as `unstamped` — an
explicit unknown, never as agreement. Nothing is rewritten, and no
comparison behaves differently yet; `UX-250` is where the recorded
stamp starts deciding anything.

**Carried findings.** `UX-241`'s first review filed three, all still
open and all documentation: the architecture's CLI table is two
subcommands behind (`UX-245`), the end-to-end guide never reaches
`bga whatif` (`UX-246`), and the architecture's own Verification Log is
stale about its currency (`UX-247`). They are named here rather than
left in the backlog alone, so "we knew" is on the record.

```text state
digest: 5a67b03d07ac
contracts: analyze/v2 blast/v1 compare/v1 correlate/v1 host/v1 plane2/v1 plane2/v2 sources/v1 store-aggregate/v1 store/v1 whatif/v1
commands: analyze baseline blast cache-logs cache-trend capture checkout-cost chrome-to-trace compare correlate cross-check diagnostics doctor extract floors gen-synthetic graph graph-from-show log-to-chrome native-to-chrome rebuild-set release-notes replay run-context snapshot sweep timeline utilisation view whatif wrap
```

### What landed

<!-- generated: UX-252 238→243 -->
5 scenarios closed (closed-row markers 238 → 243).

**contracts**

- [UX-248](docs/backlog/scenarios/UX-0248-there-is-no-authoritative-contract-inventory.md) — `schemas.names()` answers a narrower question than it looks like it does - the documents `bga --schema` can print, not the documents `bga` writes.
- [UX-249](docs/backlog/scenarios/UX-0249-nothing-an-artifact-records-says-which-bga-wrote-it.md) — `bga` reads its own past output as input, and nothing an artifact recorded said which build wrote it.
- [UX-250](docs/backlog/scenarios/UX-0250-comparison-refuses-on-host-and-mode-but-not-on-contract-movement.md) — `bga compare` refuses on host and on cache mode, with an exit code of its own, and had nothing to say about the two runs having been measured by different builds of the tool

**docs**

- [UX-251](docs/backlog/scenarios/UX-0251-a-release-is-a-contract-state-not-a-date.md) — `bga --version` said `0.1.0`, unmoved across 29 rounds and 247 scenarios;
- [UX-252](docs/backlog/scenarios/UX-0252-the-release-notes-should-be-generated-from-the-closed-rows.md) — Hand-writing release notes would make a third copy of facts that already live in the task file's Outcome and the closed row - and two hand-maintained copies of one fact drifting is this repository's…

<!-- /generated -->

Rows 1–238 predate recorded releases: they landed across twenty-nine
rounds under a version that never moved, which is the thing this
release fixes. Their history is
[`docs/backlog/scenarios/closed.md`](docs/backlog/scenarios/closed.md)
and each task file's Outcome, and reprinting 238 of them here would be
a copy of that file rather than a changelog.
