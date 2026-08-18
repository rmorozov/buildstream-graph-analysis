# Optimization Walkthrough: Iteratively Improving a Real Build

> **A note on the commands below.** These sessions predate the `bga <alias>`
> entry points (`UX-77`), so they were originally run as
> `python3 -m tools.<module>`. <!-- docs-style: allow-direct-module -->
> The commands are shown in current form: an
> alias is a thin dispatcher onto the very same module, so the output
> quoted here is what these commands produce.


A worked, narrative example of using `bga` to find and fix real build-efficiency
problems - not illustrative pseudo-output, every command below was actually run
against a real BuildStream 2.7.0 build. The project used,
[`examples/04-critical-path-optimization`](../../examples/04-critical-path-optimization),
was built specifically to have two distinct, independently discoverable
problems, so this walkthrough can show two different iterations driven by two
different signals in `bga`'s report.

## The starting project

Ten elements: a `runtime.bst` (a real shell, so the manual build steps below
have something to run commands with), then a chain `base-config.bst` ->
`base-generate.bst` -> `core.bst`, then four independent libraries
(`lib-a.bst`..`lib-d.bst`) that all depend on `core.bst`, then `app.bst`
depending on all four libraries, then a `stack` element `all.bst` as the real
build target. Every element's "real work" is a `sleep N` in its
`install-commands` (a workload proxy real enough to produce a real
BuildStream log with real timing, without needing an actual compiler
toolchain in this environment).

```
runtime.bst -> base-config.bst -> base-generate.bst -> core.bst -+-> lib-a.bst -+-> app.bst -> all.bst
                                                                  +-> lib-b.bst -+
                                                                  +-> lib-c.bst -+
                                                                  +-> lib-d.bst -+
```

## Iteration 0: build and extract

```
$ bst --builders 2 build all.bst
...
Pipeline Summary
    Total:       10
    Session:     10
    Fetch Queue: processed 10, skipped 0, failed 0
    Build Queue: processed 10, skipped 0, failed 0
```

BuildStream's own real wall clock: 11 seconds (confirmed by the shell's own
timing around the command). The log was captured live with
[`tools/bst_run_wrapped.py`](../../tools/bst_run_wrapped.py) rather than saved to
a file and parsed with `--format raw` - see the note at the end of this
document on why (`docs/backlog/scenarios/UX-06-raw-log-timestamp-corruption.md`), then
extracted with `tools/bst_extract_run.py --format wrapped`:

```
$ bga wrap examples/04-critical-path-optimization \
    build-baseline-b2.log -- bst --builders 2 build all.bst
$ bga extract --format wrapped \
    examples/04-critical-path-optimization build-baseline-b2.log run-baseline-b2
Wrote run directory to run-baseline-b2 - targets=['all.bst'], 10 elements, 19 dependencies, 20 spans
```

## Iteration 1: what does `bga` say to look at first?

```
$ bga analyze run-baseline-b2
============================================================
Build Efficiency Report
============================================================
Run: 4c27cdc4b536c303bf94bef657a65800814b449ba3c575dfe9139dbabe6525fa
Total Duration: 10.6s

Key Findings:
  Confidence: 0.88 (high)
  Biggest Opportunity: 18.9% of wall-clock time is RESOURCE WAIT (2.00s)
  Elements Most Worth Optimizing First (by blast radius):
    1. runtime.bst (9 downstream elements) [structural: import, may not reflect real compute work]
    2. base-config.bst (8 downstream elements)
    3. base-generate.bst (7 downstream elements)
  Highest Criticality Elements:
    1. all.bst (100% probability of being on critical path) [structural: stack, may not reflect real compute work]
    2. app.bst (100% probability of being on critical path)
    3. base-config.bst (100% probability of being on critical path)
  Certified Headroom: up to 2.00s available (T∞=8.60s, LB=8.60s)
  Efficiency Score: 0.81 (worth checking Certified Headroom for real scheduling gains)

Attribution Breakdown:
  Execution On Chain Us         8.60s ( 81.1%)
  Resource Wait Us              2.00s ( 18.9%)
  Untracked Head Us             1.28s ( 12.1%)
  Untracked Tail Us             0.17s (  1.6%)
```
(full report also includes CPU Utilisation, Structural Analysis, and Pipeline
Overhead sections, omitted here for length - see the actual command output
for those.)

**Reading this**: `Biggest Opportunity` names `RESOURCE_WAIT`, 18.9% of wall
clock, and `Certified Headroom` says up to 2.00s is recoverable *without*
changing any element's real work - `T∞` (the observed critical path, 8.60s) is
already below `T_C` (the actual replay makespan, 10.60s), meaning the
scheduler is being held back by something other than dependency structure.
The project design explains why: four libraries fan out from `core.bst`, but
`--builders 2` only allows two to run at once - two of the four libraries
have to queue for a second round even though nothing about the dependency
graph forces that.

This is exactly the distinction `UX-02`'s `efficiency_score` documents:
`0.81`, in the band that means "check Certified Headroom for real scheduling
gains" (a capacity problem) as opposed to "the remaining gain is in the
critical path's own work" (a structural problem). The report is pointing at
a scheduling fix, not a code change.

## Iteration 1's fix: more builders

No project change needed - just more real concurrency:

```
$ bga wrap examples/04-critical-path-optimization \
    build-baseline-b4.log -- bst --builders 4 build all.bst
$ bga extract --format wrapped \
    examples/04-critical-path-optimization build-baseline-b4.log run-baseline-b4
```

```
$ bga compare run-baseline-b2 run-baseline-b4
============================================================
Run Comparison
============================================================
Verdict: IMPROVED  (total duration -2.00s, -18.9%, 10.60s -> 8.60s)

Certified Floors:
  Total Duration           10.60s ->      8.60s   (-2.00s)
  T∞ (observed)             8.60s ->      8.60s   (+0.00s)
  LB                        8.60s ->      8.60s   (+0.00s)
  Certified Headroom        2.00s ->      0.00s   (-2.00s)
  T_C (replay)             10.60s ->      8.60s   (-2.00s)
  Efficiency Score           0.81 ->       1.00   (+0.19)

Attribution Deltas:
  Execution On Chain Us        8.60s ( 81.1%) ->    8.60s (100.0%)   +0.00s (+18.9pp)
  Resource Wait Us             2.00s ( 18.9%) ->    0.00s (  0.0%)   -2.00s (-18.9pp)
```

Real, measured confirmation: `RESOURCE_WAIT` dropped from 2.00s to 0.00s,
`Certified Headroom` dropped to zero (nothing left to recover by scheduling
alone), and `efficiency_score` reached the top of its band (`1.00`). This is
`bga compare` (`UX-01`) doing exactly its job: a one-command real before/after
delta instead of eyeballing two separate reports.

## Iteration 2: what's left, now that scheduling is maxed out?

With `Certified Headroom` at zero, `bga`'s own re-run report on
`run-baseline-b4` says what's next:

```
$ bga analyze run-baseline-b4
  Efficiency Score: 1.00 (very efficient - remaining gains are mostly in
    reducing Critical Path's own work, not scheduling)
  Elements Most Worth Optimizing First (by blast radius):
    1. runtime.bst (9 downstream elements) [structural: import, ...]
    2. base-config.bst (8 downstream elements)
    3. base-generate.bst (7 downstream elements)
```

`efficiency_score`'s own wording is the stopping signal for the *scheduling*
axis - `1.00` means there's no more schedule-only gain to chase; any further
improvement has to come from reducing the critical path's own real work. The
blast-radius ranking says where to look: `base-config.bst`, the
highest-blast-radius element that isn't the structural `runtime.bst` import,
sits at the front of the critical path with 8 downstream elements riding on
it.

Inspecting the project against that hint surfaces two real, fixable things
that weren't visible from the report alone (the report says *what* has high
leverage, not *why* it's slow - that inspection is still the human's job):
1. `base-config.bst` -> `base-generate.bst` is an unnecessary two-step split
   - `base-generate.bst` has no real dependency on `base-config.bst`'s
     *output*, just an artificial ordering.
2. `core.bst` (6 downstream elements, also on the critical path) does 4
   seconds of real work - the single slowest step in the whole build.

## Iteration 2's fix: `examples/04-critical-path-optimization/optimized/`

A second, real BuildStream project - not a hypothetical diff - with both
changes applied: `base-config.bst` + `base-generate.bst` merged into one
`base.bst` (one `sleep 1` instead of two), and `core.bst` cut from `sleep 4`
to `sleep 2`. This is also `bga compare`'s other real use case: comparing not
just the same project under different flags, but two genuinely different
project variants, which is exactly what the `optimized/` subdirectory
convention (`docs/backlog/scenarios/UX-05`'s own ask) is for.

```
$ bga wrap examples/04-critical-path-optimization/optimized \
    build-optimized-b4.log -- bst --builders 4 build all.bst
$ bga extract --format wrapped \
    examples/04-critical-path-optimization/optimized build-optimized-b4.log run-optimized-b4
```

```
$ bga compare run-baseline-b4 run-optimized-b4
============================================================
Run Comparison
============================================================
Verdict: IMPROVED  (total duration -3.10s, -36.0%, 8.60s -> 5.50s)
  Caveat: at least one run's confidence is below the 'high' band - treat this comparison with caution.

Certified Floors:
  Total Duration            8.60s ->      5.50s   (-3.10s)
  T∞ (observed)             8.60s ->      5.50s   (-3.10s)
  LB                        8.60s ->      5.50s   (-3.10s)
  Certified Headroom        0.00s ->      0.00s   (+0.00s)
  Efficiency Score           1.00 ->       1.00   (+0.00)

Confidence:
  Baseline:  0.85 (high)
  Candidate: 0.79 (medium)
```

`T∞` itself (the observed critical path) dropped by exactly the 3.10s the two
changes should save (1s from the merged `base` step, 2s from `core.bst`'s cut)
- real confirmation the structural fix worked, not just a scheduling
rearrangement (`Certified Headroom` stayed at 0.00s both times, since there
was never any scheduling slack left to recover here - all of this iteration's
gain is `efficiency_score`'s "critical path's own work" axis, exactly as
predicted). `Confidence` dropped to `medium` on the smaller project - expected
and correctly flagged: fewer, shorter tasks mean proportionally more of the
run is `Untracked Head`/`Tail` overhead relative to total duration, which the
tool surfaces as a caveat on the comparison rather than hiding it.

## The full before/after

```
$ bga compare run-baseline-b2 run-optimized-b4
Verdict: IMPROVED  (total duration -5.10s, -48.1%, 10.60s -> 5.50s)
```

Both iterations combined: **10.60s -> 5.50s, a 48.1% real reduction**, from
two different fixes the tool's own report pointed at in sequence - first a
scheduling/capacity problem (`RESOURCE_WAIT`, fixed with no project change),
then a structural/critical-path problem (unnecessary serial split + an
oversized single step, fixed by editing the project).

## Stopping point

`efficiency_score` reached `1.00` after iteration 1 and stayed there - the
scheduling axis was maxed out early. Iteration 2's further gain came from
reducing real work on the critical path, which `efficiency_score` doesn't
(and by design shouldn't) claim credit for: it measures schedule quality
given the work as specified, not whether the work itself could be smaller.
The real stopping signal for *this* project is structural: `core.bst` and
`base.bst` remain on the critical path with real, deliberate work
(`sleep 2`/`sleep 1`) that isn't obviously reducible further without changing
what the project actually does - at that point, further gains are a product
decision (is 2s of `core.bst`'s work actually necessary?), not something
`bga` can identify for you.

## A note on trustworthiness of these numbers

This walkthrough's builds were captured with `tools/bst_run_wrapped.py`
(real, live, per-line UTC timestamps) rather than the more common pattern of
saving `bst build`'s output to a plain log file and extracting it afterward
with `--format raw`. That was a deliberate choice, not a style preference:
`--format raw` was found, while building this walkthrough, to corrupt
cross-task ordering on any real multi-task build (BuildStream's own
`[HH:MM:SS]` per-line prefix restarts at zero for every individual task, not
once per invocation - `--format raw`'s parser treats it as the latter). See
[`docs/backlog/scenarios/UX-06-raw-log-timestamp-corruption.md`](../backlog/scenarios/UX-06-raw-log-timestamp-corruption.md)
for the full writeup and real reproduction evidence - this likely affects the
CI-reported numbers for `examples/01-03` too, not just this new example.

A second, unrelated bug was found the same way: comparing the baseline and
`optimized/` runs above, `run_identity.manifest_hash` came back identical for
both (two genuinely different projects) - see
[`docs/backlog/scenarios/UX-07-run-identity-collides-across-sibling-projects.md`](../backlog/scenarios/UX-07-run-identity-collides-across-sibling-projects.md).
It didn't affect this walkthrough's actual numbers (`bga compare` still
computed a correct delta from each run's own real data), just the identifying
label `bga` prints for each run - worth knowing if you see two different
`bga compare` runs print the same `Run:`/candidate hash.
