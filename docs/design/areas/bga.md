# The bga area

Moved from [`docs/design/architecture.md`](../architecture.md)'s "Joining the planes", "What the 2026-08-16 audit round changed structurally", "What the real-capture rounds (7–10) changed structurally" and "Core invariants still load-bearing (Plane 1)" chapters (`UX-816`); no line of any of the four is read by a guard, so nothing but a pointer stays behind for them. "Real extensions beyond the original spec" is the fifth: its history table is read whole by `test_the_architecture_table_is_read_at_all` and `test_the_table_status_matches_the_task_files`, and every sentence around the table refers to it, so the whole chapter stays in architecture.md and this page points back to it instead of duplicating it.

## Joining the planes (`UX-51`, `UX-100`)

Planes 1 and 2 are joined by `bga correlate RUN_DIR NATIVE_REPORT.json`, and the contract between them is **one string**: the element UID. Plane 3 joins the same command through `--cache-logs PLANE3.json`, which is what the *merge* half of the granularity findings is computed from (`UX-100`) — without it the split half still runs and the merge half stays silent, because the sandbox toll is the whole basis for calling an element too small. That choice was made by measuring rather than arguing, and the measurements are worth keeping because they also say why the alternative is closed:

- **A merged capture would buy nothing.** `UX-24`'s `run --wrapped-log` already produces both artifacts from one real `bst build`.
- **The join key is exact.** On a real dual capture of `examples/06`, 9 of 9 Plane 2 elements matched Plane 1 UIDs with zero mismatches; the only Plane 1 elements absent were a `stack` and an `import`, which run no build commands, so their absence is correct.
- **The horizons cannot be merged**, per this doc's own argument above — Plane 2 measures inside one element's sandbox and shares no horizon with an element-level trace. Anything called a merge would be a join with a misleading name.

So `bga/correlate.py` is a third consumer that reads two finished artifacts and neither plane knows about, leaving both independently replaceable. It produces the sentences neither can alone, ranks by Plane 1 impact (Plane 2 explains that ranking, never reorders it), carries `UX-45`'s measurement coverage through so a partial result says so, and names elements Plane 1 ranks that Plane 2 never traced rather than passing over them in silence.

Four properties of the join are worth stating because each was a defect first:

- **It ranks on what a fix is worth.** It used to rank and gate on `sensitivity.top_opportunities`, whose score is `min(duration, next_binding_gap)` — a correct upper bound and a useless ranking, because the cap is a constant over exactly the population being ranked. On a real capture all five candidates scored an identical `0.0316`, so the order was the alphabetical tiebreak and the gate never opened for anything, making the join's own headline verdict unreachable. It now reads `UX-70`'s realizable saving, the same number `bga analyze` ranks on, so the two commands cannot name different elements first (`UX-71`).
- **It reads all of Plane 2, ranked by evidence strength.** Every row used to be the same explicitly-hedged declared-vs-used sentence while `binary_cost`, `peak_memory` and `redundant_operations` sat unread in the file it had just opened. It now carries all of them, strongest measurement first and the hedged one last, with that class published as an `id` and a `severity` rather than implied by ordering (`UX-72`, `UX-75`).
- **It refuses fiction.** Plane 2's own element test is syntactic — a name ends in `.bst`, which is all Plane 2 can do alone. The *declared graph* is a Plane 1 fact, so the join checks against it: a bucket name the graph never contained is excluded from every recommendation and listed, rather than quietly recommended (`UX-66`). On the real capture that is exactly `buildstream-build`, `flit_core`, `unknown`.
- **Negative results are load-bearing.** "Already compute-bound at 3.41 cores busy" tells a reader to stop looking inside that element, which is worth as much as a positive finding and much easier to skip past.

## What the 2026-08-16 audit round changed structurally

`UX-27`..`UX-40` were mostly small fixes, but three of them changed the
*shape* of what the tool asserts, and those are worth knowing before
reading anything else in this doc.

### 1. Efficiency is now two numbers, not one

`efficiency_score` (`UX-02`) is `LB / horizon`, and every input to `LB`
is derived from the graph the run actually had. That makes it a correct
answer to *"did the scheduler pack this graph well?"* and a structurally
impossible answer to *"was this graph worth packing?"* - a build whose
independent elements were accidentally chained has a critical path equal
to its own total work, so `LB == T∞ == T_C` identically and the score is
1.00.

Measured, not argued: on `examples/06-macro-micro-optimization`, three
one-line fixes made a real build **30.5% faster** while
`efficiency_score` moved **1.00 → 0.83** and `certified_headroom` moved
**0.00s → 4.05s**. Both backwards.

`floors.occupancy_share` (`UX-27`) is the second signal - `Σ task
slot-occupancy / (horizon × builders)` - and it never consults the graph,
so serializing work that could have run concurrently pushes it down. On
the same pair: **27.8% → 63.0%**. Neither number is redundant and neither
replaces the other; the report prints them adjacently, and a high score
beside a low occupancy is the specific reading that means *"the scheduler
did fine, your graph is the problem"*.

Known weakness, stated in the source rather than hidden: the numerator is
slot occupancy, not CPU time (P1-33/`UX-36`), so it inflates under
contention. It is an honest directional signal, not a precise one.

### 2. Capacity has a single verdict, and everything conditions on it

Before this round the capacity guards (`UX-12`/`15`/`16`/`17`/`21`) were
inert on every run the documented pipeline produced, because
`native_max_jobs` was operator-only (`UX-29`), and the bar they compared
against was BuildStream's own default rather than the real core count
(`UX-28`). Both are fixed, and the resulting verdict is now published
once as `AnalysisResult.capacity_verdict`:

```text
{"oversubscribed": bool, "undersubscribed": bool,
 "checks_ran": bool, "skipped_inputs": [...]}
```

Consumers condition on that dict rather than re-deriving capacity
arithmetic - `UX-35`'s next-step hints are the first, and the rule is
`UX-17`'s own: two independently-derived formulas comparing the same real
inputs will eventually disagree about the same real condition.
`checks_ran` is load-bearing and deliberately separate from
`oversubscribed: false` - "we checked and it is fine" and "we could not
check" are different claims, and the report says which one it is making.

### 3. The CI posture is two gates, not one threshold

`--fail-on-regression` (`UX-03`) answers "did the build get slower".
`--fail-on-efficiency-regression`/`--min-efficiency` (`UX-39`) answer
"was the work this build does being done efficiently", on `occupancy_share`,
with their own exit code `5`. The separation exists because on a growing
project those verdicts diverge, and measurably do: two well-parallelized
elements added to a real project took wall-clock **+2.5%** (failing the
duration gate) while occupancy **rose 13.8pp** (passing the efficiency
one).

The efficiency gate's default tolerance is derived from three repeat
captures of an unchanged project on one real runner (1.0pp of observed
occupancy noise, against 7.4% of wall-clock noise - which is itself the
measured evidence that the duration gate's own 1% default sits below the
noise floor).

## What the real-capture rounds (7–10) changed structurally

Rounds 1–6 were measured against builds this repository wrote itself. From round 7 the tool has been audited against a real `freedesktop-sdk` capture, and four things changed shape as a result.

### 1. The report ranks by what a fix is worth, not by how big something is

`share of the critical path` answers *what is this chain made of*. It does not answer *what happens if I change it*, because it holds the rest of the graph fixed — and on the real capture **97 of 126 elements have zero slack**, so the rest of the graph does not stay fixed at all. `compute_realizable_savings` recomputes the longest path with each candidate zeroed: `python3.bst` holds **17.7%** of the path and eliminating it entirely saves **3.2%** of the build, because a near-tie chain takes over the moment it shrinks (`UX-70`). `zero_slack_share` is published beside it, because *chain or mesh* decides whether "optimize the top element" is meaningful advice at all.

### 2. One capture answers more than one question

A real capture costs ~60 minutes; a longest-path recomputation costs 0.40 ms. `UX-74` spends a handful of the latter to publish what becomes binding after each fix, what the recommended set is worth *together* (simulated — on a chain savings compose, on parallel branches they take a maximum, and only the simulation knows which), and which heavy elements sit off the path worth nothing to fix today. On the real capture the 4th and 6th heaviest elements in the whole build appear in no ranking, correctly, and are now named anyway.

### 3. Conclusions are data, not prose

Every judgement the report makes lives in `bga/findings.py` with a stable `id`, a `severity` and its numeric evidence; `bga/report/text.py` renders that list and `bga/report/json.py` publishes it (`UX-75`). Before this, `--format json` carried every number and none of the conclusions, so a CI consumer had to re-implement the structural exclusion and four thresholds out of the renderer — and two implementations of one judgement is precisely how `analyze` and `correlate` had already drifted (`UX-71`). A finding that is not produced cannot appear in either format; that property is tested, not asserted.

### 4. The known gap, stated rather than papered over

**Both CI scenarios are now captured.** Rounds 6-10 were all incremental — 25 elements built, 65 skipped — which meant the critical path every round measured was the chain through the rebuilt elements rather than the project's real one. Round 11 took the first caches-off capture (`UX-86`): `bootstrap/build/gcc-stage1.bst`'s whole 18-element closure built from source with remotes ignored, 0 cached, 34.2 minutes, confidence 1.00. The constraint that produced warm-then-cut bounds the *target*, not the scenario — every `components/*` target roots in a 64-element compiler bootstrap, but `bootstrap/base-sdk/*` is rooted at a 2-element pre-built binary seed, so a bounded subtree builds from nothing. Related and measured: run-to-run noise on the real build spans **33%** across five captures of the *same* commit (3614.2 / 3434.4 / 3405.8 / 3261.2 / 2712.4s) against the regression gate's fixed 1% default, so `UX-59`'s band over a baseline *set* is the correct path. Its three-run minimum became reachable in round 11, once `UX-81` stopped each capture force-pushing over the last. The band those five define is median 3405.8s ± 3×214.3s (scaled MAD): it correctly calls the pairs the fixed rule reports as `IMPROVED (-5.8%)` and `(-9.8%)` no significant change, and — re-checked at n=5 on 2026-08-20 — the widest same-commit pair falls outside it, because the *fastest* run (2712.4s) sits below the lower edge of the band it helped build. That pair used to read `IMPROVED (-25.0%)`; since `UX-170` it answers `within the baseline set's own observed range`, because a duration the baseline runs themselves reached is not evidence of a change. The band is unchanged — widening it to cover the observed range was measured and rejected (it lets one contaminated baseline run swallow a real regression), so what `UX-170` added is a withheld verdict, not a wider band. See `docs/audits/round-9.md`.

## Core invariants still load-bearing (Plane 1)

The spec's invariants (full text: `docs/spec/specification.md`) remain the real correctness contract every Plane 1 change is checked against:

- **I4** `Σ attribution == H` (horizon) — checked by `bga/validation/invariants.py`, exercised end-to-end by every attribution-touching change (e.g. `UX-19`'s wait-gap re-saturation fix).
- **I8** run-identity capture/enforcement (`UX-07` fixed a real cross-sibling-project collision in it).
- **I9** CPU-accounting reconciliation within tolerance.
- **I11** determinism (same input → byte-identical output, N-run harness in `bga/validation/determinism.py`).
- **I12** cold-floor independence from certified/measured attribution.

## Real extensions beyond the original spec

Every addition beyond the original spec, and its status, is architecture.md's own history table, kept there whole because `test_the_architecture_table_is_read_at_all` and `test_the_table_status_matches_the_task_files` read it: [`docs/design/architecture.md`](../architecture.md) (`UX-816`).
