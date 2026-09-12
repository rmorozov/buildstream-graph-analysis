# Changelog

What changed between the `bga` you installed and the one you have now.

A release here records a **contract state**, not a date: the
twenty-five published contracts and the command surface as they stood, plus what
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
  is a new row, not an edit to that one.

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
contracts: analyze/v2 analyze/v3 analyze/v4 analyze/v5 analyze/v6 blast/v1 blast/v2 bundle-manifest/v1 capacity-model/v1 capture-layout/v1 compare/v1 compare/v2 correlate/v1 correlate/v2 host-samples/v1 host/v1 host/v2 plane2/v1 plane2/v2 plane2/v3 sources/v1 store-aggregate/v1 store/v1 sweep/v1 whatif/v1
commands: analyze baseline blast bundle cache-logs cache-trend capture checkout-cost chrome-to-trace compare correlate cross-check diagnostics doctor extract floors gen-synthetic graph graph-from-show log-to-chrome native-to-chrome rebuild-set release-notes replay run-context snapshot sweep timeline utilisation view whatif wrap
```

### What landed

<!-- generated: UX-252 537→813 -->
276 scenarios closed (closed-row markers 537 → 813).

**contracts**

- [UX-553](UX-0553-the-holder-set-is-mandated-and-unread.md) — [the resource-holder set is spec-mandated and reaches no reader](UX-0553-the-holder-set-is-mandated-and-unread.md)
- [UX-540](UX-0540-the-three-contracts-bga-reads-and-never-registers.md) — [the three contracts `bga` reads and never registers](UX-0540-the-three-contracts-bga-reads-and-never-registers.md)
- [UX-550](UX-0550-the-newest-release-row-records-the-state-now.md) — [the newest release row records the state *now*, not the one it shipped](UX-0550-the-newest-release-row-records-the-state-now.md)
- [UX-602](UX-0602-two-hard-gates-are-published-and-named-nowhere.md) — [two hard gates are published and named nowhere](UX-0602-two-hard-gates-are-published-and-named-nowhere.md)
- [UX-598](UX-0598-two-of-the-four-percentile-rows-publish-no-distribution.md) — [two of the four percentile rows publish no distribution](UX-0598-two-of-the-four-percentile-rows-publish-no-distribution.md)
- [UX-610](UX-0610-the-verdict-record-is-not-a-published-key.md) — [the verdict record is not a published key](UX-0610-the-verdict-record-is-not-a-published-key.md)
- [UX-613](UX-0613-the-capacity-model-emits-no-document.md) — [the capacity model emits no document](UX-0613-the-capacity-model-emits-no-document.md)
- [UX-628](UX-0628-five-published-keys-no-document-names.md) — [five published keys no document names](UX-0628-five-published-keys-no-document-names.md)
- [UX-629](UX-0629-a-required-set-grew-under-an-unchanged-id.md) — [a required set grew under an unchanged id](UX-0629-a-required-set-grew-under-an-unchanged-id.md)
- [UX-637](UX-0637-a-shallow-clone-answers-and-does-not-say-so.md) — [a shallow clone answers, and does not say so](UX-0637-a-shallow-clone-answers-and-does-not-say-so.md)
- [UX-659](UX-0659-two-superseded-ids-sit-on-a-live-line.md) — [two superseded ids sit on a live line of the spec's registry](UX-0659-two-superseded-ids-sit-on-a-live-line.md)

**cli**

- [UX-574](UX-0574-invalid-arguments-exit-2-which-the-table-gives-to-ingestion.md) — ["invalid arguments" exit 2, which the table gives to ingestion](UX-0574-invalid-arguments-exit-2-which-the-table-gives-to-ingestion.md)
- [UX-575](UX-0575-a-documented-pipe-prints-a-traceback.md) — [a documented pipe prints a traceback](UX-0575-a-documented-pipe-prints-a-traceback.md)
- [UX-725](UX-0725-view-export-prints-two-error-lines-and-exits-zero.md) — [`bga view --export` prints two ERROR lines and exits 0](UX-0725-view-export-prints-two-error-lines-and-exits-zero.md)

**analysis**

- [UX-541](UX-0541-the-gap-sweep-is-cut-but-still-quadratic.md) — [the gap sweep is cut and still quadratic, and the reason is a contract](UX-0541-the-gap-sweep-is-cut-but-still-quadratic.md)
- [UX-542](UX-0542-diagnostics-is-now-the-largest-phase.md) — [`_compute_diagnostics` is now the largest phase of `analyze`](UX-0542-diagnostics-is-now-the-largest-phase.md)
- [UX-563](UX-0563-part-8-2-s-unknown-holder-is-a-state-the-code-cannot-reach.md) — [Part 8.2's `UNKNOWN` holder is a state the code cannot reach](UX-0563-part-8-2-s-unknown-holder-is-a-state-the-code-cannot-reach.md)
- [UX-564](UX-0564-parts-23-and-27-exist-in-the-spec-and-nowhere-else.md) — [Parts 23 and 27 exist in the spec and nowhere else](UX-0564-parts-23-and-27-exist-in-the-spec-and-nowhere-else.md)
- [UX-565](UX-0565-part-29-is-wired-to-none-while-the-store-holds-the-series-it-needs.md) — [Part 29 is wired to `None` while the store holds the series it needs](UX-0565-part-29-is-wired-to-none-while-the-store-holds-the-series-it-needs.md)
- [UX-593](UX-0593-the-regression-verdict-carries-no-evidence-chain.md) — [the regression verdict carries no evidence chain](UX-0593-the-regression-verdict-carries-no-evidence-chain.md)
- [UX-596](UX-0596-build-time-in-the-team-s-units.md) — [build time in the team's units](UX-0596-build-time-in-the-team-s-units.md)
- [UX-611](UX-0611-whatifs-saving-is-still-in-build-seconds.md) — [what-if's saving is still in build seconds](UX-0611-whatifs-saving-is-still-in-build-seconds.md)
- [UX-641](UX-0641-the-levels-key-is-the-identity-function.md) — [the levels key is the identity function](UX-0641-the-levels-key-is-the-identity-function.md)
- [UX-676](UX-0676-the-utilization-envelope-and-the-intervals-that-violate-it.md) — [the utilization envelope, and the intervals that violate it](UX-0676-the-utilization-envelope-and-the-intervals-that-violate-it.md)
- [UX-681](UX-0681-fan-in-what-an-element-depends-on-ranked.md) — [fan-in — what an element depends on, ranked](UX-0681-fan-in-what-an-element-depends-on-ranked.md)
- [UX-724](UX-0724-the-diagnostics-blocks-vanish-on-a-fully-cached-run.md) — [the diagnostics blocks vanish on a fully cached run](UX-0724-the-diagnostics-blocks-vanish-on-a-fully-cached-run.md)
- [UX-719](UX-0719-the-bottleneck-fan-in-and-fan-out-labels-are-swapped.md) — [the bottleneck fan-in and fan-out labels are swapped](UX-0719-the-bottleneck-fan-in-and-fan-out-labels-are-swapped.md)
- [UX-733](UX-0733-the-two-fan-averages-are-the-same-number-and-both-described-wrong.md) — [the two fan averages are the same number, and both described wrong](UX-0733-the-two-fan-averages-are-the-same-number-and-both-described-wrong.md)
- [UX-677](UX-0677-the-max-jobs-advisor-per-element-under-a-no-overcommit-constraint.md) — [the max-jobs advisor — per element, under a no-overcommit constraint](UX-0677-the-max-jobs-advisor-per-element-under-a-no-overcommit-constraint.md)
- [UX-740](UX-0740-a-span-under-the-epsilon-grid-becomes-a-zero-width-segment-and-nothing-says-so.md) — [a span under the epsilon grid becomes a zero-width segment, and nothing says so](UX-0740-a-span-under-the-epsilon-grid-becomes-a-zero-width-segment-and-nothing-says-so.md)
- [UX-682](UX-0682-change-frequency-and-co-change-from-the-logs-the-project-already-keeps.md) — [change frequency and co-change, from the logs the project already keeps](UX-0682-change-frequency-and-co-change-from-the-logs-the-project-already-keeps.md)
- [UX-683](UX-0683-the-foundation-tier-is-declared-and-the-kind-based-exemption-misses-it.md) — [the foundation tier is declared, and the kind-based exemption misses it](UX-0683-the-foundation-tier-is-declared-and-the-kind-based-exemption-misses-it.md)
- [UX-678](UX-0678-memory-joins-the-sweep-and-the-queue-model.md) — [memory joins the sweep and the queue model](UX-0678-memory-joins-the-sweep-and-the-queue-model.md)
- [UX-684](UX-0684-the-cached-build-verdict-does-the-graph-rebuild-the-cheapest-subgraph.md) — [the cached-build verdict — does the graph rebuild the cheapest subgraph?](UX-0684-the-cached-build-verdict-does-the-graph-rebuild-the-cheapest-subgraph.md)
- [UX-680](UX-0680-remote-execution-is-priced-not-built.md) — [remote execution is priced, not built](UX-0680-remote-execution-is-priced-not-built.md)
- [UX-808](UX-0808-the-max-jobs-advice-lists-one-row-per-task-not-per-element.md) — [the max-jobs advice lists one row per task, not per element](UX-0808-the-max-jobs-advice-lists-one-row-per-task-not-per-element.md)
- [UX-739](UX-0739-the-max-jobs-advice-is-not-priced-nothing-says-what-the-build-drops-to.md) — [the max-jobs advice is not priced — nothing says what the build drops to](UX-0739-the-max-jobs-advice-is-not-priced-nothing-says-what-the-build-drops-to.md)
- [UX-809](UX-0809-the-price-s-two-assumptions-are-on-the-payload-not-in-the-text.md) — [the price's two assumptions are on the payload, not in the text](UX-0809-the-price-s-two-assumptions-are-on-the-payload-not-in-the-text.md)

**capture**

- [UX-594](UX-0594-a-capture-cannot-say-when-the-build-was-requested.md) — [a capture cannot say when the build was requested](UX-0594-a-capture-cannot-say-when-the-build-was-requested.md)
- [UX-612](UX-0612-the-start-clock-has-no-provenance.md) — [the start clock has no provenance](UX-0612-the-start-clock-has-no-provenance.md)
- [UX-675](UX-0675-the-host-series-has-memory-and-no-cores.md) — [the host series has memory and no cores](UX-0675-the-host-series-has-memory-and-no-cores.md)
- [UX-726](UX-0726-no-flag-omits-plane-2-and-the-empty-one-says-nothing.md) — [no flag omits Plane 2, and the empty one says nothing](UX-0726-no-flag-omits-plane-2-and-the-empty-one-says-nothing.md)
- [UX-738](UX-0738-a-build-that-could-not-write-reports-as-a-clean-run-and-exit-255.md) — [a build that could not write reports as a clean run and exit 255](UX-0738-a-build-that-could-not-write-reports-as-a-clean-run-and-exit-255.md)
- [UX-805](UX-0805-the-doctor-s-chain-probe-drops-the-user-s-cache-config-with-its-home.md) — [the doctor's chain probe drops the user's cache config with its HOME](UX-0805-the-doctor-s-chain-probe-drops-the-user-s-cache-config-with-its-home.md)
- [UX-679](UX-0679-a-jobserver-every-sandbox-joins-the-prototype-bga-can-run.md) — [a jobserver every sandbox joins — the prototype bga can run](UX-0679-a-jobserver-every-sandbox-joins-the-prototype-bga-can-run.md)

**viewer**

- [UX-545](UX-0545-a-refused-timeline-says-the-wrong-thing.md) — [a refused timeline tells the reader the snapshot has no build log](UX-0545-a-refused-timeline-says-the-wrong-thing.md)
- [UX-555](UX-0555-with-trace-false-blames-a-missing-plane-2.md) — [`--no-trace` tells a two-plane run it kept no Plane 2 log](UX-0555-with-trace-false-blames-a-missing-plane-2.md)
- [UX-559](UX-0559-serve-leaks-a-scratch-directory-per-run.md) — [`bga view --serve` leaks a scratch directory per served run](UX-0559-serve-leaks-a-scratch-directory-per-run.md)
- [UX-640](UX-0640-the-rail-names-the-key-the-heading-asks-the-question.md) — [the rail names the key, the heading asks the question](UX-0640-the-rail-names-the-key-the-heading-asks-the-question.md)
- [UX-642](UX-0642-a-structured-fold-forgets-it-was-open.md) — [a structured fold forgets it was open](UX-0642-a-structured-fold-forgets-it-was-open.md)
- [UX-638](UX-0638-table-focus-destroys-the-reading-position.md) — [table focus destroys the reading position](UX-0638-table-focus-destroys-the-reading-position.md)
- [UX-639](UX-0639-the-rail-is-dead-while-a-table-is-focused.md) — [the rail is dead while a table is focused](UX-0639-the-rail-is-dead-while-a-table-is-focused.md)
- [UX-648](UX-0648-the-jump-box-names-sections-the-old-way.md) — [the jump box names sections the old way](UX-0648-the-jump-box-names-sections-the-old-way.md)
- [UX-643](UX-0643-a-reader-role-that-demotes-rather-than-hides.md) — [a reader role that demotes rather than hides](UX-0643-a-reader-role-that-demotes-rather-than-hides.md)
- [UX-647](UX-0647-a-rail-click-never-reaches-the-view-state-writer.md) — [a rail click never reaches the view-state writer](UX-0647-a-rail-click-never-reaches-the-view-state-writer.md)
- [UX-646](UX-0646-the-fragment-is-one-event-behind-the-fold.md) — [the fragment is one event behind the fold](UX-0646-the-fragment-is-one-event-behind-the-fold.md)
- [UX-650](UX-0650-nine-page-built-sections-declare-no-reader.md) — [nine page-built sections declare no reader](UX-0650-nine-page-built-sections-declare-no-reader.md)
- [UX-654](UX-0654-the-vocabulary-module-still-says-nine-hints.md) — [the vocabulary module still says nine hints](UX-0654-the-vocabulary-module-still-says-nine-hints.md)
- [UX-672](UX-0672-a-blocked-pop-up-s-refusal-never-renders.md) — [a blocked pop-up's refusal never renders](UX-0672-a-blocked-pop-up-s-refusal-never-renders.md)
- [UX-673](UX-0673-sixteen-tables-offer-a-top-10-they-cannot-fill.md) — [sixteen tables offer a Top 10 they cannot fill](UX-0673-sixteen-tables-offer-a-top-10-they-cannot-fill.md)
- [UX-669](UX-0669-a-runbook-is-a-shape-the-next-steps-rendered-once-as-steps.md) — [a runbook is a shape — the next steps rendered once, as steps](UX-0669-a-runbook-is-a-shape-the-next-steps-rendered-once-as-steps.md)
- [UX-670](UX-0670-the-first-rail-click-into-a-folded-chapter-lands-687-px-above-its-sect.md) — [the first rail click into a folded chapter lands 687 px above its section](UX-0670-the-first-rail-click-into-a-folded-chapter-lands-687-px-above-its-sect.md)
- [UX-721](UX-0721-an-aliased-import-is-silently-dropped-by-the-export.md) — [an aliased import is silently dropped by the export](UX-0721-an-aliased-import-is-silently-dropped-by-the-export.md)
- [UX-722](UX-0722-a-rail-target-inside-a-scrolling-table-lands-under-the-header.md) — [a rail target inside a scrolling table lands under the header](UX-0722-a-rail-target-inside-a-scrolling-table-lands-under-the-header.md)
- [UX-729](UX-0729-two-modules-declare-one-name-and-the-satellite-bundle-would-take-both.md) — [two modules declare one name, and the satellite bundle would take both](UX-0729-two-modules-declare-one-name-and-the-satellite-bundle-would-take-both.md)
- [UX-717](UX-0717-the-host-series-is-on-the-trace-and-in-no-question.md) — [the host series is on the trace and in no question](UX-0717-the-host-series-is-on-the-trace-and-in-no-question.md)
- [UX-667](UX-0667-the-rail-is-a-source-list-chapters-disclose-and-the-mark-stays-in-view.md) — [the rail is a source list — chapters disclose, and the mark stays in view](UX-0667-the-rail-is-a-source-list-chapters-disclose-and-the-mark-stays-in-view.md)
- [UX-699](UX-0699-the-viewer-linted-as-one-module-graph.md) — [the viewer linted as one module graph](UX-0699-the-viewer-linted-as-one-module-graph.md)
- [UX-674](UX-0674-eighteen-font-sizes-an-h3-larger-than-its-h2-and-130-character-lines.md) — [eighteen font sizes, an h3 larger than its h2, and 130-character lines](UX-0674-eighteen-font-sizes-an-h3-larger-than-its-h2-and-130-character-lines.md)
- [UX-753](UX-0753-the-flow-axis-is-drawn-by-one-row-and-read-by-none.md) — [the flow axis is drawn by one row and read by none](UX-0753-the-flow-axis-is-drawn-by-one-row-and-read-by-none.md)
- [UX-758](UX-0758-the-edge-mark-test-reads-a-merged-name-and-never-matches.md) — [the edge-mark test reads a merged name and never matches](UX-0758-the-edge-mark-test-reads-a-merged-name-and-never-matches.md)
- [UX-668](UX-0668-a-reader-is-a-shape-not-a-hue-and-the-selector-lives-in-the-header.md) — [a reader is a shape, not a hue — and the selector lives in the header](UX-0668-a-reader-is-a-shape-not-a-hue-and-the-selector-lives-in-the-header.md)
- [UX-671](UX-0671-the-rail-acts-on-the-view-and-the-url-does-not-follow.md) — [the rail acts on the view, and the URL does not follow](UX-0671-the-rail-acts-on-the-view-and-the-url-does-not-follow.md)
- [UX-800](UX-0800-the-rail-landing-counts-frames-and-the-count-moved-with-the-header.md) — [the rail landing counts frames, and the count moved with the header](UX-0800-the-rail-landing-counts-frames-and-the-count-moved-with-the-header.md)

**store**

- [UX-577](UX-0577-the-committed-example-s-own-next-step-refuses.md) — [the committed example's own next step refuses](UX-0577-the-committed-example-s-own-next-step-refuses.md)
- [UX-595](UX-0595-the-capacity-model-has-a-fact-base-and-no-model.md) — [the capacity model has a fact base and no model](UX-0595-the-capacity-model-has-a-fact-base-and-no-model.md)

**guards**

- [UX-544](UX-0544-the-node-census-has-a-hole.md) — [the hand-built *node* census has a hole the document census does not](UX-0544-the-node-census-has-a-hole.md)
- [UX-547](UX-0547-the-fixture-differ-cannot-see-key-order.md) — [the fixture differ compares parsed JSON, so key order drifts unseen](UX-0547-the-fixture-differ-cannot-see-key-order.md)
- [UX-554](UX-0554-a-failed-suite-takes-its-junit-with-it.md) — [a failed CI suite takes the record of what failed with it](UX-0554-a-failed-suite-takes-its-junit-with-it.md)
- [UX-543](UX-0543-a-second-ranking-clause-under-contention.md) — [a second clause of the answer key ranks under contention](UX-0543-a-second-ranking-clause-under-contention.md)
- [UX-546](UX-0546-the-fetch-guard-is-flaky-under-load.md) — [the fetch-counting handoff guard is flaky under the full suite](UX-0546-the-fetch-guard-is-flaky-under-load.md)
- [UX-557](UX-0557-the-cause-filter-admits-the-whole-suite.md) — [the drift gate's cause filter admits all 424 files](UX-0557-the-cause-filter-admits-the-whole-suite.md)
- [UX-558](UX-0558-the-failure-name-is-3800-lines-from-the-end.md) — [the failure's name is 3,800 lines from the end of the 3.11 job](UX-0558-the-failure-name-is-3800-lines-from-the-end.md)
- [UX-560](UX-0560-a-worktree-track-starts-from-origin-main.md) — [a worktree track starts from `origin/main`, whatever base its brief names](UX-0560-a-worktree-track-starts-from-origin-main.md)
- [UX-561](UX-0561-a-track-cannot-pass-its-own-commit-hook.md) — [a track that closes an item cannot pass its own pre-commit selector](UX-0561-a-track-cannot-pass-its-own-commit-hook.md)
- [UX-562](UX-0562-the-empty-backlog-reds-its-own-topic-guard.md) — [the guard that reds when the backlog it reads reaches zero open rows](UX-0562-the-empty-backlog-reds-its-own-topic-guard.md)
- [UX-586](UX-0586-the-premise-detector-reads-a-proxy.md) — [the premise detector reads a proxy](UX-0586-the-premise-detector-reads-a-proxy.md)
- [UX-587](UX-0587-the-reference-goes-stale-as-the-backlog-it-walks-grows.md) — [a guard whose cost is the backlog's size drifts past a reference `--adopt` cannot refresh](UX-0587-the-reference-goes-stale-as-the-backlog-it-walks-grows.md)
- [UX-579](UX-0579-the-docs-guard-reads-command-words-not-commands.md) — [the docs guard reads command words, not commands](UX-0579-the-docs-guard-reads-command-words-not-commands.md)
- [UX-588](UX-0588-the-python-floor-is-in-the-matrix-and-in-no-guard.md) — [the Python floor is in the CI matrix and in no guard](UX-0588-the-python-floor-is-in-the-matrix-and-in-no-guard.md)
- [UX-573](UX-0573-the-context-map-cannot-see-below-tools.md) — [the context map cannot see below `tools/`](UX-0573-the-context-map-cannot-see-below-tools.md)
- [UX-592](UX-0592-two-rail-harnesses-press-before-the-mark-they-depend-on.md) — [two rail harnesses press before the mark they depend on](UX-0592-two-rail-harnesses-press-before-the-mark-they-depend-on.md)
- [UX-585](UX-0585-the-card-s-guard-column-is-counted-not-read.md) — [the card's guard column is counted, not read](UX-0585-the-card-s-guard-column-is-counted-not-read.md)
- [UX-567](UX-0567-two-invariants-have-no-guard-and-one-has-no-code.md) — [two invariants have no guard, and one has no code](UX-0567-two-invariants-have-no-guard-and-one-has-no-code.md)
- [UX-568](UX-0568-the-spec-has-no-index-of-which-part-a-guard-holds.md) — [the spec has no index of which Part a guard holds](UX-0568-the-spec-has-no-index-of-which-part-a-guard-holds.md)
- [UX-589](UX-0589-the-namer-reads-a-junit-the-run-did-not-write.md) — [the failure namer reads a junit the run did not write](UX-0589-the-namer-reads-a-junit-the-run-did-not-write.md)
- [UX-605](UX-0605-the-touching-map-adopted-a-selection-that-is-everything.md) — [the touching map adopted a selection that is everything](UX-0605-the-touching-map-adopted-a-selection-that-is-everything.md)
- [UX-599](UX-0599-a-guard-pins-a-contract-version-by-typing-it.md) — [a guard pins a contract version by typing it](UX-0599-a-guard-pins-a-contract-version-by-typing-it.md)
- [UX-600](UX-0600-the-rules-card-has-one-guard-it-cannot-mark.md) — [the rules card has one guard it cannot mark](UX-0600-the-rules-card-has-one-guard-it-cannot-mark.md)
- [UX-590](UX-0590-the-context-map-s-non-path-claims-are-unguarded.md) — [the context map's non-path claims are unguarded](UX-0590-the-context-map-s-non-path-claims-are-unguarded.md)
- [UX-606](UX-0606-the-selectors-bound-is-measured-on-one-module.md) — [the selector's bound is measured on one module](UX-0606-the-selectors-bound-is-measured-on-one-module.md)
- [UX-609](UX-0609-the-invariants-docstring-lists-five-of-six-gates.md) — [the invariants docstring lists five of six gates](UX-0609-the-invariants-docstring-lists-five-of-six-gates.md)
- [UX-604](UX-0604-the-verification-log-clause-reads-the-entry-below.md) — [the verification-log clause reads the entry below it](UX-0604-the-verification-log-clause-reads-the-entry-below.md)
- [UX-618](UX-0618-the-step-that-fails-most-writes-no-record.md) — [the step that fails most writes no record](UX-0618-the-step-that-fails-most-writes-no-record.md)
- [UX-620](UX-0620-a-derived-count-re-dates-the-document-it-grounds.md) — [a derived count re-dates the document it grounds](UX-0620-a-derived-count-re-dates-the-document-it-grounds.md)
- [UX-619](UX-0619-four-small-tier-failures-nobody-can-name.md) — [four small-tier failures nobody can name](UX-0619-four-small-tier-failures-nobody-can-name.md)
- [UX-617](UX-0617-the-derived-count-cannot-see-an-unstaged-row.md) — [the derived count cannot see an unstaged row](UX-0617-the-derived-count-cannot-see-an-unstaged-row.md)
- [UX-614](UX-0614-a-track-starts-on-the-default-branch.md) — [a track starts on the default branch, not the round's](UX-0614-a-track-starts-on-the-default-branch.md)
- [UX-615](UX-0615-the-scratchpad-is-shared-between-tracks.md) — [the scratchpad is shared between tracks](UX-0615-the-scratchpad-is-shared-between-tracks.md)
- [UX-621](UX-0621-a-drift-gate-red-nobody-can-read.md) — [a drift-gate red nobody can read](UX-0621-a-drift-gate-red-nobody-can-read.md)
- [UX-624](UX-0624-the-cap-dropped-a-guard-that-was-not-noise.md) — [the cap dropped a guard that was not noise](UX-0624-the-cap-dropped-a-guard-that-was-not-noise.md)
- [UX-623](UX-0623-a-track-cannot-read-the-tree-it-was-copied-from.md) — [a track cannot read the tree it was copied from](UX-0623-a-track-cannot-read-the-tree-it-was-copied-from.md)
- [UX-626](UX-0626-a-brief-names-a-commit-nobody-resolved.md) — [a brief names a commit nobody resolved](UX-0626-a-brief-names-a-commit-nobody-resolved.md)
- [UX-625](UX-0625-reverting-a-mutation-can-discard-the-work.md) — [reverting a mutation can discard the work](UX-0625-reverting-a-mutation-can-discard-the-work.md)
- [UX-622](UX-0622-the-derived-count-and-its-guard-read-two-populations.md) — [the derived count and its guard read two populations](UX-0622-the-derived-count-and-its-guard-read-two-populations.md)
- [UX-627](UX-0627-closing-a-row-writes-done-open.md) — [closing a row writes `🟢 Done Open`](UX-0627-closing-a-row-writes-done-open.md)
- [UX-644](UX-0644-main-is-red-a-map-entry-under-the-cap-widened-a-module.md) — [main is red — a map entry under the cap widened a module](UX-0644-main-is-red-a-map-entry-under-the-cap-widened-a-module.md)
- [UX-649](UX-0649-the-spread-bound-was-set-on-one-machine.md) — [the spread bound was set on one machine](UX-0649-the-spread-bound-was-set-on-one-machine.md)
- [UX-645](UX-0645-the-census-floor-spends-half-the-width-bound.md) — [the census floor spends half the width bound](UX-0645-the-census-floor-spends-half-the-width-bound.md)
- [UX-656](UX-0656-main-is-red-a-closed-outcome-is-eight-lines-over-the-cap.md) — [main is red: a closed outcome is eight lines over the cap](UX-0656-main-is-red-a-closed-outcome-is-eight-lines-over-the-cap.md)
- [UX-657](UX-0657-the-priority-column-has-no-guard.md) — [the priority column has no guard](UX-0657-the-priority-column-has-no-guard.md)
- [UX-658](UX-0658-a-ninth-topic-exists-that-no-open-row-may-carry.md) — [a ninth topic exists that no open row may carry](UX-0658-a-ninth-topic-exists-that-no-open-row-may-carry.md)
- [UX-704](UX-0704-check-lists-the-backlog-once-per-row.md) — [`--check` lists the backlog once per row](UX-0704-check-lists-the-backlog-once-per-row.md)
- [UX-706](UX-0706-a-task-s-shape-is-derived-from-its-text-and-names-the-model-that-runs-it.md) — [a task's shape is derived from its text, and names the model that runs it](UX-0706-a-task-s-shape-is-derived-from-its-text-and-names-the-model-that-runs-it.md)
- [UX-693](UX-0693-the-lint-rule-set-widened-by-layer-in-one-auto-fix-commit-with-the-too.md) — [the lint rule set widened by layer, in one auto-fix commit, with the tools pinned](UX-0693-the-lint-rule-set-widened-by-layer-in-one-auto-fix-commit-with-the-too.md)
- [UX-700](UX-0700-the-symbol-index-and-codeql-declined-for-navigation.md) — [the symbol index — and CodeQL declined for navigation](UX-0700-the-symbol-index-and-codeql-declined-for-navigation.md)
- [UX-707](UX-0707-the-orchestrator-s-rebuilds-are-counted-and-priced-per-session.md) — [the orchestrator's rebuilds are counted and priced, per session](UX-0707-the-orchestrator-s-rebuilds-are-counted-and-priced-per-session.md)
- [UX-709](UX-0709-close-a-batch-of-ids-in-one-move.md) — [close a batch of ids in one `--move`](UX-0709-close-a-batch-of-ids-in-one-move.md)
- [UX-694](UX-0694-a-finding-baseline-and-a-size-ledger-for-what-has-no-identity.md) — [a finding baseline, and a size ledger for what has no identity](UX-0694-a-finding-baseline-and-a-size-ledger-for-what-has-no-identity.md)
- [UX-662](UX-0662-the-adopted-map-made-the-selector-guard-a-hundred-times-dearer.md) — [the adopted touching map made the selector guard a hundred times dearer](UX-0662-the-adopted-map-made-the-selector-guard-a-hundred-times-dearer.md)
- [UX-661](UX-0661-the-fourth-copy-of-the-topic-set-orders-a-release.md) — [the second copy of the topic set orders a release body](UX-0661-the-fourth-copy-of-the-topic-set-orders-a-release.md)
- [UX-687](UX-0687-the-impact-set-is-derived-by-one-tool-not-five-greps.md) — [the impact set is derived by one tool, not five greps](UX-0687-the-impact-set-is-derived-by-one-tool-not-five-greps.md)
- [UX-718](UX-0718-the-census-omits-the-guard-its-own-docstring-names.md) — [the census omits the guard its own docstring names](UX-0718-the-census-omits-the-guard-its-own-docstring-names.md)
- [UX-665](UX-0665-the-page-s-census-is-a-tool-so-a-walk-reads-it-instead-of-driving-it.md) — [the page's census is a tool, so a walk reads it instead of driving it](UX-0665-the-page-s-census-is-a-tool-so-a-walk-reads-it-instead-of-driving-it.md)
- [UX-685](UX-0685-exploration-is-a-seeded-scenario-and-every-finding-grows-the-answer-ke.md) — [exploration is a seeded scenario, and every finding grows the answer key](UX-0685-exploration-is-a-seeded-scenario-and-every-finding-grows-the-answer-ke.md)
- [UX-723](UX-0723-the-scenario-recipe-prints-commands-that-do-not-run.md) — [the scenario recipe prints commands that do not run](UX-0723-the-scenario-recipe-prints-commands-that-do-not-run.md)
- [UX-727](UX-0727-a-design-review-report-has-no-shape-a-guard-can-read.md) — [a design review report has no shape a guard can read](UX-0727-a-design-review-report-has-no-shape-a-guard-can-read.md)
- [UX-732](UX-0732-the-verification-logs-anchor-cannot-survive-a-merge.md) — [the verification log's anchor cannot survive a merge](UX-0732-the-verification-logs-anchor-cannot-survive-a-merge.md)
- [UX-731](UX-0731-a-ratio-guard-with-a-two-millisecond-denominator.md) — [a ratio guard with a two-millisecond denominator](UX-0731-a-ratio-guard-with-a-two-millisecond-denominator.md)
- [UX-736](UX-0736-the-architectures-status-table-is-a-third-copy-of-a-guarded-fact.md) — [the architecture's status table is a third copy of a guarded fact](UX-0736-the-architectures-status-table-is-a-third-copy-of-a-guarded-fact.md)
- [UX-730](UX-0730-a-derived-figure-over-the-whole-test-tree-has-no-refresh-route.md) — [a derived figure over the whole test tree has no refresh route](UX-0730-a-derived-figure-over-the-whole-test-tree-has-no-refresh-route.md)
- [UX-728](UX-0728-a-tracks-repro-runs-the-sessions-checkout-not-its-worktree.md) — [a track's repro runs the session's checkout, not its worktree](UX-0728-a-tracks-repro-runs-the-sessions-checkout-not-its-worktree.md)
- [UX-737](UX-0737-the-census-detectors-other-half-thirteen-guards-a-subprocess-hides.md) — [the census detector's other half — thirteen guards a subprocess hides](UX-0737-the-census-detectors-other-half-thirteen-guards-a-subprocess-hides.md)
- [UX-716](UX-0716-a-guard-whose-cost-is-its-population-has-no-refresh-route.md) — [a guard whose cost is its population has no refresh route](UX-0716-a-guard-whose-cost-is-its-population-has-no-refresh-route.md)
- [UX-692](UX-0692-the-invariants-hold-for-any-shape-a-seeded-sweep-over-generated-projec.md) — [the invariants hold for any shape — a seeded sweep over generated projects](UX-0692-the-invariants-hold-for-any-shape-a-seeded-sweep-over-generated-projec.md)
- [UX-691](UX-0691-a-flake-ledger-so-an-excursion-is-counted-before-it-is-a-flake.md) — [a flake ledger, so an excursion is counted before it is a flake](UX-0691-a-flake-ledger-so-an-excursion-is-counted-before-it-is-a-flake.md)
- [UX-702](UX-0702-a-performance-ratchet-at-the-gate.md) — [a performance ratchet at the gate](UX-0702-a-performance-ratchet-at-the-gate.md)
- [UX-712](UX-0712-the-size-ledger-for-what-has-no-finding-identity.md) — [the size ledger, for what has no finding identity](UX-0712-the-size-ledger-for-what-has-no-finding-identity.md)
- [UX-703](UX-0703-a-mutation-run-on-the-touched-modules-weekly.md) — [a mutation run on the touched modules, weekly](UX-0703-a-mutation-run-on-the-touched-modules-weekly.md)
- [UX-743](UX-0743-the-small-tier-backstop-was-sized-against-a-suite-half-this-size.md) — [the small tier's backstop was sized against a suite half this size](UX-0743-the-small-tier-backstop-was-sized-against-a-suite-half-this-size.md)
- [UX-696](UX-0696-the-register-s-unguarded-rows-no-round-in-code-a-dated-count-the-commi.md) — [the register's unguarded rows — no round in code, a dated count, the commit body](UX-0696-the-register-s-unguarded-rows-no-round-in-code-a-dated-count-the-commi.md)
- [UX-742](UX-0742-the-viewer-s-dead-exports-need-a-detector-eslint-cannot-be.md) — [the viewer's dead exports need a detector eslint cannot be](UX-0742-the-viewer-s-dead-exports-need-a-detector-eslint-cannot-be.md)
- [UX-705](UX-0705-the-burn-down-runs-on-the-reporters-model-a-batch-a-commit-never-a-supp.md) — [the burn-down runs on the reporters' model — a batch a commit, never a suppression](UX-0705-the-burn-down-runs-on-the-reporters-model-a-batch-a-commit-never-a-supp.md)
- [UX-747](UX-0747-the-derive-skill-s-own-example-crashes-the-tool-it-documents.md) — [the `derive` skill's own example crashes the tool it documents](UX-0747-the-derive-skill-s-own-example-crashes-the-tool-it-documents.md)
- [UX-745](UX-0745-a-track-can-authorise-its-own-baseline-growth-and-did.md) — [a track can authorise its own baseline growth, and did](UX-0745-a-track-can-authorise-its-own-baseline-growth-and-did.md)
- [UX-748](UX-0748-three-guards-read-a-narrower-population-than-the-sentence-they-check.md) — [three guards read a narrower population than the sentence they check](UX-0748-three-guards-read-a-narrower-population-than-the-sentence-they-check.md)
- [UX-752](UX-0752-the-guard-s-spelling-table-ran-out-at-forty.md) — [the guard's spelling table ran out at forty](UX-0752-the-guard-s-spelling-table-ran-out-at-forty.md)
- [UX-754](UX-0754-the-derived-figure-exclusion-cannot-read-a-merge.md) — [the derived-figure exclusion cannot read a merge](UX-0754-the-derived-figure-exclusion-cannot-read-a-merge.md)
- [UX-750](UX-0750-the-map-s-one-count-is-the-one-noun-the-guard-does-not-list.md) — [the map's one count is the one noun the guard does not list](UX-0750-the-map-s-one-count-is-the-one-noun-the-guard-does-not-list.md)
- [UX-751](UX-0751-the-landed-clause-reads-endpoints-where-the-open-clause-reads-the-range.md) — [the landed clause reads endpoints where the open clause reads the range](UX-0751-the-landed-clause-reads-endpoints-where-the-open-clause-reads-the-range.md)
- [UX-755](UX-0755-the-gate-and-ci-disagree-and-the-gate-is-the-one-that-is-wrong.md) — [the gate and CI disagree, and the gate is the one that is wrong](UX-0755-the-gate-and-ci-disagree-and-the-gate-is-the-one-that-is-wrong.md)
- [UX-762](UX-0762-the-gate-binds-to-a-branch-not-to-the-commit-that-is-pushed.md) — [the gate binds to a branch, not to the commit that is pushed](UX-0762-the-gate-binds-to-a-branch-not-to-the-commit-that-is-pushed.md)
- [UX-769](UX-0769-the-count-guard-matches-a-task-id.md) — [the count guard matches a task id, not a count](UX-0769-the-count-guard-matches-a-task-id.md)
- [UX-770](UX-0770-the-cost-row-median-sits-on-a-tie.md) — [the cost row's median sits on a tie, and the population moves under it](UX-0770-the-cost-row-median-sits-on-a-tie.md)
- [UX-768](UX-0768-the-closing-note-is-a-shell-argument-and-its-backticks-run.md) — [the closing note is a shell argument, and its backticks run](UX-0768-the-closing-note-is-a-shell-argument-and-its-backticks-run.md)
- [UX-766](UX-0766-the-forced-baseline-is-loud-only-until-it-is-committed.md) — [the forced baseline is loud only until it is committed](UX-0766-the-forced-baseline-is-loud-only-until-it-is-committed.md)
- [UX-767](UX-0767-the-push-gate-sees-one-channel-and-the-round-used-another.md) — [the push gate sees one channel, and the round used another](UX-0767-the-push-gate-sees-one-channel-and-the-round-used-another.md)
- [UX-759](UX-0759-the-register-s-id-column-loses-a-subset-in-silence.md) — [the register's id column loses a subset in silence](UX-0759-the-register-s-id-column-loses-a-subset-in-silence.md)
- [UX-760](UX-0760-six-more-files-build-against-the-broken-reserve.md) — [six more files build against the broken reserve](UX-0760-six-more-files-build-against-the-broken-reserve.md)
- [UX-776](UX-0776-a-derivation-from-git-history-is-a-property-of-the-clone.md) — [a derivation from git history is a property of the clone](UX-0776-a-derivation-from-git-history-is-a-property-of-the-clone.md)
- [UX-771](UX-0771-two-more-documents-number-sections-and-no-guard-reads-them.md) — [two more documents number sections, and no guard reads them](UX-0771-two-more-documents-number-sections-and-no-guard-reads-them.md)
- [UX-772](UX-0772-the-first-date-in-a-document-is-not-its-dateline.md) — [the first date in a document is not its dateline](UX-0772-the-first-date-in-a-document-is-not-its-dateline.md)
- [UX-773](UX-0773-a-killed-worker-leaks-a-browser-and-its-profile.md) — [a killed worker leaks a browser and its profile](UX-0773-a-killed-worker-leaks-a-browser-and-its-profile.md)
- [UX-781](UX-0781-ci-truncates-the-history-it-just-fetched-in-full.md) — [CI truncates the history it just fetched in full](UX-0781-ci-truncates-the-history-it-just-fetched-in-full.md)
- [UX-783](UX-0783-two-tier-rules-disagree-and-a-sweep-does-not-wait.md) — [two tier rules disagree about one file, and a sweep does not wait for what it killed](UX-0783-two-tier-rules-disagree-and-a-sweep-does-not-wait.md)
- [UX-784](UX-0784-one-fetch-depth-anywhere-satisfied-a-sentence-about-every-job.md) — [one `fetch-depth: 0` anywhere satisfied a sentence about every job](UX-0784-one-fetch-depth-anywhere-satisfied-a-sentence-about-every-job.md)
- [UX-698](UX-0698-the-gate-only-shelf-on-github-code-scanning-a-lockfile-and-audit-depen.md) — [the gate-only shelf on GitHub — code scanning, a lockfile and audit, Dependabot, secret scanning](UX-0698-the-gate-only-shelf-on-github-code-scanning-a-lockfile-and-audit-depen.md)
- [UX-793](UX-0793-a-retrospective-verifier-reads-the-tracks-tip-and-not-the-suite.md) — [a retrospective verifier reads the track's tip, and not the suite](UX-0793-a-retrospective-verifier-reads-the-tracks-tip-and-not-the-suite.md)
- [UX-785](UX-0785-the-flake-census-clears-any-file-a-task-ever-mentioned.md) — [the flake census clears any file a task ever mentioned](UX-0785-the-flake-census-clears-any-file-a-task-ever-mentioned.md)
- [UX-786](UX-0786-the-flake-ledgers-adopt-is-never-run-against-a-non-empty-ledger.md) — [the flake ledger's adopt is never run against a non-empty ledger](UX-0786-the-flake-ledgers-adopt-is-never-run-against-a-non-empty-ledger.md)
- [UX-792](UX-0792-the-perf-carry-key-is-scoped-to-a-branch-by-nothing.md) — [the perf-carry key is scoped to a branch by nothing](UX-0792-the-perf-carry-key-is-scoped-to-a-branch-by-nothing.md)
- [UX-787](UX-0787-the-size-ledger-cannot-record-a-shrink-while-any-cell-grew.md) — [the size ledger cannot record a shrink while any cell grew](UX-0787-the-size-ledger-cannot-record-a-shrink-while-any-cell-grew.md)
- [UX-788](UX-0788-the-size-ledger-trusts-a-broken-pylint.md) — [the size ledger trusts a broken pylint](UX-0788-the-size-ledger-trusts-a-broken-pylint.md)
- [UX-794](UX-0794-the-ledgers-count-word-stopped-at-ninety-nine.md) — [the ledger's count word stopped at ninety-nine](UX-0794-the-ledgers-count-word-stopped-at-ninety-nine.md)
- [UX-697](UX-0697-a-type-error-ratchet-contracts-first.md) — [a type-error ratchet, contracts first](UX-0697-a-type-error-ratchet-contracts-first.md)
- [UX-790](UX-0790-the-mutation-runs-classifier-has-no-fast-guard.md) — [the mutation run's classifier has no fast guard](UX-0790-the-mutation-runs-classifier-has-no-fast-guard.md)
- [UX-764](UX-0764-two-register-caps-are-guarded-and-two-are-honour-system.md) — [two Register caps are guarded and two are honour-system](UX-0764-two-register-caps-are-guarded-and-two-are-honour-system.md)
- [UX-795](UX-0795-the-focus-guard-measures-after-a-fixed-sleep-and-one-runner-was-slower.md) — [the focus guard measures after a fixed sleep, and one runner was slower](UX-0795-the-focus-guard-measures-after-a-fixed-sleep-and-one-runner-was-slower.md)
- [UX-789](UX-0789-a-baseline-entry-carries-a-key-the-tool-never-reads.md) — [a baseline entry carries a key the tool never reads](UX-0789-a-baseline-entry-carries-a-key-the-tool-never-reads.md)
- [UX-775](UX-0775-two-files-still-build-against-the-ambient-home.md) — [two files still build against the ambient HOME](UX-0775-two-files-still-build-against-the-ambient-home.md)
- [UX-741](UX-0741-the-spine-s-ground-truth-reads-wall-clock-and-a-loaded-host-reds-it.md) — [the spine's ground truth reads wall clock, and a loaded host reds it](UX-0741-the-spine-s-ground-truth-reads-wall-clock-and-a-loaded-host-reds-it.md)
- [UX-690](UX-0690-the-suite-has-a-shape-budget-and-a-feature-files-its-test-analysis.md) — [the suite has a shape budget, and a feature files its test analysis](UX-0690-the-suite-has-a-shape-budget-and-a-feature-files-its-test-analysis.md)
- [UX-796](UX-0796-the-host-sampler-claims-more-busy-cores-than-the-host-has-under-load.md) — [the host sampler claims more busy cores than the host has, under load](UX-0796-the-host-sampler-claims-more-busy-cores-than-the-host-has-under-load.md)
- [UX-801](UX-0801-bst-show-writes-the-cas-and-two-files-still-run-it-in-the-ambient-home.md) — [`bst show` writes the CAS, and two files still run it in the ambient HOME](UX-0801-bst-show-writes-the-cas-and-two-files-still-run-it-in-the-ambient-home.md)
- [UX-802](UX-0802-the-baseline-guard-files-spawn-pyright-sixteen-times.md) — [the baseline guard files spawn pyright sixteen times](UX-0802-the-baseline-guard-files-spawn-pyright-sixteen-times.md)
- [UX-803](UX-0803-a-step-change-in-a-file-s-cost-takes-three-main-pushes-to-reach-the-reference.md) — [a step change in a file's cost takes three main pushes to reach the reference](UX-0803-a-step-change-in-a-file-s-cost-takes-three-main-pushes-to-reach-the-reference.md)
- [UX-782](UX-0782-the-register-derives-its-rounds-from-git-log.md) — [the register derives its rounds from `git log`, which is a property of the clone](UX-0782-the-register-derives-its-rounds-from-git-log.md)
- [UX-797](UX-0797-eight-identical-sleeps-spread-past-a-tenth-under-organic-load.md) — [eight identical sleeps spread past a tenth, under organic load](UX-0797-eight-identical-sleeps-spread-past-a-tenth-under-organic-load.md)
- [UX-804](UX-0804-the-diagnostics-performance-guard-is-a-typed-ten-seconds-of-wall-clock.md) — [the diagnostics performance guard is a typed ten seconds of wall clock](UX-0804-the-diagnostics-performance-guard-is-a-typed-ten-seconds-of-wall-clock.md)
- [UX-811](UX-0811-the-commit-body-gate-reads-dependabot-s-generated-bodies.md) — [the commit-body gate reads Dependabot's generated bodies](UX-0811-the-commit-body-gate-reads-dependabot-s-generated-bodies.md)
- [UX-812](UX-0812-the-impact-guard-needs-an-open-analysis-row-to-be-green.md) — [the impact guard needs an open analysis row to be green](UX-0812-the-impact-guard-needs-an-open-analysis-row-to-be-green.md)
- [UX-813](UX-0813-the-history-row-s-count-is-right-because-two-errors-cancel.md) — [the history row's count is right because two errors cancel](UX-0813-the-history-row-s-count-is-right-because-two-errors-cancel.md)

**docs**

- [UX-548](UX-0548-round-80s-viewer-axis-reaches-no-guide.md) — [five mechanisms round 80 shipped, and no guide names one](UX-0548-round-80s-viewer-axis-reaches-no-guide.md)
- [UX-552](UX-0552-the-alias-table-is-two-rows-short.md) — [the CLI guide's alias table is two rows short](UX-0552-the-alias-table-is-two-rows-short.md)
- [UX-549](UX-0549-five-counted-figures-a-reader-reads-as-current.md) — [five counted figures, read as current, wrong](UX-0549-five-counted-figures-a-reader-reads-as-current.md)
- [UX-551](UX-0551-the-loop-is-planned-against-a-suite-that-is-gone.md) — [every session plans its loop against a suite 62% faster than the real one](UX-0551-the-loop-is-planned-against-a-suite-that-is-gone.md)
- [UX-556](UX-0556-the-spec-carries-the-sentence-ux-549-fixed.md) — [the spec still says "the last four are written but not printable"](UX-0556-the-spec-carries-the-sentence-ux-549-fixed.md)
- [UX-566](UX-0566-two-recommended-parts-describe-a-tool-that-was-never-built-that-way.md) — [two "recommended" Parts describe a tool that was never built that way](UX-0566-two-recommended-parts-describe-a-tool-that-was-never-built-that-way.md)
- [UX-576](UX-0576-the-question-count-is-stated-three-ways.md) — [the question count is stated three ways](UX-0576-the-question-count-is-stated-three-ways.md)
- [UX-570](UX-0570-the-capture-workflow-document-describes-a-workflow-that-has-moved-on.md) — [the capture workflow document describes a workflow that has moved on](UX-0570-the-capture-workflow-document-describes-a-workflow-that-has-moved-on.md)
- [UX-572](UX-0572-by-construction-survived-the-construction-it-now-depends-on.md) — ["by construction" survived the construction it now depends on](UX-0572-by-construction-survived-the-construction-it-now-depends-on.md)
- [UX-571](UX-0571-the-ingestion-facts-were-confirmed-on-a-buildstream-this-machine-no-lo.md) — [the ingestion facts were confirmed on a BuildStream this machine no longer has](UX-0571-the-ingestion-facts-were-confirmed-on-a-buildstream-this-machine-no-lo.md)
- [UX-582](UX-0582-the-styleguide-s-ledger-says-seven-sections-have-no-guard.md) — [the styleguide's ledger says seven sections have no guard](UX-0582-the-styleguide-s-ledger-says-seven-sections-have-no-guard.md)
- [UX-583](UX-0583-the-round-history-is-typed-and-three-rounds-are-missing-from-it.md) — [the round history is typed, and three rounds are missing from it](UX-0583-the-round-history-is-typed-and-three-rounds-are-missing-from-it.md)
- [UX-581](UX-0581-a-direction-has-no-status-so-a-tail-goes-silent.md) — [a direction has no status, so a tail goes silent](UX-0581-a-direction-has-no-status-so-a-tail-goes-silent.md)
- [UX-580](UX-0580-the-roles-table-says-nothing-aggregates-across-builds.md) — [the roles table says nothing aggregates across builds](UX-0580-the-roles-table-says-nothing-aggregates-across-builds.md)
- [UX-569](UX-0569-the-architecture-document-s-prose-is-not-what-its-guards-read.md) — [the architecture document's prose is not what its guards read](UX-0569-the-architecture-document-s-prose-is-not-what-its-guards-read.md)
- [UX-578](UX-0578-the-verbatim-blocks-that-are-neither-dated-nor-fresh.md) — [the verbatim blocks that are neither dated nor fresh](UX-0578-the-verbatim-blocks-that-are-neither-dated-nor-fresh.md)
- [UX-584](UX-0584-the-figures-nothing-reads-thirteen-stale-numbers-in-the-process-layer.md) — [the figures nothing reads — thirteen stale numbers in the process layer](UX-0584-the-figures-nothing-reads-thirteen-stale-numbers-in-the-process-layer.md)
- [UX-591](UX-0591-the-architecture-review-log-is-in-no-index.md) — [the architecture review log is in no index](UX-0591-the-architecture-review-log-is-in-no-index.md)
- [UX-603](UX-0603-the-python-floor-reaches-no-reader.md) — [the Python floor reaches no reader](UX-0603-the-python-floor-reaches-no-reader.md)
- [UX-607](UX-0607-a-paragraph-in-the-guide-is-a-two-file-change.md) — [a paragraph in the guide is a two-file change](UX-0607-a-paragraph-in-the-guide-is-a-two-file-change.md)
- [UX-608](UX-0608-fifteen-commands-the-context-map-never-names.md) — [fifteen commands the context map never names](UX-0608-fifteen-commands-the-context-map-never-names.md)
- [UX-601](UX-0601-two-guard-ledgers-of-the-same-kind.md) — [two guard ledgers of the same kind, two mechanisms](UX-0601-two-guard-ledgers-of-the-same-kind.md)
- [UX-616](UX-0616-the-coupling-runs-the-other-way-too.md) — [the coupling runs the other way too](UX-0616-the-coupling-runs-the-other-way-too.md)
- [UX-597](UX-0597-three-release-rows-and-no-tag.md) — [three release rows and no tag](UX-0597-three-release-rows-and-no-tag.md)
- [UX-634](UX-0634-the-tag-is-cut-and-nothing-is-published.md) — [the tag is cut and nothing is published](UX-0634-the-tag-is-cut-and-nothing-is-published.md)
- [UX-633](UX-0633-a-release-tag-names-a-commit-main-cannot-reach.md) — [a release tag names a commit `main` cannot reach](UX-0633-a-release-tag-names-a-commit-main-cannot-reach.md)
- [UX-630](UX-0630-two-environment-variables-no-inventory-sees.md) — [two environment variables no inventory sees](UX-0630-two-environment-variables-no-inventory-sees.md)
- [UX-631](UX-0631-the-context-map-guard-cannot-see-a-package-file.md) — [the context map's guard cannot see a file inside a package](UX-0631-the-context-map-guard-cannot-see-a-package-file.md)
- [UX-632](UX-0632-the-touching-figure-is-the-sample-its-own-round-disproved.md) — [the touching figure is the sample its own round disproved](UX-0632-the-touching-figure-is-the-sample-its-own-round-disproved.md)
- [UX-635](UX-0635-the-inventory-stops-at-one-namespace.md) — [the environment inventory stops at one namespace](UX-0635-the-inventory-stops-at-one-namespace.md)
- [UX-636](UX-0636-eighty-published-keys-no-document-names.md) — [eighty published keys no document names](UX-0636-eighty-published-keys-no-document-names.md)
- [UX-651](UX-0651-the-spec-s-part-32-block-is-two-ids-behind.md) — [the spec's Part 32 block is two ids behind](UX-0651-the-spec-s-part-32-block-is-two-ids-behind.md)
- [UX-652](UX-0652-the-currency-guard-resolves-to-a-day-and-a-day-holds-three-rounds.md) — [the currency guard resolves to a day, and a day holds three rounds](UX-0652-the-currency-guard-resolves-to-a-day-and-a-day-holds-three-rounds.md)
- [UX-653](UX-0653-a-contract-bump-rewrites-the-record-of-what-it-superseded.md) — [a contract bump rewrites the record of what it superseded](UX-0653-a-contract-bump-rewrites-the-record-of-what-it-superseded.md)
- [UX-655](UX-0655-a-contract-bump-landed-one-level-below-the-key-population.md) — [a contract bump landed one level below the key population](UX-0655-a-contract-bump-landed-one-level-below-the-key-population.md)
- [UX-663](UX-0663-reading-and-checking-run-on-a-smaller-model-and-the-frontmatter-says-s.md) — [reading and checking run on a smaller model, and the frontmatter says so](UX-0663-reading-and-checking-run-on-a-smaller-model-and-the-frontmatter-says-s.md)
- [UX-664](UX-0664-the-walk-and-the-design-review-are-protocols-not-prompts.md) — [the walk and the design review are protocols, not prompts](UX-0664-the-walk-and-the-design-review-are-protocols-not-prompts.md)
- [UX-710](UX-0710-a-ledger-row-is-derived-from-the-transcript-not-typed.md) — [a ledger row is derived from the transcript, not typed](UX-0710-a-ledger-row-is-derived-from-the-transcript-not-typed.md)
- [UX-660](UX-0660-one-sentence-two-figures-one-guarded.md) — [one sentence, two line numbers, and only one of them is guarded](UX-0660-one-sentence-two-figures-one-guarded.md)
- [UX-711](UX-0711-a-tool-result-longer-than-a-screen-goes-to-a-file.md) — [a tool result longer than a screen goes to a file](UX-0711-a-tool-result-longer-than-a-screen-goes-to-a-file.md)
- [UX-701](UX-0701-the-self-review-skill-the-existing-policy-on-the-diff-on-the-reporters.md) — [the `self-review` skill — the existing policy on the diff, on the reporters' model](UX-0701-the-self-review-skill-the-existing-policy-on-the-diff-on-the-reporters.md)
- [UX-688](UX-0688-every-task-carries-an-area-and-the-area-pages-are-generated.md) — [every task carries an area, and the area pages are generated](UX-0688-every-task-carries-an-area-and-the-area-pages-are-generated.md)
- [UX-686](UX-0686-a-release-waits-for-the-walk-that-read-its-candidate.md) — [a release waits for the walk that read its candidate](UX-0686-a-release-waits-for-the-walk-that-read-its-candidate.md)
- [UX-713](UX-0713-the-skill-that-runs-the-review-is-named-by-neither-document.md) — [the skill that runs the review is named by neither document](UX-0713-the-skill-that-runs-the-review-is-named-by-neither-document.md)
- [UX-714](UX-0714-the-orchestrators-share-is-a-bare-figure-that-has-moved.md) — [the orchestrator's share is a bare figure that has moved](UX-0714-the-orchestrators-share-is-a-bare-figure-that-has-moved.md)
- [UX-715](UX-0715-fifteen-viewer-modules-in-a-passage-with-no-date.md) — [fifteen viewer modules, in a passage with no date](UX-0715-fifteen-viewer-modules-in-a-passage-with-no-date.md)
- [UX-734](UX-0734-three-counted-figures-in-three-documents-and-no-guard-reads-any.md) — [three counted figures in three documents, and no guard reads any](UX-0734-three-counted-figures-in-three-documents-and-no-guard-reads-any.md)
- [UX-735](UX-0735-the-attachment-guides-export-size-measures-a-capture-not-in-the-tree.md) — [the attachment guide's export size measures a capture not in the tree](UX-0735-the-attachment-guides-export-size-measures-a-capture-not-in-the-tree.md)
- [UX-666](UX-0666-a-subagent-s-cost-is-written-down-and-its-friction-with-it.md) — [a subagent's cost is written down, and its friction with it](UX-0666-a-subagent-s-cost-is-written-down-and-its-friction-with-it.md)
- [UX-708](UX-0708-the-first-batch-under-the-pipeline-priced-per-shape.md) — [the first batch under the pipeline, priced per shape](UX-0708-the-first-batch-under-the-pipeline-priced-per-shape.md)
- [UX-746](UX-0746-four-workflows-are-on-no-map-and-the-map-s-guard-cannot-see-them.md) — [four workflows are on no map, and the map's guard cannot see them](UX-0746-four-workflows-are-on-no-map-and-the-map-s-guard-cannot-see-them.md)
- [UX-749](UX-0749-a-citation-that-looks-like-a-path-and-a-count-of-branches-that-moved.md) — [a citation that looks like a path, and a count of branches that moved](UX-0749-a-citation-that-looks-like-a-path-and-a-count-of-branches-that-moved.md)
- [UX-756](UX-0756-the-spread-rule-names-a-new-file-when-an-import-is-enough.md) — [the spread rule names a new file when an import is enough](UX-0756-the-spread-rule-names-a-new-file-when-an-import-is-enough.md)
- [UX-761](UX-0761-the-verifier-is-mandated-in-the-one-document-the-guide-outranks.md) — [the verifier is mandated in the one document the guide outranks](UX-0761-the-verifier-is-mandated-in-the-one-document-the-guide-outranks.md)
- [UX-757](UX-0757-the-four-rounds-the-register-names-have-no-document.md) — [the four rounds the register names have no document](UX-0757-the-four-rounds-the-register-names-have-no-document.md)
- [UX-763](UX-0763-no-document-says-what-closing-a-round-owes.md) — [no document says what closing a round owes](UX-0763-no-document-says-what-closing-a-round-owes.md)
- [UX-765](UX-0765-two-process-cross-references-point-at-numbers-that-are-not-there.md) — [two process cross-references point at numbers that are not there](UX-0765-two-process-cross-references-point-at-numbers-that-are-not-there.md)
- [UX-791](UX-0791-an-orphan-row-in-the-architecture-table-is-invisible.md) — [an orphan row in the architecture table is invisible](UX-0791-an-orphan-row-in-the-architecture-table-is-invisible.md)
- [UX-778](UX-0778-the-docs-index-counts-two-guards-where-four-fire.md) — [the docs index counts two guards where four fire](UX-0778-the-docs-index-counts-two-guards-where-four-fire.md)
- [UX-744](UX-0744-no-register-says-which-rounds-exist-and-four-records-disagree.md) — [no register says which rounds exist, and four records disagree](UX-0744-no-register-says-which-rounds-exist-and-four-records-disagree.md)
- [UX-779](UX-0779-the-readme-prints-two-wall-clocks-the-guide-says-are-not-the-suites.md) — [the README prints two wall clocks the guide says are not the suite's](UX-0779-the-readme-prints-two-wall-clocks-the-guide-says-are-not-the-suites.md)
- [UX-777](UX-0777-the-nine-page-built-sections-are-thirteen-in-two-documents.md) — [the nine page-built sections are thirteen, in two documents](UX-0777-the-nine-page-built-sections-are-thirteen-in-two-documents.md)
- [UX-780](UX-0780-the-map-says-a-shelf-shipped-and-one-linter-did.md) — [the map says a shelf shipped, and one linter did](UX-0780-the-map-says-a-shelf-shipped-and-one-linter-did.md)
- [UX-774](UX-0774-the-guide-is-at-its-band-ceiling-and-every-round-pays-a-trim.md) — [the guide is at its band ceiling, and every round pays a trim](UX-0774-the-guide-is-at-its-band-ceiling-and-every-round-pays-a-trim.md)
- [UX-798](UX-0798-the-directions-row-counts-a-round-s-closes-by-hand.md) — [the directions row counts a round's closes by hand](UX-0798-the-directions-row-counts-a-round-s-closes-by-hand.md)
- [UX-799](UX-0799-the-map-row-for-the-baseline-tool-names-one-of-its-two-modes.md) — [the map row for the baseline tool names one of its two modes](UX-0799-the-map-row-for-the-baseline-tool-names-one-of-its-two-modes.md)
- [UX-695](UX-0695-the-refactor-stream-takes-the-ledger-s-top-row-renderers-first.md) — [the refactor stream takes the ledger's top row — renderers first](UX-0695-the-refactor-stream-takes-the-ledger-s-top-row-renderers-first.md)
- [UX-806](UX-0806-the-plane-2-chapter-moves-into-the-native-trace-area-page.md) — [the Plane 2 chapter moves into the native-trace area page](UX-0806-the-plane-2-chapter-moves-into-the-native-trace-area-page.md)
- [UX-807](UX-0807-the-projection-chapter-moves-into-the-replay-area-page.md) — [the projection chapter moves into the replay area page](UX-0807-the-projection-chapter-moves-into-the-replay-area-page.md)
- [UX-810](UX-0810-the-plane-3-chapter-moves-into-the-tools-area-page.md) — [the Plane 3 chapter moves into the tools area page](UX-0810-the-plane-3-chapter-moves-into-the-tools-area-page.md)
- [UX-814](UX-0814-the-map-s-commit-body-row-is-behind-the-app-author-skip.md) — [the map's commit-body row is behind the App-author skip](UX-0814-the-map-s-commit-body-row-is-behind-the-app-author-skip.md)
- [UX-815](UX-0815-the-ingestion-path-chapter-moves-into-the-tools-area-page.md) — [the ingestion-path chapter moves into the tools area page](UX-0815-the-ingestion-path-chapter-moves-into-the-tools-area-page.md)
- [UX-816](UX-0816-the-bga-area-s-five-chapters-move-into-its-page.md) — [the bga area's five chapters move into its page](UX-0816-the-bga-area-s-five-chapters-move-into-its-page.md)
- [UX-689](UX-0689-the-architecture-document-moves-into-the-area-pages-one-track-at-a-tim.md) — [the architecture document moves into the area pages, one track at a time](UX-0689-the-architecture-document-moves-into-the-area-pages-one-track-at-a-tim.md)
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

- [UX-343](UX-0343-seven-in-ten-numbers-carry-no-declared-unit.md) — [half the numbers carry no unit at all](UX-0343-seven-in-ten-numbers-carry-no-declared-unit.md)
- [UX-341](UX-0341-one-unit-per-dimension.md) — [one unit per dimension](UX-0341-one-unit-per-dimension.md)
- [UX-345](UX-0345-the-chains-length-is-a-duration-wearing-a-counts-declaration.md) — [the chain's length is a duration wearing a count's declaration](UX-0345-the-chains-length-is-a-duration-wearing-a-counts-declaration.md)
- [UX-344](UX-0344-the-payload-is-six-deep-and-two-of-them-are-namespaces.md) — [the payload is six deep, and two of them are namespaces](UX-0344-the-payload-is-six-deep-and-two-of-them-are-namespaces.md)
- [UX-354](UX-0354-the-workflow-reads-the-payload-and-no-guard-reads-the-workflow.md) — [the workflow reads the payload, and no guard reads the workflow](UX-0354-the-workflow-reads-the-payload-and-no-guard-reads-the-workflow.md)
- [UX-382](UX-0382-the-element-entity-has-two-shapes-sharing-one-attribute.md) — [the element entity has two shapes, and they share one attribute](UX-0382-the-element-entity-has-two-shapes-sharing-one-attribute.md)
- [UX-381](UX-0381-the-capture-directory-is-a-contract-nothing-writes-down.md) — [the capture directory is a contract nothing writes down](UX-0381-the-capture-directory-is-a-contract-nothing-writes-down.md)
- [UX-384](UX-0384-a-redundancy-finding-still-carries-every-element-it-spans.md) — [a redundancy finding still carries every element it spans](UX-0384-a-redundancy-finding-still-carries-every-element-it-spans.md)
- [UX-386](UX-0386-plane2-v2-is-described-as-per-element-and-is-mostly-not.md) — [`plane2/v2` is described as per-element, and mostly is not](UX-0386-plane2-v2-is-described-as-per-element-and-is-mostly-not.md)
- [UX-408](UX-0408-serialized-pairs-described-as-its-own-opposite.md) — [`serialized_pairs` is described as its own opposite](UX-0408-serialized-pairs-described-as-its-own-opposite.md)
- [UX-431](UX-0431-the-arrow-count-reports-zero-losses-having-dropped-most.md) — [the arrow count reports zero losses, having drawn no arrows](UX-0431-the-arrow-count-reports-zero-losses-having-dropped-most.md)
- [UX-438](UX-0438-the-page-guesses-a-unit-and-says-so.md) — [the page guesses a unit on a real capture, and says so on the console](UX-0438-the-page-guesses-a-unit-and-says-so.md)
- [UX-440](UX-0440-two-rankings-over-one-order.md) — [two rankings over one order, and nothing says why there are two](UX-0440-two-rankings-over-one-order.md)
- [UX-452](UX-0452-the-legacy-chrome-trace-is-written-and-never-read.md) — [every capture writes a legacy Chrome trace that no reader opens](UX-0452-the-legacy-chrome-trace-is-written-and-never-read.md)
- [UX-466](UX-0466-what-the-capture-holds-and-the-trace-drops.md) — [nothing measures which captured field reaches a Perfetto slice](UX-0466-what-the-capture-holds-and-the-trace-drops.md)
- [UX-469](UX-0469-fields-the-capture-holds-and-the-trace-drops.md) — [the resource a task held reaches no Perfetto carrier](UX-0469-fields-the-capture-holds-and-the-trace-drops.md)
- [UX-483](UX-0483-a-provenance-record-inlines-the-whole-population-it-cites.md) — [a provenance record inlines whatever its path resolves to, and only convention keeps that from being a whole population](UX-0483-a-provenance-record-inlines-the-whole-population-it-cites.md)
- [UX-485](UX-0485-the-census-cannot-tell-a-carried-value-from-a-borrowed-one.md) — [the trace census cannot tell a field that arrived from one whose values another field brought](UX-0485-the-census-cannot-tell-a-carried-value-from-a-borrowed-one.md)

**analysis**

- [UX-365](UX-0365-the-finding-that-claims-the-superlative-is-the-small-one.md) — [the finding that claims the superlative is the small one](UX-0365-the-finding-that-claims-the-superlative-is-the-small-one.md)
- [UX-409](UX-0409-the-configure-tax-names-one-payer-twice.md) — [the configure tax names one payer twice](UX-0409-the-configure-tax-names-one-payer-twice.md)
- [UX-407](UX-0407-the-finding-that-is-the-answer-stays-at-the-terminal.md) — [the finding that *is* the answer stays at the terminal](UX-0407-the-finding-that-is-the-answer-stays-at-the-terminal.md)
- [UX-439](UX-0439-the-blast-radius-ranking-ties-and-the-tie-break-is-unstable.md) — [the blast-radius ranking ties, and the tie-break is unstable](UX-0439-the-blast-radius-ranking-ties-and-the-tie-break-is-unstable.md)
- [UX-467](UX-0467-does-the-shape-conclusion-support-a-decision.md) — [the graph-shape conclusions have no negative case](UX-0467-does-the-shape-conclusion-support-a-decision.md)
- [UX-477](UX-0477-the-chain-share-denominator-carries-a-constant.md) — [one graph, two verdicts — the chain-bound line is decided by how long the build is](UX-0477-the-chain-share-denominator-carries-a-constant.md)
- [UX-479](UX-0479-a-chain-bound-build-publishes-no-blast-radius.md) — [a chain-bound build publishes no blast radius, so the recipe-author never learns what their element reaches](UX-0479-a-chain-bound-build-publishes-no-blast-radius.md)
- [UX-475](UX-0475-mesh-graph-calls-a-linear-chain-a-mesh.md) — [`mesh-graph` calls a five-element linear chain "a mesh of near-equal chains"](UX-0475-mesh-graph-calls-a-linear-chain-a-mesh.md)
- [UX-478](UX-0478-the-graph-owner-vanishes-on-a-graph-problem.md) — [the graph-owner is not offered a reader on the one build whose defect is the graph](UX-0478-the-graph-owner-vanishes-on-a-graph-problem.md)
- [UX-474](UX-0474-the-blast-ranking-publishes-a-list-of-zeros.md) — ["Elements Most Worth Optimizing First (by blast radius)" ranks three elements whose blast radius is zero](UX-0474-the-blast-ranking-publishes-a-list-of-zeros.md)
- [UX-481](UX-0481-the-replay-lets-a-build-start-before-its-dependency-is-pulled.md) — [the replay starts a build before the artifacts it consumes have been pulled](UX-0481-the-replay-lets-a-build-start-before-its-dependency-is-pulled.md)
- [UX-531](UX-0531-bga-analyze-is-superlinear-and-the-page-pays.md) — [`bga analyze` is superlinear, and the page pays for it](UX-0531-bga-analyze-is-superlinear-and-the-page-pays.md)
- [UX-539](UX-0539-two-superlinear-terms-analyze-still-has.md) — [the two superlinear terms UX-531 measured and did not take](UX-0539-two-superlinear-terms-analyze-still-has.md)

**capture**

- [UX-333](UX-0333-the-name-is-the-whole-command.md) — [the name is the whole command](UX-0333-the-name-is-the-whole-command.md)
- [UX-379](UX-0379-the-hook-reads-a-rusage-struct-and-publishes-three-fields.md) — [the hook reads a rusage struct and publishes three of its fields](UX-0379-the-hook-reads-a-rusage-struct-and-publishes-three-fields.md)
- [UX-378](UX-0378-the-hosts-memory-is-a-number-from-before-the-build.md) — [the host's memory is a number from before the build, and an OOM leaves no trace](UX-0378-the-hosts-memory-is-a-number-from-before-the-build.md)
- [UX-375](UX-0375-the-plane-2-report-has-one-uncapped-population.md) — [the Plane 2 report has one uncapped population](UX-0375-the-plane-2-report-has-one-uncapped-population.md)
- [UX-377](UX-0377-the-run-and-the-graph-disagree-about-max-jobs.md) — [the run and the graph disagree about max-jobs, and on a default capture neither has it](UX-0377-the-run-and-the-graph-disagree-about-max-jobs.md)
- [UX-376](UX-0376-the-census-cannot-see-a-tool-this-build-produced.md) — [the census cannot see a tool this build produced, and the spine policy believes it](UX-0376-the-census-cannot-see-a-tool-this-build-produced.md)
- [UX-385](UX-0385-a-capture-cannot-detect-the-binary-it-never-saw.md) — [a capture cannot detect the binary it never saw](UX-0385-a-capture-cannot-detect-the-binary-it-never-saw.md)
- [UX-405](UX-0405-a-relative-project-forfeits-plane-2-in-silence.md) — [a relative `--project` forfeits Plane 2 in silence](UX-0405-a-relative-project-forfeits-plane-2-in-silence.md)
- [UX-410](UX-0410-a-project-flag-that-is-not-a-project-builds-one-anyway.md) — [a `--project` that is not a project builds one anyway](UX-0410-a-project-flag-that-is-not-a-project-builds-one-anyway.md)
- [UX-406](UX-0406-the-spine-counts-every-process-twice-in-the-trace.md) — [the spine counts every process twice in the trace](UX-0406-the-spine-counts-every-process-twice-in-the-trace.md)
- [UX-395](UX-0395-format-chrome-silently-drops-the-flows-and-counters.md) — [`--format chrome` silently drops the flows and counters](UX-0395-format-chrome-silently-drops-the-flows-and-counters.md)
- [UX-465](UX-0465-a-project-generator-for-real-builds.md) — [nothing generates a BuildStream project, so axes D, F and G are hand-authored or absent](UX-0465-a-project-generator-for-real-builds.md)
- [UX-470](UX-0470-what-the-planes-could-capture-and-do-not.md) — [nothing compares a plane's capability with the records it writes](UX-0470-what-the-planes-could-capture-and-do-not.md)
- [UX-487](UX-0487-a-spine-only-process-has-no-fault-or-io-counts.md) — [a spine-only process has no fault counts and no I/O, from a /proc read the spine already does](UX-0487-a-spine-only-process-has-no-fault-or-io-counts.md)
- [UX-518](UX-0518-one-buildstream-startup-per-element.md) — [the snapshot's tail pays one BuildStream startup per element](UX-0518-one-buildstream-startup-per-element.md)
- [UX-519](UX-0519-the-snapshot-tail-goes-quiet.md) — [the snapshot's tail goes quiet in the one phase that has no line](UX-0519-the-snapshot-tail-goes-quiet.md)
- [UX-514](UX-0514-the-schedule-can-never-capture-a-second-commit.md) — [the capture schedule can never produce a second commit](UX-0514-the-schedule-can-never-capture-a-second-commit.md)
- [UX-530](UX-0530-a-real-capture-reaches-the-track-ceiling-and-loses-the-timeline.md) — [a real capture reaches the track ceiling, and the timeline is dropped whole](UX-0530-a-real-capture-reaches-the-track-ceiling-and-loses-the-timeline.md)

**viewer**

- [UX-342](UX-0342-the-export-ships-six-schemas-nothing-can-resolve.md) — [the export ships six schemas nothing can resolve](UX-0342-the-export-ships-six-schemas-nothing-can-resolve.md)
- [UX-346](UX-0346-two-thirds-of-the-page-is-the-schemas-own-sentences.md) — [two thirds of the page is the schema's own sentences](UX-0346-two-thirds-of-the-page-is-the-schemas-own-sentences.md)
- [UX-347](UX-0347-the-click-budget-is-satisfied-by-never-folding.md) — [the click budget is satisfied by never folding](UX-0347-the-click-budget-is-satisfied-by-never-folding.md)
- [UX-348](UX-0348-the-two-capabilities-the-tool-is-for-are-a-closed-fold-and-a-stub.md) — [the two capabilities the tool is for are a closed fold and a stub](UX-0348-the-two-capabilities-the-tool-is-for-are-a-closed-fold-and-a-stub.md)
- [UX-351](UX-0351-the-label-prints-the-unit-the-value-already-carries.md) — [the label prints the unit the value already carries](UX-0351-the-label-prints-the-unit-the-value-already-carries.md)
- [UX-350](UX-0350-the-shape-channel-is-written-and-unbuilt.md) — [the shape channel is written and unbuilt](UX-0350-the-shape-channel-is-written-and-unbuilt.md)
- [UX-349](UX-0349-the-table-tools-do-not-scale-with-the-table.md) — [the table tools do not scale with the table](UX-0349-the-table-tools-do-not-scale-with-the-table.md)
- [UX-355](UX-0355-a-fold-that-expands-nothing-and-a-copy-that-says-nothing.md) — [a fold that expands nothing, and a copy that says nothing](UX-0355-a-fold-that-expands-nothing-and-a-copy-that-says-nothing.md)
- [UX-356](UX-0356-the-merge-keeps-four-of-twenty-eight-fields.md) — [the element join is "merged into the element table", and the merge keeps four of its twenty-eight fields](UX-0356-the-merge-keeps-four-of-twenty-eight-fields.md)
- [UX-357](UX-0357-the-provenance-shows-the-claim-and-withholds-the-rule.md) — [the provenance section shows the claim and withholds the rule](UX-0357-the-provenance-shows-the-claim-and-withholds-the-rule.md)
- [UX-361](UX-0361-the-drawing-vocabulary-is-two-shapes.md) — [the drawing vocabulary is two shapes, and the tool's central claim has neither](UX-0361-the-drawing-vocabulary-is-two-shapes.md)
- [UX-360](UX-0360-folding-paid-the-distance-and-the-volume-grew.md) — [folding paid the distance, and the volume grew by a third](UX-0360-folding-paid-the-distance-and-the-volume-grew.md)
- [UX-362](UX-0362-the-absence-sentence-claims-a-plane-it-does-not-own.md) — [the Plane 2 absence sentence claims a timeline it does not own](UX-0362-the-absence-sentence-claims-a-plane-it-does-not-own.md)
- [UX-364](UX-0364-the-perfetto-lead-promises-a-plane-the-trace-does-not-carry.md) — [the Perfetto lead promises a plane the trace does not carry](UX-0364-the-perfetto-lead-promises-a-plane-the-trace-does-not-carry.md)
- [UX-369](UX-0369-the-query-library-substitutes-one-projects-element.md) — [the query library substitutes one project's element name](UX-0369-the-query-library-substitutes-one-projects-element.md)
- [UX-367](UX-0367-the-volume-budget-is-enforced-at-eleven-elements.md) — [the volume budget is enforced at eleven elements](UX-0367-the-volume-budget-is-enforced-at-eleven-elements.md)
- [UX-368](UX-0368-no-finding-carries-a-perfetto-query.md) — [no finding carries a Perfetto query](UX-0368-no-finding-carries-a-perfetto-query.md)
- [UX-366](UX-0366-all-rows-shows-twenty-five-of-twelve-hundred.md) — ["All rows" shows 25 of 1,202](UX-0366-all-rows-shows-twenty-five-of-twelve-hundred.md)
- [UX-370](UX-0370-plane-twos-frequency-and-time-do-not-reach-the-page.md) — [Plane 2's frequency and time do not reach the page](UX-0370-plane-twos-frequency-and-time-do-not-reach-the-page.md)
- [UX-371](UX-0371-a-fifth-of-the-page-is-repeated-text.md) — [a fifth of the page is repeated text](UX-0371-a-fifth-of-the-page-is-repeated-text.md)
- [UX-372](UX-0372-the-page-has-one-reader.md) — [the page has one reader](UX-0372-the-page-has-one-reader.md)
- [UX-373](UX-0373-two-satellite-pages-for-one-handoff.md) — [two satellite pages for one handoff](UX-0373-two-satellite-pages-for-one-handoff.md)
- [UX-374](UX-0374-the-page-renames-the-readers-elements.md) — [the page renames the reader's elements and programs](UX-0374-the-page-renames-the-readers-elements.md)
- [UX-380](UX-0380-the-trace-says-what-an-element-is-never-where-it-sits.md) — [the trace says what an element is, never where it sits](UX-0380-the-trace-says-what-an-element-is-never-where-it-sits.md)
- [UX-383](UX-0383-plane-2s-per-element-blocks-reach-the-terminal-not-the-page.md) — [Plane 2's per-element blocks reach the terminal, not the page](UX-0383-plane-2s-per-element-blocks-reach-the-terminal-not-the-page.md)
- [UX-398](UX-0398-the-library-question-measured-against-the-factory.md) — [the library question, measured against the factory](UX-0398-the-library-question-measured-against-the-factory.md)
- [UX-399](UX-0399-the-browser-is-the-library.md) — [the browser is the library](UX-0399-the-browser-is-the-library.md)
- [UX-388](UX-0388-an-empty-population-disappears-without-a-word.md) — [an empty population disappears without a word](UX-0388-an-empty-population-disappears-without-a-word.md)
- [UX-391](UX-0391-wall-clock-share-shows-the-reader-a-composite-key.md) — [`wall_clock_share_us` shows the reader a composite key](UX-0391-wall-clock-share-shows-the-reader-a-composite-key.md)
- [UX-389](UX-0389-fourteen-plane-two-blocks-reach-no-browser.md) — [fourteen of twenty-five Plane 2 blocks reach no browser](UX-0389-fourteen-plane-two-blocks-reach-no-browser.md)
- [UX-390](UX-0390-attribution-and-its-hints-are-one-population-in-two-sections.md) — [attribution and its hints are one population in two sections](UX-0390-attribution-and-its-hints-are-one-population-in-two-sections.md)
- [UX-392](UX-0392-thirty-one-tables-and-one-search-box.md) — [thirty-one tables, one search box](UX-0392-thirty-one-tables-and-one-search-box.md)
- [UX-393](UX-0393-nothing-moves-to-the-next-section-or-back-to-the-top.md) — [nothing moves to the next section, or back to the top](UX-0393-nothing-moves-to-the-next-section-or-back-to-the-top.md)
- [UX-396](UX-0396-sixteen-of-forty-four-sections-draw-something.md) — [sixteen of forty-four sections draw something](UX-0396-sixteen-of-forty-four-sections-draw-something.md)
- [UX-397](UX-0397-the-perfetto-handoff-sits-outside-the-pinned-rail.md) — [the Perfetto handoff sits outside the pinned rail](UX-0397-the-perfetto-handoff-sits-outside-the-pinned-rail.md)
- [UX-394](UX-0394-nothing-in-the-page-moves-between-runs.md) — [nothing in the page moves between runs](UX-0394-nothing-in-the-page-moves-between-runs.md)
- [UX-413](UX-0413-a-population-with-nothing-to-rank-by-is-never-bounded.md) — [a population with nothing to rank by is never bounded](UX-0413-a-population-with-nothing-to-rank-by-is-never-bounded.md)
- [UX-412](UX-0412-a-table-of-one-says-one-rows.md) — [a table of one says "1 rows"](UX-0412-a-table-of-one-says-one-rows.md)
- [UX-414](UX-0414-two-sections-fall-into-everything-else.md) — [two sections fall into "Everything else", and the guard's fixture cannot see it](UX-0414-two-sections-fall-into-everything-else.md)
- [UX-411](UX-0411-a-ranked-map-has-no-instrument.md) — [a ranked map has no instrument](UX-0411-a-ranked-map-has-no-instrument.md)
- [UX-419](UX-0419-a-map-population-is-bounded-by-nothing.md) — [a map population is bounded by nothing](UX-0419-a-map-population-is-bounded-by-nothing.md)
- [UX-434](UX-0434-the-graph-shape-query-collapses-every-level.md) — [the graph-shape query collapses every level into one row](UX-0434-the-graph-shape-query-collapses-every-level.md)
- [UX-430](UX-0430-the-trace-budget-counts-bytes-and-perfetto-spends-tracks.md) — [the trace budget counts bytes, and Perfetto spends tracks](UX-0430-the-trace-budget-counts-bytes-and-perfetto-spends-tracks.md)
- [UX-433](UX-0433-nothing-pivots-by-executable.md) — [nothing pivots by executable, because no annotation names one](UX-0433-nothing-pivots-by-executable.md)
- [UX-429](UX-0429-a-command-is-rendered-as-a-list-of-its-words.md) — [a command is rendered as a list of its words](UX-0429-a-command-is-rendered-as-a-list-of-its-words.md)
- [UX-436](UX-0436-the-page-has-no-control-style.md) — [forty-four controls are the browser's, not the page's](UX-0436-the-page-has-no-control-style.md)
- [UX-435](UX-0435-the-handoff-box-is-measured-in-the-mode-it-is-smallest.md) — [the handoff box is measured in the mode where it is smallest](UX-0435-the-handoff-box-is-measured-in-the-mode-it-is-smallest.md)
- [UX-437](UX-0437-the-host-series-is-captured-and-read-by-nobody.md) — [the host memory series is captured every run and read by nobody](UX-0437-the-host-series-is-captured-and-read-by-nobody.md)
- [UX-443](UX-0443-the-served-handoff-cannot-count-its-own-edges.md) — [the served handoff cannot count its own edges](UX-0443-the-served-handoff-cannot-count-its-own-edges.md)
- [UX-448](UX-0448-the-element-scoped-pivot-has-no-finding-to-arrive-from.md) — [the element-scoped pivot has no finding to arrive from](UX-0448-the-element-scoped-pivot-has-no-finding-to-arrive-from.md)
- [UX-451](UX-0451-the-handoff-refusal-sentence-has-the-rails-width.md) — [the hand-off's refusal sentence is written into a 208px column](UX-0451-the-handoff-refusal-sentence-has-the-rails-width.md)
- [UX-521](UX-0521-the-handoff-goes-quiet-for-minutes.md) — [the Perfetto handoff goes quiet, and cannot tell working from refused](UX-0521-the-handoff-goes-quiet-for-minutes.md)
- [UX-532](UX-0532-the-table-tools-read-the-nested-tables-rows-as-their-own.md) — [the table tools read the nested tables' rows as their own](UX-0532-the-table-tools-read-the-nested-tables-rows-as-their-own.md)
- [UX-534](UX-0534-focus-answers-far-above-the-button.md) — [Focus answers 25,501 px above the button](UX-0534-focus-answers-far-above-the-button.md)
- [UX-536](UX-0536-four-controls-that-say-less-than-they-do.md) — [four controls that say less than they do](UX-0536-four-controls-that-say-less-than-they-do.md)
- [UX-527](UX-0527-one-control-has-an-option-per-element.md) — [one control has an option per element](UX-0527-one-control-has-an-option-per-element.md)
- [UX-528](UX-0528-the-served-store-section-grows-with-every-snapshot.md) — [the served store section and run picker grow with every snapshot](UX-0528-the-served-store-section-grows-with-every-snapshot.md)
- [UX-535](UX-0535-one-fact-published-twice-drawn-twice-listed-twice.md) — [one fact published twice, drawn twice, listed twice](UX-0535-one-fact-published-twice-drawn-twice-listed-twice.md)
- [UX-533](UX-0533-the-served-page-is-the-capture-time-analysis.md) — [the served page is the capture-time analysis, and cannot say so](UX-0533-the-served-page-is-the-capture-time-analysis.md)
- [UX-529](UX-0529-the-export-data-half-is-unbounded-and-holds-each-row-twice.md) — [the export's data half is unbounded, and holds each row twice](UX-0529-the-export-data-half-is-unbounded-and-holds-each-row-twice.md)

**store**

- [UX-96](UX-0096-the-baseline-set-exists-but-assembling-it-is-a-scavenger-hunt.md) — [the baseline set exists, but assembling it is a scavenger hunt](UX-0096-the-baseline-set-exists-but-assembling-it-is-a-scavenger-hunt.md)
- [UX-92](UX-0092-cache-effectiveness-is-invisible-to-the-tool.md) — [cache effectiveness — hits, misses, churn, trends — is invisible to the tool](UX-0092-cache-effectiveness-is-invisible-to-the-tool.md)
- [UX-520](UX-0520-a-run-bundle-you-can-carry.md) — [a capture you can carry to another machine in one command](UX-0520-a-run-bundle-you-can-carry.md)

**guards**

- [UX-337](UX-0337-the-two-viewer-modules-split-along-their-seams.md) — [the two viewer modules split along their seams](UX-0337-the-two-viewer-modules-split-along-their-seams.md)
- [UX-340](UX-0340-the-graph-was-derived-with-a-broken-instrument.md) — [the graph was derived with a broken instrument](UX-0340-the-graph-was-derived-with-a-broken-instrument.md)
- [UX-359](UX-0359-every-guard-measures-a-plane-2-stripped-page.md) — [every guard measures a page with Plane 2 stripped out of it](UX-0359-every-guard-measures-a-plane-2-stripped-page.md)
- [UX-358](UX-0358-no-fixture-can-render-a-timeline.md) — [no committed fixture can render a timeline, so the handoff the tool is for is never exercised](UX-0358-no-fixture-can-render-a-timeline.md)
- [UX-363](UX-0363-the-small-tier-budget-is-nine-tenths-headroom.md) — [the small tier's budget is nine-tenths headroom](UX-0363-the-small-tier-budget-is-nine-tenths-headroom.md)
- [UX-387](UX-0387-the-close-check-is-blind-to-the-mismatch-it-exists-for.md) — [the close check is blind to the mismatch it exists for](UX-0387-the-close-check-is-blind-to-the-mismatch-it-exists-for.md)
- [UX-400](UX-0400-every-population-is-tested-at-zero-one-and-many.md) — [every population is tested at zero, one and many](UX-0400-every-population-is-tested-at-zero-one-and-many.md)
- [UX-401](UX-0401-no-key-is-terminal-only-in-silence.md) — [no key is terminal-only in silence](UX-0401-no-key-is-terminal-only-in-silence.md)
- [UX-404](UX-0404-the-unit-census-stops-at-the-analyze-door.md) — [the unit census stops at the analyze door](UX-0404-the-unit-census-stops-at-the-analyze-door.md)
- [UX-402](UX-0402-the-journey-is-a-guard-with-an-answer-key.md) — [the journey is a guard with an answer key](UX-0402-the-journey-is-a-guard-with-an-answer-key.md)
- [UX-403](UX-0403-the-guard-census.md) — [the guard census — every guard proves it can fail](UX-0403-the-guard-census.md)
- [UX-415](UX-0415-the-shared-probe-is-always-served.md) — [the shared node probe says `file:` and always measures `http:`](UX-0415-the-shared-probe-is-always-served.md)
- [UX-418](UX-0418-a-slow-file-is-small-until-ci-times-out.md) — [a slow file is small until CI times out](UX-0418-a-slow-file-is-small-until-ci-times-out.md)
- [UX-420](UX-0420-ci-cannot-check-tier-drift-without-its-own-clock.md) — [CI cannot check tier drift without a reference of its own](UX-0420-ci-cannot-check-tier-drift-without-its-own-clock.md)
- [UX-424](UX-0424-the-bulk-add-hook-reads-command-text.md) — [the bulk-add hook matches command text, not command effect](UX-0424-the-bulk-add-hook-reads-command-text.md)
- [UX-423](UX-0423-the-drift-shift-is-a-median-taken-at-the-noise-floor.md) — [the drift shift is a median taken at the noise floor](UX-0423-the-drift-shift-is-a-median-taken-at-the-noise-floor.md)
- [UX-421](UX-0421-the-small-tier-budget-window-is-a-second-wide.md) — [the small tier's budget window is a second wide](UX-0421-the-small-tier-budget-window-is-a-second-wide.md)
- [UX-422](UX-0422-the-layout-ratio-guard-measures-the-runner-too.md) — [the layout-cost guard measures the runner as well as the page](UX-0422-the-layout-ratio-guard-measures-the-runner-too.md)
- [UX-427](UX-0427-the-reference-can-be-recorded-but-never-refreshed.md) — [the CI reference can be recorded but never refreshed](UX-0427-the-reference-can-be-recorded-but-never-refreshed.md)
- [UX-428](UX-0428-the-run-picker-probe-reads-before-the-page-renders.md) — [the run-picker probe reads the page before it has rendered](UX-0428-the-run-picker-probe-reads-before-the-page-renders.md)
- [UX-432](UX-0432-the-question-library-had-never-been-run.md) — [the question library had never been run](UX-0432-the-question-library-had-never-been-run.md)
- [UX-441](UX-0441-the-reference-dump-buries-the-failure-it-follows.md) — [the reference dump buries the failure it follows](UX-0441-the-reference-dump-buries-the-failure-it-follows.md)
- [UX-442](UX-0442-one-slow-sample-reddens-ci.md) — [one slow sample reddens CI, and nothing asks it to repeat](UX-0442-one-slow-sample-reddens-ci.md)
- [UX-444](UX-0444-the-page-budget-and-the-data-ratio-have-converged.md) — [the page budget and the data ratio have converged](UX-0444-the-page-budget-and-the-data-ratio-have-converged.md)
- [UX-445](UX-0445-the-track-bound-is-one-sample.md) — [the track bound is one sample, and nothing has measured the cost it stands for](UX-0445-the-track-bound-is-one-sample.md)
- [UX-453](UX-0453-the-clock-bracket-compares-a-rounded-stamp.md) — [the clock bracket compares a rounded stamp with unrounded readings](UX-0453-the-clock-bracket-compares-a-rounded-stamp.md)
- [UX-454](UX-0454-closing-a-task-twice-doubles-its-status-word.md) — [closing a task twice doubles its status word](UX-0454-closing-a-task-twice-doubles-its-status-word.md)
- [UX-449](UX-0449-a-skip-reason-is-only-checked-where-the-skip-happens.md) — [a skip reason is only checked where the skip happens](UX-0449-a-skip-reason-is-only-checked-where-the-skip-happens.md)
- [UX-450](UX-0450-two-viewer-modules-sit-exactly-on-the-ceiling.md) — [two viewer modules sit exactly on the line-count ceiling](UX-0450-two-viewer-modules-sit-exactly-on-the-ceiling.md)
- [UX-457](UX-0457-the-reference-refresh-artifact-is-unreachable.md) — [the reference can only be refreshed from a host the round cannot reach](UX-0457-the-reference-refresh-artifact-is-unreachable.md)
- [UX-455](UX-0455-two-files-drift-past-their-tier-and-the-parse-is-red.md) — [two files have grown past the tier they are listed in](UX-0455-two-files-drift-past-their-tier-and-the-parse-is-red.md)
- [UX-456](UX-0456-two-bst-gated-guards-are-at-the-noise-floor.md) — [two bst-gated guards fail on the runner and not on the diff](UX-0456-two-bst-gated-guards-are-at-the-noise-floor.md)
- [UX-462](UX-0462-following-the-examples-readme-reddens-the-suite.md) — [following `examples/README.md` reddens the suite](UX-0462-following-the-examples-readme-reddens-the-suite.md)
- [UX-463](UX-0463-which-topologies-do-we-actually-need.md) — [which topologies we actually need, and why that set](UX-0463-which-topologies-do-we-actually-need.md)
- [UX-464](UX-0464-the-curated-covering-set.md) — [the curated covering set — T1, T2, T3 and half of T4](UX-0464-the-curated-covering-set.md)
- [UX-458](UX-0458-the-drift-factor-was-never-sized-from-data.md) — [the drift factor is a starting value nothing has re-measured](UX-0458-the-drift-factor-was-never-sized-from-data.md)
- [UX-480](UX-0480-the-bst-tier-pin-is-written-twice-and-read-once.md) — [the bst-tier pin is written twice and the guard read the half that does not decide](UX-0480-the-bst-tier-pin-is-written-twice-and-read-once.md)
- [UX-482](UX-0482-the-browser-harness-waits-a-duration-not-a-condition.md) — [the browser harness waited a duration where it meant a condition](UX-0482-the-browser-harness-waits-a-duration-not-a-condition.md)
- [UX-459](UX-0459-seven-examples-keep-nothing-analysable.md) — [eight findings are reachable by nothing a clone has](UX-0459-seven-examples-keep-nothing-analysable.md)
- [UX-460](UX-0460-no-guard-says-which-findings-a-fixture-produces.md) — [nothing says which findings the fixtures can actually produce](UX-0460-no-guard-says-which-findings-a-fixture-produces.md)
- [UX-473](UX-0473-ci-never-builds-a-generated-project.md) — [nothing in CI builds a generated project](UX-0473-ci-never-builds-a-generated-project.md)
- [UX-484](UX-0484-the-step-that-must-not-use-set-e-was-given-it-by-the-runner.md) — [the step that must not use `set -e` was given it by the runner, and its guard read the wrong half](UX-0484-the-step-that-must-not-use-set-e-was-given-it-by-the-runner.md)
- [UX-476](UX-0476-an-untouched-file-crossed-on-two-consecutive-runs.md) — [the falsifier `UX-458` named arrived on the very next run](UX-0476-an-untouched-file-crossed-on-two-consecutive-runs.md)
- [UX-486](UX-0486-a-committed-analysis-fixture-drifts-from-the-analyzer.md) — [a committed analysis fixture drifts from the analyzer, and one clause out of many noticed](UX-0486-a-committed-analysis-fixture-drifts-from-the-analyzer.md)
- [UX-488](UX-0488-the-wholesale-re-record-the-drift-rule-change-has-to-follow.md) — [the reference is five hand-appends deep, and the re-record has to come after the rule change](UX-0488-the-wholesale-re-record-the-drift-rule-change-has-to-follow.md)
- [UX-494](UX-0494-the-explanation-filter-names-the-whole-suite.md) — [the drift gate's explanation filter names the whole suite, so it explains nothing](UX-0494-the-explanation-filter-names-the-whole-suite.md)
- [UX-497](UX-0497-the-register-is-a-budget.md) — [the register is a budget, not a preference](UX-0497-the-register-is-a-budget.md)
- [UX-503](UX-0503-a-new-test-file-records-itself.md) — [a new test file records itself in the CI reference](UX-0503-a-new-test-file-records-itself.md)
- [UX-508](UX-0508-a-stale-verdict-fires-on-one-sample.md) — [the whole-runner verdict fires on one sample](UX-0508-a-stale-verdict-fires-on-one-sample.md)
- [UX-504](UX-0504-an-implementer-agent-that-may-edit-in-a-worktree.md) — [an implementer agent that may edit, in a worktree only](UX-0504-an-implementer-agent-that-may-edit-in-a-worktree.md)
- [UX-509](UX-0509-the-agent-worktree-is-inside-the-lint.md) — [a parallel track's worktree is inside the tree that lints it](UX-0509-the-agent-worktree-is-inside-the-lint.md)
- [UX-490](UX-0490-the-clone-guard-cannot-see-an-absolute-path.md) — [the guard against one-machine data cannot see an absolute path](UX-0490-the-clone-guard-cannot-see-an-absolute-path.md)
- [UX-491](UX-0491-the-gate-line-has-no-route-for-a-reader-without-the-log.md) — [the drift gate's own line has no route a reader can reach](UX-0491-the-gate-line-has-no-route-for-a-reader-without-the-log.md)
- [UX-495](UX-0495-three-browser-guards-swing-under-parallel-load.md) — [three browser guards swing 1.5-2.3x under parallel load](UX-0495-three-browser-guards-swing-under-parallel-load.md)
- [UX-496](UX-0496-a-one-run-re-record-bakes-in-one-sample-per-file.md) — [a wholesale re-record samples every file once, and the drift factor has never been sized against that](UX-0496-a-one-run-re-record-bakes-in-one-sample-per-file.md)
- [UX-489](UX-0489-the-answer-key-asserts-a-ranking-with-no-margin.md) — [the answer key asserts a ranking with no margin, on a build it runs for real](UX-0489-the-answer-key-asserts-a-ranking-with-no-margin.md)
- [UX-512](UX-0512-an-exemption-for-a-build-artifact.md) — [a guard is red on any tree whose `__pycache__` was cleared](UX-0512-an-exemption-for-a-build-artifact.md)
- [UX-515](UX-0515-a-guard-that-ci-turns-red-by-adopting.md) — [a guard the reference-adopt commit turns red](UX-0515-a-guard-that-ci-turns-red-by-adopting.md)
- [UX-513](UX-0513-two-guards-are-red-until-you-commit.md) — [two guards are red while a tier edit is uncommitted](UX-0513-two-guards-are-red-until-you-commit.md)
- [UX-510](UX-0510-a-track-starts-from-a-stale-base.md) — [a parallel track starts from a base the orchestrator has left behind](UX-0510-a-track-starts-from-a-stale-base.md)
- [UX-523](UX-0523-forty-files-boot-the-same-page.md) — [forty files boot the same page](UX-0523-forty-files-boot-the-same-page.md)
- [UX-522](UX-0522-the-selector-runs-last-and-carries-the-census.md) — [the selector runs last, and carries the census](UX-0522-the-selector-runs-last-and-carries-the-census.md)
- [UX-524](UX-0524-the-touching-map-is-measured-in-ci.md) — [the touching map is measured in CI, not grepped](UX-0524-the-touching-map-is-measured-in-ci.md)
- [UX-526](UX-0526-the-large-budget-class-is-breached-at-its-top.md) — [the large budget class is measured at its bottom and breached at its top](UX-0526-the-large-budget-class-is-breached-at-its-top.md)
- [UX-538](UX-0538-a-ranking-guard-under-contention.md) — [a guard that ranks a real build's seconds cannot hold under load](UX-0538-a-ranking-guard-under-contention.md)
- [UX-537](UX-0537-forty-eight-documents-and-one-shim.md) — [forty-eight hand-built documents, and the shared shim they were to become](UX-0537-forty-eight-documents-and-one-shim.md)

**docs**

- [UX-331](UX-0331-the-readme-excerpt-and-the-sentence-that-contradicts-itself.md) — [the README excerpt, and the sentence that contradicts itself](UX-0331-the-readme-excerpt-and-the-sentence-that-contradicts-itself.md)
- [UX-330](UX-0330-the-stranger-needs-a-seed.md) — [the stranger needs a seed](UX-0330-the-stranger-needs-a-seed.md)
- [UX-353](UX-0353-the-roles-table-serves-a-contract-nothing-writes.md) — [the roles table serves a contract nothing writes](UX-0353-the-roles-table-serves-a-contract-nothing-writes.md)
- [UX-352](UX-0352-the-architecture-counts-seven-chapters-and-the-page-has-eight.md) — [the architecture counts seven chapters and the page has eight](UX-0352-the-architecture-counts-seven-chapters-and-the-page-has-eight.md)
- [UX-417](UX-0417-the-export-figures-are-four-rounds-stale.md) — [the guide's export figures are stale by 3.2x](UX-0417-the-export-figures-are-four-rounds-stale.md)
- [UX-416](UX-0416-the-page-moves-between-runs-and-no-document-says-so.md) — [the page moves between runs, and no document says so](UX-0416-the-page-moves-between-runs-and-no-document-says-so.md)
- [UX-425](UX-0425-the-proxy-instrument-class-is-in-no-rule-document.md) — [the defect class this repository hits most often is in no rule document](UX-0425-the-proxy-instrument-class-is-in-no-rule-document.md)
- [UX-426](UX-0426-ci-is-the-only-instrument-for-some-claims.md) — [the sessions' loop does not know that CI is sometimes the only instrument](UX-0426-ci-is-the-only-instrument-for-some-claims.md)
- [UX-446](UX-0446-a-third-ceiling-no-reader-facing-document-has.md) — [a third ceiling, and no reader-facing document has it](UX-0446-a-third-ceiling-no-reader-facing-document-has.md)
- [UX-447](UX-0447-the-reference-refresh-route-is-in-no-contributor-document.md) — [the reference-refresh route is in no contributor document](UX-0447-the-reference-refresh-route-is-in-no-contributor-document.md)
- [UX-468](UX-0468-the-guided-walk-against-a-planted-defect.md) — [no walk of the guides has ever started from a defect somebody planted](UX-0468-the-guided-walk-against-a-planted-defect.md)
- [UX-471](UX-0471-the-day-one-summary-counts-421-of-468.md) — [the day-one summary counts 421 task files and the tree has 468](UX-0471-the-day-one-summary-counts-421-of-468.md)
- [UX-472](UX-0472-the-architecture-has-no-paragraph-for-the-generators.md) — [the architecture says one script needs no `bst`, and now three tools do not fit the sentence](UX-0472-the-architecture-has-no-paragraph-for-the-generators.md)
- [UX-498](UX-0498-a-filing-is-decomposed-before-it-is-coded.md) — [a filing is decomposed before it is coded](UX-0498-a-filing-is-decomposed-before-it-is-coded.md)
- [UX-499](UX-0499-where-is-it-costs-one-line-not-one-file.md) — ["where is it" costs one line, not one file](UX-0499-where-is-it-costs-one-line-not-one-file.md)
- [UX-501](UX-0501-the-index-is-derived-not-merged.md) — [the index is derived, not merged](UX-0501-the-index-is-derived-not-merged.md)
- [UX-505](UX-0505-the-rules-card.md) — [the rules card — the guide's rules on one page, its reasons behind it](UX-0505-the-rules-card.md)
- [UX-506](UX-0506-the-outcome-skeleton-fits-the-register.md) — [the Outcome skeleton fits the register](UX-0506-the-outcome-skeleton-fits-the-register.md)
- [UX-502](UX-0502-the-comment-that-tells-the-story.md) — [the comment that tells the story](UX-0502-the-comment-that-tells-the-story.md)
- [UX-492](UX-0492-the-readme-verbatim-block-is-no-longer-verbatim.md) — [the README's "verbatim" real-project block prints a sentence the tool can no longer produce](UX-0492-the-readme-verbatim-block-is-no-longer-verbatim.md)
- [UX-493](UX-0493-a-moved-bound-left-an-earlier-task-file-asserting-the-old-one.md) — [a bound moved and the task file that presents it as current was not annotated](UX-0493-a-moved-bound-left-an-earlier-task-file-asserting-the-old-one.md)
- [UX-511](UX-0511-the-real-project-guide-teaches-a-retired-reading.md) — [the guide the README sends readers to teaches a retired reading as current](UX-0511-the-real-project-guide-teaches-a-retired-reading.md)
- [UX-507](UX-0507-the-unclassified-bucket.md) — [223 closed rows are in no topic](UX-0507-the-unclassified-bucket.md)
- [UX-516](UX-0516-the-ci-owners-page-teaches-a-command-that-exits-6.md) — [the CI owner's page teaches a command that exits 6 on this repository's own refs](UX-0516-the-ci-owners-page-teaches-a-command-that-exits-6.md)
- [UX-517](UX-0517-a-closed-outcome-quotes-a-bucket-that-is-now-empty.md) — [a closed Outcome quotes a bucket that is now empty](UX-0517-a-closed-outcome-quotes-a-bucket-that-is-now-empty.md)
- [UX-525](UX-0525-a-track-costs-tokens-and-nobody-knows-where.md) — [a track costs 81k-131k tokens, and nobody knows where](UX-0525-a-track-costs-tokens-and-nobody-knows-where.md)
- [UX-500](UX-0500-the-batch-gate-measured-against-the-per-item-suite.md) — [the batch gate, measured against the per-item suite](UX-0500-the-batch-gate-measured-against-the-per-item-suite.md)
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

- [UX-259](UX-0259-a-blast-number-has-no-scale.md) — `753 downstream` is p99.9 in a 1,202-element graph and unremarkable in a graph of forty thousand — and the number is what travels into a ticket while the rank stays behind.
- [UX-253](UX-0253-the-aggregate-mixes-contract-sets-without-saying-so.md) — `UX-250` settled the two-run rule and its clause 2 asked for the many-run case, which was deliberately not implemented: with thirty runs there can be three contract sets and the questions that follow…
- [UX-260](UX-0260-the-other-quantities-that-need-a-scale.md) — Where else a percentile belongs, argued per quantity rather than applied everywhere - `UX-259` gave blast radius a scale and the same question stood for duration, sandbox tax and process count
- [UX-288](UX-0288-the-contract-publishes-membership-three-ways.md) — `analyze/v1` published the same leaf membership three times and the same critical path twice, each a subset of the one element table, and no guard said the copies must agree
- [UX-291](UX-0291-a-finding-carries-its-numbers-three-times.md) — twenty-three numbers across nine findings, ten carried a second time in `provenance.evidence[].value` and twenty a third time in `copy_text` - with no rule saying they must agree
- [UX-275](UX-0275-the-capacity-recommendation-is-text-only.md) — the tool's answer to the question this backlog opened with - what should `--builders` be, and which constraint is the reason - was computed, rendered by the text report, and dropped by the JSON…
- [UX-290](UX-0290-the-schema-does-not-describe-its-tuples.md) — `[["app.bst", 8], …]` was described by nothing, so the page named its columns after their *position* - 78 of the report's headers named a place in a data structure rather than a measure
- [UX-328](UX-0328-schema-answers-for-everything-that-emits-one.md) — [--schema answers for everything that emits one](UX-0328-schema-answers-for-everything-that-emits-one.md)
- [UX-339](UX-0339-the-capacity-sweep-has-no-contract.md) — [the capacity sweep has no contract](UX-0339-the-capacity-sweep-has-no-contract.md)

**cli**

- [UX-326](UX-0326-the-tools-own-sentences-are-contracts.md) — the "Next:" block printed `bga snapshot /abs/path/to/project`, which crashed when run verbatim, and `bga compare @prev @last` printed "(--allow-mismatch was given)" with no flags passed

**analysis**

- [UX-258](UX-0258-the-blast-ranking-tells-you-to-optimize-the-base-image.md) — The blast ranking put `toolchain.bst` first — an `import` element with 1,201 dependents, `is_structural_kind: true` on the very entry the ranking ordered.
- [UX-329](UX-0329-the-terminal-and-the-viewer-disagree-about-plane-2.md) — [the terminal and the viewer disagree about Plane 2](UX-0329-the-terminal-and-the-viewer-disagree-about-plane-2.md)

**capture**

- [UX-313](UX-0313-the-record-list-is-the-floor-that-is-left.md) — `UX-297` left the record list as extraction's floor - 185.8 MB of a 221.1 MB peak on a 200,000-process trace - and asked whether a bounded reorder window could replace it, making extraction…
- [UX-324](UX-0324-a-capture-that-cannot-start-says-so-and-leaves-nothing.md) — on a machine without `bst`, `bga snapshot -- bst build all.bst` - the README's own first command - died in a 32-line `FileNotFoundError` traceback and left a debris snapshot behind, while `bga…
- [UX-297](UX-0297-extraction-streams-and-the-monolith-retires.md) — `summarize()` embedded the whole per-process record list in plane2.json - ~95% of a 1.5 GB monolith that no production reader consumed - and extraction then held the whole event list in RAM to…
- [UX-308](UX-0308-a-slice-that-says-what-bga-knows-about-it.md) — a slice said one thing - its name - and for Plane 2 that name is the command truncated to 120 characters, so the argv tail that tells two compiler invocations apart was not in the trace at all, while…
- [UX-310](UX-0310-the-counters-the-reserved-constant-was-waiting-for.md) — UX-298 pinned TYPE_COUNTER with the comment "reserved rather than used", and the three series the capture could fold went undrawn
- [UX-311](UX-0311-a-trace-that-knows-whose-build-it-was.md) — a trace file leaves the machine that made it and carried no identity at all - not which run, not which host, not whether the capture was complete - while the lane order was discovery order
- [UX-309](UX-0309-the-arrows-that-answer-why-now.md) — the dependency question is the one a timeline is *for* - an element ends, another begins, and whether that adjacency is causation is exactly what graph.json knows and the trace did not say;
- [UX-298](UX-0298-the-timeline-speaks-perfetto-natively.md) — the timeline was legacy Chrome JSON - a shape Perfetto tolerates rather than reads - assembled whole in memory and regenerated from the raw log on every handoff;

**viewer**

- [UX-254](UX-0254-the-contents-take-two-thirds-of-the-first-screen.md) — Reported from a real run: the contents occupy most of the first screen and read as content.
- [UX-255](UX-0255-the-heading-is-below-the-navigation.md) — The heading arrived at y=630, *after* the navigation, and carried less than the footer did - two lines of identity and nothing that qualifies the run
- [UX-262](UX-0262-a-long-critical-path-grows-a-section-without-bound.md) — `UX-187` capped the tables that grow with element count;
- [UX-263](UX-0263-the-pages-own-policy-refuses-its-drawings.md) — Reported from a real project: Chrome logs "Refused to apply inline style ...
- [UX-265](UX-0265-the-handoff-answers-the-read-but-not-the-preflight.md) — Reported from a real project: the Perfetto hand-off stopped working in latest Chrome, with "blocked by cors policy, no access control allow origin header is present on the requested resource"
- [UX-261](UX-0261-the-first-view-ranks-what-is-big.md) — The first screen met the reader with eleven near-identical blast counts;
- [UX-266](UX-0266-two-of-three-pages-run-nothing.md) — Reported from a real run: a CSP problem on `sql.html`.
- [UX-267](UX-0267-every-object-is-a-details-called-object.md) — Every object *and every array* rendered as `<details><summary>object</summary><pre>{raw JSON}</pre>` - 34 such cells and 32,393 characters of `<pre>` on a 44-element run, the largest 8,191 and…
- [UX-268](UX-0268-six-maps-are-one-table.md) — Six of the seven wide `signals` maps are the same element list rendered six times;
- [UX-269](UX-0269-a-long-field-shows-all-of-itself.md) — Field contents measured per field: 678 chars of `copy_text`, 572 of `capacity_model_note`, 293 of `attribution_hints.resource_wait_us` - all shown in full, always
- [UX-270](UX-0270-the-critical-path-is-its-own-section.md) — The critical path - the run's most important list - was a row inside a section named after a schema key
- [UX-271](UX-0271-the-rail-is-flat.md) — The rail is one flat list and the report renders 30+ sections;
- [UX-272](UX-0272-the-header-is-four-stacked-paragraphs.md) — The header stacks four block elements and was reported as too long
- [UX-277](UX-0277-every-table-cell-stringifies-its-own-structure.md) — `UX-267`'s width-not-depth rule was wired into `renderPairs` (which draws `<dd>` cells) and never into `buildTable` (which draws every `<td>`), so 6 cells rendered raw JSON, 11 joined arrays, one…
- [UX-289](UX-0289-one-element-table-many-presets.md) — the page drew 19 element tables over 13 populations and the one table every element is in carried 13 columns, because it served every question at once - and it had bounds and filters but **zero named…
- [UX-292](UX-0292-thirteen-tables-share-one-view-state-key.md) — `UX-211` keys a table's view state by the table's name and `renderStructured` named every nested table `value`, so thirteen tables answered to `f.value` - a filter typed into one landed, on the other…
- [UX-278](UX-0278-the-magnifier-opens-nothing-for-most-elements.md) — a magnifier that consumes the click and does nothing: the detail cap excluded 1,178 of 1,202 elements, so the affordance was absent for 98% of the run and dead where it was present
- [UX-279](UX-0279-forty-three-copy-controls-and-no-way-to-know-what-they-copy.md) — 43 copy controls, three vocabularies, `Copy` fourteen times over two different payloads, and not one `title` among them
- [UX-280](UX-0280-copy-as-markdown.md) — JSON pastes into a ticket as a code block somebody has to read
- [UX-284](UX-0284-the-table-tools-are-below-the-table-and-scroll-away.md) — the table tools sat below their table and scrolled away: 28 of 43 inputs started below the table they belong to, all 43 were `position: static`, and the jump box was at y=1236 on a page whose fold is…
- [UX-281](UX-0281-the-satellite-pages-are-dead-ends.md) — both satellite pages were dead ends;
- [UX-282](UX-0282-the-perfetto-fallback-is-below-the-button-that-fails.md) — *"Nothing opened? Use the direct link"* sat three paragraphs under the button it is about, read only by somebody who has just watched that button fail
- [UX-283](UX-0283-the-bottleneck-view-names-elements-you-cannot-reach.md) — the bottleneck block rendered all seven of its members and carried **zero** links out of the entire `structural` section - nine choke points, none clickable
- [UX-286](UX-0286-the-report-is-forty-eight-fragments-with-no-chapters.md) — forty-eight sections averaging 0.24 screens with nothing grouping them: a report read by scrolling past fragments, and a rail of thirty-one top-level entries
- [UX-285](UX-0285-the-identity-blocks-are-split-and-the-blast-box-is-last.md) — three identity blocks answering one question, split across the page - `summary` and `run_instance` at screens 1.4 and 1.6, `producer` at 10.9 of 18.8 - and the blast control, an interactive query, as…
- [UX-296](UX-0296-the-view-that-parses-nothing.md) — `bga view` on a real ~2 GB dual-plane snapshot froze in parsing and died of memory near server start: `serve()` built every payload before the socket existed, running every whole-file load path in…
- [UX-312](UX-0312-questions-for-the-trace-that-can-finally-answer-them.md) — the canned SQL library was track-scoped by `UX-210` and arg-scoped by `UX-204`, both against the legacy Chrome JSON trace;
- [UX-314](UX-0314-the-deep-link-perfetto-refuses-to-follow.md) — the `?url=` deep link was refused by ui.perfetto.dev's own `connect-src` on every port `bga view` binds, so the handoff that `UX-299` made the only transport above 4 MiB failed silently in the field
- [UX-316](UX-0316-exhibits-drawn-at-annotation-size.md) — every drawing shared one geometry - `SPARK_HEIGHT = 20` / `STRIP_HEIGHT = 8`, calibrated for the sparkline beside a table cell - so the three drawings that are their section's whole answer drew at…
- [UX-318](UX-0318-the-rabbit-hole-announces-its-depth.md) — a fold said how *wide* it was and nothing about how deep, and a nested table's own scroll sat inside a scrolling parent - so the reader could neither see the rabbit hole's depth nor reach all the…
- [UX-317](UX-0317-apparatus-in-its-place.md) — the save-the-trace sentence rendered in the sticky header, two blocks above the control it explains and paid for on every screen;
- [UX-319](UX-0319-the-chain-folds-and-the-clicks-are-counted.md) — the critical chain's element listing rendered whole - `UX-187` had folded the text report's chain and `UX-196` the drawn strip, and the third surface got neither - and nobody had ever measured what…
- [UX-321](UX-0321-the-question-that-can-never-answer.md) — `element-commands` filtered Plane 2 slices on `debug.element`, a key only Plane 1 carried, so it returned zero rows on every trace this emitter can write - silently, and the dictionary guard could…
- [UX-320](UX-0320-the-page-conforms-to-its-new-sections.md) — round 44 extended the visual contract with four sections, and the `UX-305` precedent says an extension is not real until the existing page is audited against it and the audit is a guard
- [UX-315](UX-0315-the-canned-why-renders-with-doubled-spaces.md) — every canned question's `why` renders with doubled spaces: the library concatenates each `why` across source lines and the file's convention began every continuation with a space while the previous…
- [UX-307](UX-0307-the-export-ships-the-source-comments.md) — the export inlines every viewer module and this project's modules are commented by design, so the argument for each rule was believed to ride into every attachment - 175 KB of a 196 KB page
- [UX-299](UX-0299-a-handoff-that-does-not-carry-the-trace-in-its-hands.md) — the tab-to-tab handoff fetches the whole trace into the report page, posts it to Perfetto's window and was measured at 25 KB - and it is the same design at 1.5 GB, where the browser tab meets the…
- [UX-305](UX-0305-emphasis-is-a-budget.md) — styleguide §4 budgets emphasis - one emphasized element per block, one accent, text in ink never in status tone - and the page had grown section by section without ever being read against it
- [UX-303](UX-0303-the-shape-before-the-rows.md) — styleguide §2 asks that a value which *is* a shape draws as its shape first;
- [UX-304](UX-0304-dark-first-with-two-grades-of-token.md) — the page was authored light-first with a dark media override and the reader it was built for reads dark;
- [UX-302](UX-0302-the-mapping-made-law.md) — round 41's style guide made §1 a dispatch table on paper;
- [UX-301](UX-0301-the-ordering-authority-moved-and-left-its-old-uniform.md) — round 40 ran `UX-235`'s own acceptance mutation - `root.prepend(decision)` to `append` - and the booted page did not change: `UX-286`'s chapter pass had become the ordering authority, leaving five…
- [UX-334](UX-0334-a-console-the-page-keeps-clean.md) — [a console the page keeps clean](UX-0334-a-console-the-page-keeps-clean.md)
- [UX-335](UX-0335-reading-start-time-of-undefined.md) — [reading 'start_time' of undefined](UX-0335-reading-start-time-of-undefined.md)
- [UX-338](UX-0338-the-page-draws-the-element-population-twice.md) — [the page draws the element population twice](UX-0338-the-page-draws-the-element-population-twice.md)

**store**

- [UX-325](UX-0325-aggregate-crashes-on-every-user-install.md) — `bga snapshot --aggregate` - named in `docs/README.md` as one of the commands to know - died with `ModuleNotFoundError: No module named 'tools'` on every plain `pip install`, so the feature had never…
- [UX-300](UX-0300-what-a-two-gigabyte-snapshot-does-to-a-store.md) — one field snapshot reached ~2 GB and the store's retention thinking dated from kilobyte captures: the raw log kept by default on an 8-12% measurement, pruning that thinks in age and count, and…

**guards**

- [UX-256](UX-0256-the-default-open-state-is-a-policy-nobody-checks.md) — "A checker if everything is really collapsed by default".
- [UX-257](UX-0257-nothing-reads-the-pages-geometry.md) — Every geometric claim about the viewer - "nothing overlaps", "the first content is above the fold" - was measured by hand and then held by nothing, because the shim the guards run on has no layout…
- [UX-264](UX-0264-the-dom-shim-is-copied-twenty-five-times.md) — The DOM shim every viewer guard runs on was written inline **25 times**, so each of three fidelity defects had to be found in the page and then fixed twenty-five times - and `UX-263`'s seven-file fix…
- [UX-274](UX-0274-the-context-map-is-guarded-on-one-half-of-the-tree.md) — the context map's guard globbed `bga/` and `tools/` only, so the `tests/` half had drifted to 5 of 12 entries with every figure stale
- [UX-276](UX-0276-a-guard-can-rest-on-a-path-no-clone-has.md) — round 37's two new guards rested on a `bga snapshot` store that is ignored by design, so they passed on one machine and failed CI on all four Python versions before an assertion ran
- [UX-293](UX-0293-a-ci-check-pins-a-contract-version.md) — `UX-288` moved `analyze/v1` to `analyze/v2` on purpose, the suite was green at 3463 passed and `make lint` clean - and CI went red on a packaging smoke test that pinned the contract literally, in the…
- [UX-287](UX-0287-the-export-ceiling-is-measured-on-a-four-element-run.md) — the export's byte ceiling was asserted against a **four-element** run, so it bounded the one quantity that barely varies while the content that drives the size went unwatched - the committed…
- [UX-336](UX-0336-the-loop-that-got-slow.md) — [the loop that got slow, measured and re-tooled](UX-0336-the-loop-that-got-slow.md)
- [UX-332](UX-0332-the-cascade-beats-the-first-match.md) — [the cascade beats the first match, and two record nits](UX-0332-the-cascade-beats-the-first-match.md)

**docs**

- [UX-242](UX-0242-the-capacity-recommendation-is-documented-nowhere.md) — `bga analyze` computes `capacity_recommendation` and no instructional document named it;
- [UX-243](UX-0243-the-memory-envelope-reaches-no-reader.md) — `memory_envelope` decides whether `--builders` can go up and reached no reader;
- [UX-244](UX-0244-whatifs-convention-lives-in-its-own-docstring.md) — `bga whatif` publishes a projected makespan and what "fixed" means lived only in `whatif.py`'s `CONVENTION`
- [UX-245](UX-0245-the-architectures-cli-table-is-two-commands-behind.md) — the chapter titled "Real current CLI surface" was missing `bga blast` (ten rounds shipped) and `bga whatif`, and named `--explain` nowhere
- [UX-246](UX-0246-the-journey-guide-never-reaches-whatif.md) — the end-to-end journey walks capture → read → go inside → join → act → gate and named `bga whatif` nowhere in the act step
- [UX-273](UX-0273-the-rule-that-draws-a-nested-value-lives-in-one-task-file.md) — the width-not-depth rule governs every nested value in the report and `git grep` found it in exactly one task file
- [UX-247](UX-0247-the-architectures-verification-log-is-stale-about-itself.md) — a document's claim about its own currency, false: the Verification Log said 2026-08-18 while five commits had touched the file since
- [UX-322](UX-0322-the-cli-table-has-lost-the-viewer.md) — the architecture's command table had 18 rows against a tool with 31 commands, and the two a reader looks for first - `bga view`, the entry point for the whole viewer axis, and `bga timeline` - were…
- [UX-323](UX-0323-round-41s-audit-still-asserts-what-round-44-falsified.md) — `docs/audits/round-41.md` still asserted that "175 KB of the 196 KB page is commented JavaScript, because `--export` inlines modules verbatim" - the claim `UX-320` falsified and `UX-307` measured out…
- [UX-327](UX-0327-four-documented-invocations-that-do-not-exist.md) — the guides printed `bga` invocations the tool refuses, and the docs guard checked command *names* only - flags, subcommands and positional meaning were never checked
- [UX-294](UX-0294-eleven-viewer-modules-are-named-in-no-document.md) — review 3 found the viewer's fifteen ES modules named a handful of times in the architecture - `views.js` at 2,400 lines, `nav.js`, and `viewstate.js` at **zero** - so a reader opening `bga/viewer/`…
- [UX-295](UX-0295-whatif-v1-is-in-no-guide.md) — review 3 counted contract homes and found `whatif/v1` named four times across the spec, the architecture and a direction, and **zero** times in `docs/guides/` - the command documented, the document…
- [UX-306](UX-0306-the-guide-joins-the-tree.md) — round 41 wrote the web report's visual contract and left it beside the tree it governs;
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

- [UX-248](UX-0248-there-is-no-authoritative-contract-inventory.md) — `schemas.names()` answers a narrower question than it looks like it does - the documents `bga --schema` can print, not the documents `bga` writes.
- [UX-249](UX-0249-nothing-an-artifact-records-says-which-bga-wrote-it.md) — `bga` reads its own past output as input, and nothing an artifact recorded said which build wrote it.
- [UX-250](UX-0250-comparison-refuses-on-host-and-mode-but-not-on-contract-movement.md) — `bga compare` refuses on host and on cache mode, with an exit code of its own, and had nothing to say about the two runs having been measured by different builds of the tool

**docs**

- [UX-251](UX-0251-a-release-is-a-contract-state-not-a-date.md) — `bga --version` said `0.1.0`, unmoved across 29 rounds and 247 scenarios;
- [UX-252](UX-0252-the-release-notes-should-be-generated-from-the-closed-rows.md) — Hand-writing release notes would make a third copy of facts that already live in the task file's Outcome and the closed row - and two hand-maintained copies of one fact drifting is this repository's…
<!-- /generated -->

Rows 1–238 predate recorded releases: they landed across twenty-nine
rounds under a version that never moved, which is the thing this
release fixes. Their history is
[`docs/backlog/scenarios/closed.md`](docs/backlog/scenarios/closed.md)
and each task file's Outcome, and reprinting 238 of them here would be
a copy of that file rather than a changelog.
