# Walk, seed 2 — round 97

`UX-685`'s second seeded walk, the empty-population class. Base
`4a6290b`, 2026-09-06.

```text
$ python3 tools/dev_scenario.py --seed 2
area unassigned · role R8 (engineering lead) · Plane 2 hook only · cold ·
current contract · population 0 · reader the static export
```

```text
seed         2
capture      20260906T021236Z (incremental, @last) after 20260906T021223Z
             (cold, @prev) · 1 element (all.bst, stack, no deps) · 0 tagged
             processes · Plane 1 yes; Plane 2 hook-only present,
             joined_elements 0
answer key   1. UX-388: an empty population renders heading + sentence and
                distinguishes "found nothing" / "could not run" / "absent"
             2. cli.md:129 — "When Plane 2 is not in a report, the report
                says which absence it is"
             3. cli.md `run-mode-incremental` — incremental durations are
                not a cold baseline
per plane    1 | "Cache hit ratio: 100% (1 cached, 0 rebuilt) ... Confidence:
             1.00 (high)" | match | nothing to fix | none
             2 | "NO USABLE JOIN ... no process carried an element tag at
             all ... Nothing is recommended" | match | nothing to fix |
             none — an honest refusal, not a fabricated join
             1+2 | "Plane 2 is not in it: the Plane 2 capture attributes no
             span to an element ... 2 slices, 0 flows, 0 counters on 10
             tracks" | match | nothing to fix | none
page         headline right — `"diagnosis":"inconclusive"`, `"Neither the
             chain nor the scheduler can be named the constraint: this run
             did not record the durations the comparison needs."` No false
             certainty. Macro findable: the rail's "Findings (3)" matches the
             3 JSON findings verbatim. 270 controls in 23 classes across 33
             sections; `optimization_horizon`, `latent_heavies` and
             `joint_saving` each render their own rail entry despite being
             `[]`/`[]`/`null` — UX-388's fix holds on the page. 0 of 23
             classes diverge from their labels.
perfetto     0 of 9 "needs Perfetto" canned queries answered with real data —
             the trace is 2 slices / 0 flows / 0 counters. Nothing Perfetto
             added over the static export: an empty run has no per-process
             story either.
findings     1. `bga analyze --diagnostics` drops the Advanced Diagnostics
                and Structural Analysis blocks entirely on the 0-rebuilt
                incremental run, with no line saying why; `bottleneck` and
                `parallelism` are populated dicts on @prev and `None` on
                @last with the same flag passed. → UX-724
             2. `bga view @last --export` prints the same "Not comparable"
                sentence **twice** — once as `ERROR bga.cli:`, once as
                `Error:` — then "Wrote ... 418 KiB" and exits 0, having
                written a complete 428,044 B export. → UX-725
rows added   1 — `test_the_journey_has_an_answer_key.py` gains the text
             report's half of UX-388's rule: a 0-rebuilt run's diagnostics
             block is rendered, not omitted.
friction     Building a population-0 fixture: no shipped example or fixture
             is a zero-element run, so the walker hand-wrote a one-element
             stack and used a 100% cache hit to reach "zero built elements".
             Second: the seed's reader is "the static export, no boot", but
             step 4 requires `dev_page_census.py`, which boots a browser —
             the two disagree and the walker used both, verifying content by
             parsing the embedded JSON as bytes. Driving ledger 121,690
             tokens — **over** the skill's 100k target.
```

## Judging

Both findings are `UX-388`'s class in surfaces that item's fix never
reached, and both are filed. The page half of that rule is confirmed
holding by the same walk, which is what makes the text report's
silence a gap rather than a difference of opinion.

The seed's reader/census disagreement is real and is the tool's, not
the walker's: a "no boot" reader cannot run a step that boots. It is
part of `UX-723` — the recipe must be runnable as printed.
