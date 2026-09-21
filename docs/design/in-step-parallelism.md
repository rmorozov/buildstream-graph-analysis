# In-step parallelism: the axis the floors do not read

Written 2026-09-20, from the sentence `bga` prints under every
Certified Floors block: *"native build-system parallelism (`--max-jobs`)
is a separate, currently unmodeled axis"*
([`bga/analyzer.py:196-199`](../../bga/analyzer.py)).

**Serves:** R5 above all — cores are what a capacity operator buys and
builder slots are not — and R2, whose row in [`roles.md`](roles.md)
already names *"achieved parallelism"* as the thing a recipe author
wants about their own element. R1 reads the same numbers in the inner
loop; R4 inherits whatever `efficiency_score` means.

**Status:** proposed — an argument, not a numbered Direction and not a
filing. No code changed. §8 is the one increment to file first;
§9 says what adopting this as Direction 21 would cost.

Every figure below is a pasted run against the committed
[`tests/fixtures/macro_micro`](../../tests/fixtures/macro_micro) snapshot
(4 builders, 4 cores, `bst 2.7.0`, taken 2026-08-21) or a `file:line` in
the tree. Nothing here is a guard's population yet; §8's acceptance test
is where these numbers would gain one.

## 1. The contradiction, in one block of the tool's own output

```text
$ python -m bga.cli analyze tests/fixtures/macro_micro/run
Certified Floors:
  T∞ (observed critical path): 43.20s
  LB (resource lower bound):   43.20s
  Certified Headroom:          0.00s
  T_C (replay makespan):       43.20s
  Efficiency Score:            1.00 (scheduling is near the certified floor for this graph ...)
  Dispatch Occupancy:          29.1% (Slot-time used as a share of slot-time available. ...)
  Note: LB/Efficiency Score certify against this run's recorded resource capacities
  (builders/fetchers/pushers), not real host CPU cores or any declared CPU budget -
  native build-system parallelism (--max-jobs) is modelled for this capture from its
  own Plane 2 measurements; see the capacity recommendation below. ...
```

The same capture's Plane 2 report, which the block above qualifies but
does not read:

```text
$ python3 -c "import json; p=json.load(open('tests/fixtures/macro_micro/plane2.json')); \
c=p['cpu_time']; print(c['total_cpu_us']/1e6, c['measured_processes'], \
c['unmeasured_processes'], p['wall_span_s'])"
69.786259 663 150 43.50824261999992
```

| quantity | value | where from |
|---|---|---|
| builder slots | 4 | `run-context.json` `resource_capacities.PROCESS` |
| host cores | 4 | `run-context.json` `host_cpu_count` |
| slot-time used | 29.1% | `floors.occupancy_share` |
| CPU measured | 69.79 CPU-s over 663 processes, 150 unmeasured (coverage 0.815) | `cpu_time` |
| cores busy | 1.60 of 4 | 69.79 / 43.51, the same arithmetic as `bga/correlate.py:1015-1022` |
| certified headroom | 0.00s | `floors.certified_headroom` |

Four slots 29% used, four cores 40% used, and the report certifies that
no schedule finishes sooner. Nothing is wrong in the arithmetic. Part 16
computes `max_p(W_p / C_p)` where `C_PROCESS` is the builder count
([`bga/floors/capacity.py:43-46`](../../bga/floors/capacity.py)), and
against *that* resource the run is at its floor. The note under the
block even says the axis is modelled for this capture — `UX-116`'s
clause, which fires because the capacity recommendation below it does
read `cores_busy` — while the floor the note qualifies reads none of it.

So the axis is **measured, published, and not joined**. That seam, not a
missing measurement, is what this document is about.

### 1a. The condition nobody prints

There is a second, larger consequence, and it is not fixed by adding a
term. `W_p` is the observed *wall* duration of each task, and every one
of those durations was produced at whatever in-step width that element
happened to run at. Change `--max-jobs` and every `W_p` changes. So
**`LB` is certified conditional on the in-step parallelism of the run it
was computed from**, and no output says so.

The replay inherits it. On this fixture `bga correlate` proposes:

```text
Replaying this run with those edges removed - same durations, same capacity -
finishes in 19.1s against 43.2s: 24.1s
```

"Same durations" holds nine elements' measured durations fixed while
proposing to run eight of them concurrently. Those durations were
measured at 29.1% dispatch occupancy — largely one element at a time —
and each of the seven `lib-*.bst` elements draws 1.80-1.95 cores busy
(§2). Eight at once is ~14 cores of demand on a 4-core host. The
projection is not wrong as a *bound on the graph*; it is silently
conditional on an axis the model does not carry. `UX-14` recorded that
`sweep`/`replay` share the blind spot; this is what sharing it costs.

## 2. What the capture already gives

Everything in this table is on disk today, in a contracted payload, on
any capture taken with Plane 2. No new instrument is needed to read it.

| fact | key | produced | what it measures |
|---|---|---|---|
| CPU seconds per element | `cpu_time.per_element[e].cpu_us` | `tools/bst_native_build_tracer.py:5989-6072`, from `getrusage` `utime+stime` at each process's exit (`tools/native_trace/hook.c:544-594`) | **direct.** Real kernel CPU accounting |
| achieved core-width per element | `cpu_time.per_element[e].cpu_per_wall_second` | same, ÷ that element's own process span | **direct.** "1.0 is one core saturated, 4.0 is four" (`bga/schemas.py:1633-1638`) |
| coverage of both | `cpu_time.per_element[e].coverage`, `measured_processes` / `unmeasured_processes` | same | **direct.** A signal death or an exec replacement leaves no rusage, and is counted unmeasured, never zero |
| run-level CPU | `cpu_time.total_cpu_us` | same | **direct**, and on this fixture exactly the sum of the per-element `cpu_us` |
| process concurrency per element | `per_element_parallelism[].peak_work_concurrency`, `.mean_work_concurrency`, `.work_span_s` | sweep-line over matched process intervals, `tools/bst_native_build_tracer.py:4010-4034` | **proxy.** Counts processes that overlap in time, whether or not they are on a CPU |
| requested width per element | `per_element_parallelism[].requested_jobs` | `-j\s*(\d+)` on `make`/`gmake`/`ninja` argv, `:3998`, `:4089-4098` | **direct but partial.** Only those three binaries, only an explicit `-jN` |
| pinning | `findings: ["pinned_to_one_job"]` | `:4141-4151` | direct |
| whole-machine cores busy over time | `host-samples/v1`, `cpu_busy_cores` every 2.0s | `/proc/stat`, `tools/bst_native_build_tracer.py:742-769` | **direct, wrong granularity.** One number for the host, not attributed to elements |
| the raw per-process records | `plane2.log.gz` | `bga/run_store.py:266-268`; `CONDITIONAL`, **no contract id** (`:641-644`) | the `START`/`END` lines with timestamps and rusage, kept beside the report |

Per-element, on this fixture (`cpu_s`, `cores` and `cov` from
`cpu_time.per_element`; the rest from `per_element_parallelism`):

```text
element          cpu_s  wall_s  cores  peak  mean  req   cov
app.bst           3.98    2.50   1.38     3  1.60    4 0.816
codegen.bst      14.45    6.70   2.02     4  3.25    4 0.815
core.bst         16.43   17.66   0.90     2  0.96    1 0.812   pinned_to_one_job
lib-a.bst         5.97    2.79   1.85     3  2.09    4 0.816
lib-b.bst         6.28    2.94   1.86     3  2.11    4 0.816
lib-c.bst         5.41    2.46   1.88     3  2.15    4 0.816
lib-d.bst         5.53    2.59   1.85     3  2.07    4 0.816
lib-e.bst         6.26    2.80   1.95     3  2.18    4 0.816
lib-f.bst         5.48    2.65   1.80     3  2.00    4 0.816
```

Two candidate instruments for the same words, and they disagree.
`achieved_vs_requested` is `peak / requested_jobs`; the CPU-weighted
answer to the same question is `cores_busy / requested_jobs`:

```text
element        requested  peak  achieved_vs_requested  cores_busy  cores/requested
codegen.bst            4     4                   1.00        2.02             0.51
lib-c.bst              4     3                   0.75        1.88             0.47
lib-a.bst              4     3                   0.75        1.85             0.46
app.bst                4     3                   0.75        1.38             0.35
core.bst               1     2                   2.00        0.90             0.90
```

`codegen.bst` is published as having achieved **100%** of the
parallelism it asked for while using **51%** of it in CPU terms. The
field is honest about what it counts — its own docstring says
"this is NOT on its own the finding" (`:4114-4123`) — but a number named
*achieved parallelism* that reads process overlap is the proxy shape
[`rules.md` §5](../contributing/rules.md) forbids, and the two readings
differ by 1.5-2.2x on every element in this capture. **Whatever models
this axis has to be CPU-weighted.**

## 3. What the capture does not give

1. **A per-element concurrency curve.** `_concurrency_profile` computes
   one and throws it away: `finish()` publishes `peak` and `mean` only
   (`:4100-4123`). The whole-build counter track in Perfetto is one
   series for the run (`tools/bga_timeline.py:492-502`). No schema key
   named for a series exists.
2. **CPU over time.** rusage is read **once, at exit** — "No sampling,
   no estimation ... runs exactly once per process"
   (`tools/native_trace/hook.c:523-528`). So `cores_busy` is an average
   over an element's whole span and cannot distinguish "four cores for
   half the span" from "two cores throughout" — `codegen.bst`'s 2.02 is
   consistent with either.
3. **The axis's own input, per element.** `run_context.native_max_jobs`
   is one run-level scalar (`bga/ingest/models.py:82`); the per-element
   value is recovered only by the `-jN` argv regex, which sees
   `make`/`gmake`/`ninja` and not `cmake --build -j`, `cargo`, `meson`,
   or a width inherited through `MAKEFLAGS`. On this fixture it is
   absent at run level entirely — `capacity_verdict.checks_ran` is
   `false`, `skipped_inputs: ["native_max_jobs"]` — so `UX-12`'s
   oversubscription check, which compares the *declared*
   `builders × max_jobs` against cores
   (`bga/analyzer.py:1007-1143`, a "coarse, config-level signal
   ... not measured achieved concurrency", its own words), is inert.
4. **Any response curve.** One capture is one point per element. Nothing
   on disk says what `core.bst` would cost at `-j4`.
5. **A contract on the raw log.** `plane2.log.gz` carries the intervals
   and the rusage, and `UX-297` deliberately removed the per-process
   array from the report to stop a monolith being re-parsed — on this
   very fixture that array was 813 records, 458 KB of the original
   584 KB (`tests/fixtures/macro_micro/README.md`). A
   floor derived from the log would depend on an optional, unversioned
   file. A floor derived from `cpu_time` depends on `plane2/v3`.

## 4. How the certified lower bound changes

### 4a. The term

```text
LB_cpu = measured CPU work / governing cores
```

On this fixture: 69.786259 CPU-s ÷ 4 = **17.45s**, against `LB` 43.20s.

`governing cores` is the quantity `UX-15` already resolves for the
oversubscription check: a declared `cpu_budget` when the operator gave
one, else `host_cpu_count` (`bga/analyzer.py:1007-1143`). Logical CPUs,
not physical: dividing by the larger number yields the smaller floor,
which is the safe direction for a lower bound.

### 4b. Why it is certified, and in what sense

Three properties, and they are the argument for shipping this before
anything else on the axis:

- **Monotone in coverage.** Measured CPU ≤ real CPU, so an undercount
  produces a *lower* floor. 150 unmeasured processes here weaken the
  bound and cannot invalidate it. Contrast `T∞`, where one missing
  duration invalidates the path — which is why Part 15.3 has a
  publication gate and this would not need one.
- **Exact integer arithmetic.** `total_cpu_us // cores`, in the
  microsecond grid the rest of the floors use.
- **Conditional, like every other floor, but on something different.**
  `T∞` and `max_p(W_p/C_p)` are conditional on the observed durations,
  and so on the observed in-step widths (§1a). `LB_cpu` is conditional
  on the observed CPU *work* — which is not invariant either (wider
  builds pay more cache misses; `-flto` links do not divide) but moves
  for different reasons. Two floors conditioned on different things
  bracket the truth better than one floor conditioned on both while
  naming neither.

How far CPU work really moves under a width change has been measured
twice here, both on `examples/11-serial-giant` under the jobserver:
`cc1` CPU 122.6s → 121.3s (−1.1%) as the element's width went 2 → 3
(`docs/audits/round-119.md:93-99`), and 132.1s → 130.2s (−1.5%) at
2 → 4 (`docs/audits/round-120.md:109-117`) — while the wall moved
−10.6% and −13.4%. Two points on one compile-bound element is not a
law, and it is all the evidence there is. It is also the cheapest thing
a wider corpus could test, which is §5's argument.

### 4c. Why it must not be folded into `lb`

- `docs/spec/specification.md` Part 16 defines `LB` as the max over
  `T∞`, `W_p/C_p` and exclusive-serialization bounds, and Part 44's
  eleventh clause is *"CPU utilization is a separate axis from makespan
  attribution."* The repository's own hard rule is **never touch the
  spec outside Part 32's registry** ([`rules.md` §5](../contributing/rules.md)).
  Redefining `LB` is therefore not available to any session here. The
  axis enters as an **additive published fact** or not at all.
- `efficiency_score = lb / horizon_us` (`bga/analyzer.py:730`). Folding
  a term in silently moves a number `bga compare` gates CI on.
- The two floors answer different questions and a reader needs to know
  which bound is which. A single `LB` that is sometimes the graph and
  sometimes the machine is the shape `UX-83` already caught once: two
  planes giving contradictory advice with nothing arbitrating.

So: publish `lb_cpu` beside `lb`, with its coverage and its governing
core count, and let the note say which one binds. `lb`,
`certified_headroom` and `efficiency_score` keep their exact current
meanings, and `analyze/v6` gains keys rather than changing any.

### 4d. What it is worth today

On this fixture `LB_cpu` (17.45s) is far below `LB` (43.20s), so it does
not bind — and that is the useful reading, not a null result. The
restructuring projection in §1a lands at **19.1s**; the CPU floor says
the machine's own wall is **17.45s**. The projection is within 10% of a
floor no reader can currently see, and the 18.5% of processes with no
rusage can only push that floor up. The tool can already say *"remove
these edges and the build halves"*; it cannot yet say *"and then you are
done, because the cores are the next wall"*. That sentence is worth more
than the term's arithmetic.

## 5. Direction 20: the jobserver is the cheap instrument for this

[Direction 20](directions.md) landed the jobserver as a capture option
(`UX-841`..`UX-852`, round 118; status line at `directions.md:1822`).
Three consequences for this axis, in both directions:

**The mode invalidates "`max-jobs` is a number."** Under
`--jobserver auto` an element's width is granted by the pool at runtime.
Round 120's acceptance pair on `examples/11-serial-giant`:
`peak_work_concurrency` 2 → 4, wall 296.26s → 256.47s, IMPROVED −13.4%
(`docs/audits/round-120.md:104-117`). The axis is a function of time
there, not a scalar, so a model that carries one number per element
models the off case only.

**The mode's own reading is already the axis, at run level.** The token
ledger publishes `tokens_idle_share` (ticks with cores idle and tokens
still in the pool) and `tokens_starved_share` (ticks with cores idle and
the pool empty — graph-bound, not pool-bound), `bga/schemas.py:4770-4826`.
Those two shares are the run-level statement of exactly what §1's block
cannot say. Round 120's field finding is the same sentence from the
other side: *"the giant alone on its implicit token, the other three
builder slots idle, and the pool grew to the three tokens the machine
had"* (`round-120.md:119-122`) — slots idle while cores were the binding
resource, which is the case `max_p(W_p/C_p)` over builders cannot
represent.

**And the mode is the only free source of a response curve.** A speedup
curve per element needs the same element built at several widths. A
controlled sweep costs a rebuild per point. The jobserver varies width
*within one run* and already logs the pool. What it does not yet log is
which element held which tokens when: `jobserver.per_element` carries
only `joined`, `tokens_held_p50`, `tokens_held_max`, and those come from
the wrapper-acquire rows for `ld.lld`/`lld`/`ld.gold`/`mold`/`ninja`
only — a `make` or `cargo` process reads the FIFO directly and is
uninstrumented. The only time series is the **global** pool size
(`tools/bga_timeline.py:596-614`).

The feedback closes: the broker grants by slack read from
`--plan analyze.json` (`UX-849`). Slack says which element's delay costs
the build; it does not say what a token is *worth* to that element. A
measured per-element response curve is the missing input that would let
the pool grant by marginal value. The analysis that models the axis is
the analysis that improves the scheduler that varies the axis — and each
turn of that loop produces the measurements the next model needs.

## 6. What would have to be captured, in cost order

1. **Nothing** — for §4's floor and for a per-element `cores_busy`
   already published. (§8.)
2. **A per-element width series under the jobserver.** Record
   `(element, t, tokens_held)` for every proxy, not only the wrapped
   tools, and publish it as a bounded series beside the global pool
   track. Cheapest real addition: the broker already knows the grant, it
   is written to no per-element ledger.
3. **Periodic per-pid CPU.** Sample `/proc/<pid>/stat` `utime+stime`
   over the traced pid set on the host sampler's existing tick — the
   spine already reads that file once (`tools/native_trace/spine.c:461`).
   This turns `cores_busy` from an average into a curve and is what
   distinguishes "wide for half the span" from "half-wide throughout".
   Cost: one read per tracked pid per 2s, and a bounded series per
   element in the report rather than in the log.
4. **The resolved per-element `max-jobs`.** From BuildStream's own
   element configuration rather than an argv regex over three binaries,
   so the axis's input is measured wherever the axis exists.
5. **A contract for `plane2.log.gz`**, if anything is ever to be
   certified from the raw intervals. `UX-297` is the reason not to put
   them back in the report; a versioned log is the other way.

Items 2-4 are each a filing. None is a precondition for item 1.

## 7. What this declines

- **Declines to change `lb`, `certified_headroom` or
  `efficiency_score`.** §4c.
- **Declines to model speedup.** No Amdahl fit, no assumed parallel
  fraction. Where the corpus holds the same element at two widths, the
  curve is measured; where it does not, the answer is absent, as
  `t_infinity_cold` is absent rather than guessed (Part 15.3).
- **Declines to attribute host busy-cores to elements.** `/proc/stat` is
  whole-machine. Per-element CPU comes from per-element rusage or not at
  all; the two are never mixed to fill a gap.
- **Declines to recommend a `--max-jobs` value from the new floor.**
  `compute_max_jobs_advice` (`bga/correlate.py:1246`, `UX-677`) already
  owns that recommendation under a stated equal-share assumption. A
  floor is a bound, not advice, and a second recommender on one question
  is the drift this repository fixes most often.
- **Declines to bill contention.** "This build would have been faster on
  a quiet box" is a counterfactual, and the run measured one box.

## 8. The recommended first increment

One filing, one commit, `Serves: R5, R2`, `Topic: analysis`,
`Area: bga`. Publish the CPU floor from the contracted aggregate that
already exists. Filed as `UX-891`; the shape this text derives is
`judgement`, not the `mechanical` this section first claimed — the four
keys are declared in `bga/schemas.py`, which `dev_close_task.py
--shape` reads as a contract surface.

**Required fix.** In `bga/floors/`, a `cpu.py` beside `capacity.py`
computing `total_cpu_us // governing_cores` from the joined Plane 2
report, and in `floors`:

| key | value |
|---|---|
| `lb_cpu_us` | the floor, integer µs; **absent** without Plane 2 or without a governing core count, never `0` |
| `lb_cpu_coverage` | `measured_processes / (measured + unmeasured)` |
| `lb_cpu_governing_cores` and `lb_cpu_cores_source` | the number and whether it came from `cpu_budget` or `host_cpu_count` |
| `lb_cpu_binds` | whether `lb_cpu_us > lb` |

The Certified Floors block gains one line and the standing note gains
one clause naming which floor binds. `lb`, `certified_headroom`,
`efficiency_score` and every Part 16 term are untouched, so `analyze/v6`
gains keys under the rule that additive keys do not bump a contract —
but `lb_cpu_us` must not enter `required`, which would
(`test_a_required_set_grew_under_an_unchanged_id.py`).

Print the assumptions with the number, in the form
`bga/capacity_model.py:36-89` already uses: that CPU work is assumed
conserved under a different schedule; that the coverage share is what it
is; that the governing cores are the whole machine and a co-tenant is
not modelled.

**Acceptance test.** On `tests/fixtures/macro_micro`:
`lb_cpu_us == 17446564` (69786259 // 4), coverage `663/813`, governing
cores 4 from `host_cpu_count`, `lb_cpu_binds` false against `lb`
43200000. On `tests/fixtures/golden/mixed_task_kinds` (no Plane 2) every
key is absent and the report's existing note is byte-identical to today.

**And the trap in that fixture.** It has builders == cores == 4, so a
floor divided by the *builder* count returns the same 17446564 — and
`compute_default_capacities` reads exactly that field for `PROCESS`
(`run_context.max_jobs`, `bga/floors/capacity.py:43-46`), so the
confusion is one attribute away. An acceptance test that runs only this
fixture is a guard another gate already excludes, which is the shape
`CLAUDE.md` lists third. So it runs a second case on a copy with
`host_cpu_count` edited to 8, where the two candidate divisors give
8723282 and 17446564.

**The mutations that redden it** (`falsify`), each aimed at one
assertion:

1. Drop one element's `cpu_us`. The floor falls; coverage does not move.
   Catches a floor summed from the wrong field.
2. Move ten processes from `measured_processes` to
   `unmeasured_processes`. Coverage falls; the floor does not move.
   Catches a coverage derived from the floor's own inputs.
3. Halve `host_cpu_count`. The floor doubles. Catches the divisor above.

**Why this one first.** It needs no new capture, no hook contract, no
spec edit, and no new recommender. It converts a disclaimer sentence
into a number, and it is the measurement every later increment in §6 has
to be validated against.

## 9. If this is adopted as a Direction

It is not numbered here on purpose. `## Direction 21` in
[`directions.md`](directions.md) would redden
`test_every_direction_names_its_reader.py::test_the_walk_finds_every_direction_the_document_argues`,
which asserts the numbering is exactly `range(1, 21)`, and would want a
round-history row pointing at an audit document that does not exist.
Both are one-line moves for a session that is running that round; both
are out of scope for a document that changes no code. Until then this
file is the argument, and §8 is the row to file — filed as `UX-891`,
with §6's items 2-4 as `UX-892`, `UX-893` and `UX-894`.

One trap for whoever cites this file next. Writing its name immediately
before a section id — the `<document> §N` shape — pulls it into
`test_the_styleguide_names_its_guards.py`'s population of process
documents, where its §1-§9 collide with five documents that already
number those ids. Measured: four reds in that file the first time the
filings above cited it that way. Cite it as "section 4c of
`in-step-parallelism.md`" instead; it is an argument, not a process
document, and it does not belong in that id space.
