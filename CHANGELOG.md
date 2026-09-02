# Changelog

What changed between the `bga` you installed and the one you have now.

A release here records a **contract state**, not a date: the twelve
published contracts and the command surface as they stood, plus what
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
| [0.3.0](#030--every-document-says-what-shape-it-is-2026-08-27) | 2026-08-27 | 332 | breaking |
| [0.2.0](#020--the-build-that-says-what-it-is-2026-08-24) | 2026-08-24 | 243 | initial |

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
contracts: analyze/v2 analyze/v3 analyze/v4 analyze/v5 blast/v1 blast/v2 capture-layout/v1 compare/v1 compare/v2 correlate/v1 correlate/v2 host-samples/v1 host/v1 host/v2 plane2/v1 plane2/v2 plane2/v3 sources/v1 store-aggregate/v1 store/v1 sweep/v1 whatif/v1
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
