# UX-941: the only job that builds anything real is a population of one, so every instrument this repository uses to read a CI clock is unavailable exactly where the questions that need one are asked

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-420 | **Blocks:** — | **Found by:** round 137 — `UX-925` had to say what a 420 MiB pinned closure costs CI, and found that the job it is staged in has no instrument that could answer | **Serves:** every round asked what a change costs the example builds, and `UX-895`'s repeats rule, which this job is the one place in the repository that cannot follow | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

This repository is unusually careful about CI clocks. `UX-418`'s
Outcome records three instruments that each failed on the first
foreign clock they met, and `tools/dev_tier_drift.py`'s docstring
lists the six rules that were bought with those red rounds:

> the **median ratio** is divided out over files at or above
> `SHIFT_FLOOR_S` (`UX-423`); a file must clear **both** a ratio and a
> number of seconds (`UX-420`); a file is confirmed on **two
> consecutive runs** whose diff could account for it (`UX-442`,
> `UX-476`); a file the reference does not carry is **recorded**
> (`UX-503`); a `stale` runner verdict needs two runs too (`UX-508`);
> and an entry is the **median of that file's last readings**, whose
> top it must beat (`UX-496`).

Every one of the six is a statement about a **population**. The shift
is a median over files (`SHIFT_MIN_FILES = 20`, and below that the
floor is abandoned rather than the estimator lost). The seconds floor
was sized from what the largest addition on an unchanged suite was —
2.4s, rounded to 5.0. The two-run rule needs a carry file. The
recorded entry, the stale verdict and the median-of-five all need a
reference row with a window in it.

`bst-examples` has none of that, and it is the only job in this
repository that builds anything real. It produces **one number per
run** — its own wall clock — and it writes no record of it:

```text
$ awk '/^  bst-examples:/,0' .github/workflows/ci.yml \
    | grep -c 'dev_tier_drift\|dev_perf_ratchet\|--record\|--carry'
0
$ python3 -c "import json; r=json.load(open('tests/ci_reference.json')); print(len(r['files']))"
569        # per test file, from the `test` job's junit; no job is in here
```

So the number is readable only from the outside, by asking the jobs
API how long the job took. Twenty-four successful runs on `main`, read
that way on 2026-09-22:

```text
266 315 | 620 658 678 711 737 746 752 752 756 766 814
          815 817 822 826 830 831 837 854 860 861 964
```

The two on the left are from 2026-09-14, before the staged toolchain;
the series is not even one population. Over the twenty-two on the
right, with nothing in the job's own content changing:

```text
median 814.5s   min 620   max 964   spread 344s (+/-21%)
max/min 1.55    largest delta between consecutive runs 437s
                median delta between consecutive runs   71s
```

**`CI_DRIFT_FACTOR` is 1.5.** The job's own noise on an unchanged
workload is 1.55 — it would trip this repository's own drift gate
standing still, and `CI_DRIFT_SECONDS`, at 5.0 against 344s of spread,
cannot hold it back. The gate is not wrong; it is calibrated on a
population that this job does not have.

The repository already has the rule this job cannot obey. `UX-895`'s
Required Fix asks for **three repeats per arm**, "because one capture
is not a baseline (`UX-234`'s rule, and the 33% spread the README
pastes)" — and then routes the whole measurement to one of the owner's
own machines. `UX-905` routes to the owner's LLVM element for the same
kind of reason. Both decisions are right and both were taken row by
row, so nothing in the repository says why the job that already builds
six real projects every push is not where such a reading is taken.

`UX-925` is what found it. It wanted to say what a 420 MiB pinned
closure costs CI, looked here, and declined to claim a number — the
right answer, reached by one session reading the jobs API by hand. The
next round has no reason to reach it any faster.

Its own landing run is the worked example. `98c387bc` staged the whole
pinned closure for the first time and the job read **807s**, which is
mid-band in the 620-964 above. **That does not show the fetch is
cheap; it shows the instrument cannot see it.** A 420 MiB download and
a no-op are the same reading here, and so would be a hundred-second
regression — which is the distinction this row exists to write down,
because the sentence that comes naturally is the other one.

## Required Fix

Two halves, and the first is the one that matters.

**Say, where a reader will look, that this job's wall clock is not a
measurement.** `ci.yml`'s `bst-examples` comment already says the job
is "not correctness-gating"; it says nothing about its clock, and the
three rows above each assume one. One paragraph naming the spread, its
date and the command that produced it, so the next round reads it
before designing an experiment around it rather than after.

**Give the structural readings a home, since they are the ones this
job can take.** Paths staged and bytes fetched are exact, cheap and
already computed — `tools/nix_closure.py` prints both, and a capture's
element count and CAS bytes are exact per `UX-907`. A structural
figure is a measurement at n=1; a wall clock is not. Where a wall
figure is genuinely wanted, it needs a population, which means N runs
of **one** sha rather than one run of each of N shas — a dispatchable
matrix over the same commit, not the push series above.

## Out of Scope

Taking `UX-895`'s reading, which needs one of the owner's own agents
and is that row's work. Changing `CI_DRIFT_FACTOR`, `CI_DRIFT_SECONDS`
or anything else in `dev_tier_drift.py`: the constants are right for
the population they were sized on, and this row is about a job that is
not in it. Making `bst-examples` correctness-gating. Any edit to
`ci.yml` beyond the comment, which is another thread's surface tonight.

## Acceptance Test

A guard reads the `bst-examples` job's own stated spread and refuses a
sentence anywhere in `docs/` that prices a change in that job by its
wall clock without naming the spread it sits inside — the shape
`test_the_cost_row_is_derived_from_the_selector.py` already uses for
the `make test-touching` figure, which is derived by a tool and carried
in a document rather than typed.

```text
$ python3 tools/dev_bst_examples_spread.py
22 runs, median 814.5s, 620-964, max/min 1.55  (CI_DRIFT_FACTOR 1.5)
```

Three mutations, each applied, reddened, reverted:

- the document's figure edited to a narrower spread — the guard must
  red, or it reads that a figure exists rather than that it is the
  measured one;
- a sentence added that prices a change in `bst-examples` in seconds
  with no spread beside it — the guard must red, naming the sentence.
  **This is the discriminating one:** a guard that only checks the
  derived figure passes every new claim written next to it, which is
  the whole defect one level up;
- the population reduced to a single run — the tool must refuse to
  print a median rather than print one, since a population of one is
  the condition this row exists to name.

The second mutation is what rules out the cheap fix: a paragraph in
`ci.yml` that no guard reads changes nothing, the way a convention in
`CLAUDE.md` with no property behind it changes nothing (`UX-938`).

## Outcome

**Round 138, 2026-09-23**

**The gap, re-measured.** `bst-examples` wrote no record of its clock,
and nothing beside the job said the clock was not a reading. Every
successful `bst-examples` job on a `main` push since the staged
toolchain, read from the jobs API (`started_at..completed_at`):

```text
$ python3 tools/dev_bst_examples_spread.py --fetch --since 2026-09-15 --limit 30
26 runs of main, median 816s, 620-964s, max/min 1.55, read 2026-09-23  (CI_DRIFT_FACTOR 1.5)
```

Four more runs than the filing's 22, same range. Consecutive deltas over
the 26, oldest first: max 306s, median 78s. The seven runs of
2026-09-08..14 read 216-315s and sit before `--since`: another workload.

**The close.** `ci.yml` carries one paragraph beside the job: the clock
is not a measurement, the figure line above, the command. `--write`
rewrites that line from `tests/bst_examples_clock.json`, the readings
`--fetch` stored. `examples/README.md` names the job twice and prices
it in neither, so it was left alone.
`test_the_examples_clock_is_a_spread.py` holds the line to the data,
and refuses any sentence or table row in `docs/**/*.md`, the two
READMEs or `CLAUDE.md` that names `bst-examples` with a duration and
not `620-964s`. It flagged one: this Outcome's own first draft of the
mutation table below, which quoted the planted sentence verbatim.

The structural half: a last step, `UX-941 structural figures as
notices`, under `if: always()`, prints one `::notice title=UX-941
structural::` line per figure: store paths staged under examples/05's
toolchain (`nix_closure.staged_hashes`, what `--check` prints as
`staged paths`) and `graph_metrics.num_elements` of each of the six
`report*.json` the job writes. A missing input prints `absent`.

```text
$ bga analyze -f json -o <art>/06-macro-micro-optimization/report-baseline.json -d -r tests/fixtures/macro_micro/run
$ python3 tools/dev_bst_examples_spread.py --notices <art> <none> | sed -n '1p;6p'
::notice title=UX-941 structural::examples/05 toolchain: absent store paths staged (nix_closure.staged_hashes)
::notice title=UX-941 structural::examples/06-macro-micro-optimization/report-baseline.json: 11 elements (graph_metrics.num_elements)
```

| mutation | red |
|---|---|
| `ci.yml`'s figure narrowed to `700-900s, max/min 1.29` | `test_the_paragraph_is_what_the_tool_would_write` |
| fixing guide gains a sentence pricing the job at 120s, no range | `test_no_document_prices_the_job_without_its_range`, naming the sentence |
| `MIN_RUNS` check made `< 1` (a population of one gets a median) | `test_one_reading_is_refused`, `test_the_tool_prints_no_median_for_one_run` |
| notice lines print an empty figure | `test_the_command_prints_one_figure_per_line`, `test_a_missing_input_is_reported_absent_never_silent` |
| `if: always()` removed from the step | `test_it_follows_every_build_step_and_runs_always` |

Each applied, red, reverted, then 20 passed. The data cut to one run:
`dev_bst_examples_spread: 1 run(s) of bst-examples: fewer than 3, so no
median - one run of each sha is not a population`, exit 1.

**Deviations.** Bytes fetched and CAS bytes are not in the notice
step: the job computes neither. `nix_closure` counts no wire bytes, and
`FileSize` is a declaration its own `fetch_nar` records as 2,830 bytes
off for glibc; CAS bytes are `UX-907`'s opt-in walk, which no
`bst-examples` step turns on. The step is an edit to `ci.yml` beyond
the comment, which Out of Scope declined; the brief took it, as its
own step named for this row. A sentence naming an element (`\w+.bst`)
is exempt from the guard: `round-124.md`'s `giant.bst` +40.1s is a
paired reading inside one capture, not the job's clock. `MIN_RUNS` is
3, `UX-895`'s repeats per arm. The cap of 10 notices per step is
GitHub's documented one, not measured here; the step prints 7.
`--fetch`'s two `urllib` calls are ruff S310, force-added to
`tests/quality_baseline.json` under this id (`dev_baseline.py --write
--force --reason UX-941`: 2 authorised, 3+/1- lines). The fixing
guide's §6 map names the tool and the data file, and its derived
`make test-touching` spread moved to 31-163 of 584 test files.

**Not closed.** No annotation has been read back: `ci.yml` runs on
`main` pushes and pull requests, not on this branch's push, so the
first notices land on this row's PR run
(`GET .../check-runs/<id>/annotations`). A wall figure for a change
needs N runs of one sha; the route is a dispatchable matrix over the
same commit, which this row did not add.
