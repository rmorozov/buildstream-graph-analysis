# Changelog

What changed between the `bga` you installed and the one you have now.

A release here records a **contract state**, not a date: the
twenty-four published contracts and the command surface as they stood, plus what
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
| [0.4.0](#040--a-capture-you-can-carry-2026-09-03) | 2026-09-03 | 537 | breaking |
| [0.3.0](#030--every-document-says-what-shape-it-is-2026-08-27) | 2026-08-27 | 332 | breaking |
| [0.2.0](#020--the-build-that-says-what-it-is-2026-08-24) | 2026-08-24 | 243 | initial |

All three rows are tagged. `v0.3.0` and `v0.4.0` name the commits that
set those versions (`bc1593557`, `679b9cf87`) and both are reachable
from `main`; `tests/unit/test_a_release_records_a_contract_state.py`
reads them, so step 8 of the release guide cannot go unexecuted again.

`v0.2.0` names `3ebe7e1b5`, which does set `version = "0.2.0"` — on a
lineage `main` never merged, so `git checkout v0.2.0` hands a reader a
tree nothing shipped from. **It is kept on purpose** (`UX-633`): the
row is this project's first release and the tag is the only ref that
reaches the code it was cut from. The guard names it in
`UNREACHABLE_BY_DECISION` rather than excluding it behind a version
floor, so the *next* unreachable tag reddens instead of being swallowed.

Round 84 recorded this row as "never a version anywhere in the tree",
which was wrong in letter and right in effect; the reason is above.

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
contracts: analyze/v2 analyze/v3 analyze/v4 analyze/v5 blast/v1 blast/v2 bundle-manifest/v1 capacity-model/v1 capture-layout/v1 compare/v1 compare/v2 correlate/v1 correlate/v2 host-samples/v1 host/v1 host/v2 plane2/v1 plane2/v2 plane2/v3 sources/v1 store-aggregate/v1 store/v1 sweep/v1 whatif/v1
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
