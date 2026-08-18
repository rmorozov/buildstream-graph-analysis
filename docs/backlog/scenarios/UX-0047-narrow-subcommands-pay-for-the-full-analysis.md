# UX-47: `bga graph` computes attribution it never renders, so every narrow subcommand costs the same 67s as `analyze`

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-42 (independent, but fixing either alone already helps - see below)

## Motivation

Round-2 scale probe, 1202-element run. Every section subcommand costs what the full report costs:

```text
$ time bga graph        /tmp/run-scale-1200     real 1m6.827s
$ time bga floors       /tmp/run-scale-1200     real 1m8.297s
$ time bga utilisation  /tmp/run-scale-1200     real 1m8.340s
$ time bga diagnostics  /tmp/run-scale-1200     real 1m9.431s
$ time bga analyze      /tmp/run-scale-1200     real 1m7.379s
$ time bga sweep        /tmp/run-scale-1200     real 0m14.819s
```

`bga graph` renders the dependency graph, critical path, and structural metrics. It renders no attribution at all. It spends 67 seconds computing attribution anyway - `UX-42` establishes that ~98% of that time is `_resource_saturation_intervals`, which nothing in the `graph` section consumes.

`sweep` is the outlier at 14.8s precisely because it is the one subcommand that *doesn't* share the path: its own docstring says "Unlike the other subcommands, this isn't a slice of one `AnalysisResult` - it's a series of replay runs across a capacity range, so it has its own producer function". That contrast is the evidence that the cost is structural rather than inherent to the data.

This is a documented design decision, not an oversight. `cmd_analyze`'s docstring records it:

> the section-specific subcommands below (graph/floors/replay/diagnostics/utilisation) are thin aliases over the same pipeline (P1-14 hybrid resolution: keep `analyze` as the primary command per the current design, and add the spec's Part 37 command list as aliases rather than re-deriving shared pipeline stages per subcommand)

At the scale the tradeoff was made, it was free. At 1200 elements it has a measured price, and it collides with what the README tells users to do:

> The `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` subcommands are thin, narrower slices of the same full `analyze` report — **reach for one of them instead of grepping `analyze`'s output** for a single question.

A user who follows that advice on a real-sized project pays full price for a narrow question, repeatedly - and `bga graph` in particular is the natural first command during macro optimization, when the user is iterating on the dependency graph and does not care about attribution yet.

## Required Fix

Make the pipeline stages lazy, so a section pays only for what it renders. The shape, to be settled when picked up:

1. **Thread the requested section down into the analyzer** rather than only into the renderer. `_produce_analysis_output(args, section=...)` already knows the section; today that knowledge arrives only after `analyze()` has computed everything.
2. **Compute stages on demand.** Attribution, diagnostics, replay and utilisation are the expensive, separable ones; the graph/structural stage is cheap and is a prerequisite for the rest. Whether this is lazy properties on `AnalysisResult`, an explicit stage set passed to `analyze()`, or a section→stage map in the CLI is a real design choice with different testability - the invariant that matters is that `analyze` with no section still computes everything and produces byte-identical output.
3. **Keep `analyze` the primary command.** `P1-14`'s resolution was right about that and this task does not reopen it; it only stops the aliases from paying for stages they discard.

Note this interacts with `UX-42` but neither subsumes the other. `UX-42` makes attribution cheap for everyone including `analyze`; this makes `graph` cheap even while attribution is expensive. Fixing `UX-42` first would shrink this task's payoff without eliminating it, since some stages will always be irrelevant to some sections.

## Out of Scope

- `UX-42` itself - the cost of attribution, as opposed to who pays it.
- `bga sweep`'s own 14.8s, which is real replay work that `sweep` actually uses.
- Caching an `AnalysisResult` across invocations. A separate idea, with its own invalidation problem, and this task should not become that.

## Acceptance Test

1. `bga graph` on the 1202-element scale fixture completes in a small fraction of `bga analyze`'s time on the same run.
2. `bga analyze` output is byte-identical before and after, on every fixture in `tests/fixtures/topologies.py` and on the `mixed_task_kinds` golden snapshot.
3. Every section subcommand's output is byte-identical before and after - lazily computing a stage must not change what a section renders.
4. A test asserts the stage-skipping actually happens (e.g. that `bga graph` never enters `_compute_attribution`), so the property cannot silently regress into "it's fast for some other reason". Full suite green.

## Fix Implemented

`analyze()` takes an optional `section`, and a `_SECTION_STAGES` map names which stages each section actually renders. Omitting `section` - the default, and what every programmatic caller does - runs everything, so `bga analyze` is untouched.

**`P1-14`'s resolution is not reopened.** The pipeline is still one pipeline shared by every alias; it simply stops an alias paying for stages it discards. That was the right call when the difference was unmeasurable, and it remains the right structure now that it isn't.

The map was derived by reading what each section renders in **both** formatters, which agree:

| section | stages | notes |
|---|---|---|
| `graph` | `structural` | `GRAPH_SIGNAL_KEYS` are set inline from `graph_analysis`, not by a stage |
| `floors`, `replay` | `floors` | replay's makespan `t_c` is computed inside floors |
| `utilisation` | `utilisation` | |
| `diagnostics` | `diagnostics` | the non-graph signals |
| `None` | all | plus `confidence`, which both formatters gate on `section is None` and which consumes attribution and floors - computing it for a narrow section would have reintroduced the whole cost |

### Results, on the 1202-element scale fixture

```text
                before UX-42/47     after UX-42     after UX-47
bga graph          1m 57s              3.15s          0.99s
bga floors         1m 08s              3.10s          0.66s
bga utilisation    1m 08s              3.10s          0.74s
bga diagnostics    1m 09s              3.10s          1.18s
bga analyze        1m 55s              3.15s          3.26s   <- unchanged, as intended
```

`bga graph` end to end across both fixes: **117s -> 0.99s**. And the prediction in this doc's own Required Fix held - `UX-42` shrank both numbers without changing the relationship, leaving `graph` still paying exactly what `analyze` paid until this landed.

### Verification

Every section's output is byte-identical before and after - 20 combinations (5 sections x 2 formats x 2 fixtures, one of them a real `examples/06` capture), checked by capturing baselines from the stashed tree and diffing.

Tests: 30 new (`tests/unit/test_section_stage_gating.py`). They assert both halves, because either alone is insufficient: that the stage really is skipped (acceptance test 4 - otherwise a fast result could come from something else entirely), *and* that each section still renders exactly what a fully-analyzed result renders for that section, across four topologies and both formatters. The second is compared against a full analysis rather than a stored snapshot, so it cannot drift alongside the code it checks.

One documentation fix fell out: `README.md` told users to reach for the narrow subcommands, which was advice they did not previously benefit from. It now says what they cost.

## Verification Log

Filed 2026-08-16 (round 2). All six timings are real `time` runs of the same command against the same 1202-element run directory on one host, taken in one session. An earlier draft of this note recorded `bga sweep` at 0.79s; that figure was from a different, smaller run and is corrected here to the measured 14.8s - the point it supports (that `sweep` is the one subcommand off the shared path) is unchanged and is now sourced from `cmd_sweep`'s own docstring rather than from the timing. The `P1-14` design decision and the README recommendation are quoted verbatim from `bga/cli.py` and `README.md`.

The table is from the original ad-hoc scale run. `tools/gen_synthetic_scale_run.py` was committed in the same round so this doc's acceptance test is runnable; against its (slightly denser) output the same relationship holds with larger absolute numbers - `bga graph` **1m57.5s**, `bga analyze` **1m55.0s**, `bga sweep` **14.1s**. `graph` costing marginally *more* than the full `analyze` is measurement noise on a two-minute run, not a real ordering; the point is that they are indistinguishable.
