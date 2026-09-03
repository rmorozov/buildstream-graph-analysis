# UX-595: the capacity model has a fact base and no model

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-234 (which names this as its own filing), UX-339 (the sweep), UX-594 | **Serves:** R5, the capacity operator | **Topic:** store

## Motivation

`UX-234` landed the aggregate fact-base — min/median/p95/max/MAD per
host class — and names this as the filing it does not do.
`UX-580` measured what that leaves R5 with: something aggregates, and
nothing models. Direction 9's second argued step is builders `N` plus
those profiles into utilization and wait-time distributions.

## Required Fix

A model that takes a builder count and the store's measured profiles
and answers utilization and waiting, with **every assumption printed
beside every number** — the arrival process, the service distribution,
what it does with a heterogeneous store.

## Out of Scope

- The cost translation (`UX-596`) — a separate reader and a separate unit.
- Anything requiring the requested-at instant (`UX-594`) until that lands.

## Acceptance Test

The model's output names its assumptions; mutation: remove one
assumption from the printout while the model still uses it — red.

## Outcome (round 84)

`bga/capacity_model.py`, read by `bga snapshot --capacity N,RATE`.

### The gap, re-measured first

```text
$ git grep -ci "erlang\|arrival rate\|wait-time\|queueing model" -- bga/ tools/
bga/store_aggregate.py:1
```

One hit, and it is `store_aggregate`'s own docstring saying it is
**not** a model. The fact base was there; nothing answered with it.

### The close

```text
$ bga snapshot --project <store of 6 finished runs> --capacity 4,400
  4 builder(s), 400 build(s)/day
  unknown host - 6 run(s)
    Service time: mean 703.3s, sd 105.4s, CV^2 0.02, n=6
    Utilization: 81.4% of 4 builder(s)
      assumes per_host_class, finished_runs_only, service_is_the_store,
              arrival_rate_declared, servers_interchangeable, steady_state
    Wait before a build starts: 300.6s
      assumes … + arrivals_poisson, fifo_no_priority, service_general
    Builds waiting: 1.39
      assumes … + littles_law
  Assumptions, each named above by the numbers that rest on it:
    arrivals_poisson: Arrivals are Poisson … Nothing here measures that.
```

**The list is recorded where the arithmetic uses it** (`_Assumed.on`),
not typed beside it — so utilization, true whatever the arrival process
is, carries six ids where the wait carries nine.

The service time is this store's finished runs: `fmean` and the sample
sd over the samples `UX-234` takes its percentiles from. That document
publishes a median and a MAD, the robust centre a reader comparing
machines wants; a queue is a function of the mean and the spread.

The wait is **Allen–Cunneen's M/G/c** — the M/M/c wait scaled by
`(CV_a² + CV_s²)/2`. Plain M/M/c assumes an exponential service time
this store measures and contradicts: CV² is 0.02, the correction 0.51,
the wait 300.6 s against M/M/c's 588.1 s — wrong by 2x while quoting a
measured distribution, which is `UX-129`'s shape exactly.

Three refusals, each a behaviour: a class under `MIN_BASELINE_RUNS` is
not modelled; ρ ≥ 1 publishes the utilization and no wait, a finite one
being a number about a system that never reaches equilibrium; a mix of
host classes is modelled per class, exits `EXIT_CODE_MISMATCHED_RUNS`,
and carries `whole_arrival_stream` — a claim, printed as one.

### Mutations verified red and reverted (16)

`arrivals_poisson` unrecorded on the wait · the printout filtering one
id the model used (the Acceptance Test's own) · the legend printing
every assumption bga has · the Allen–Cunneen correction dropped · the
median as the service centre · the population sd · the sample floor
dropped · an unstable queue publishing a wait · an unfinished capture
counted · `whole_arrival_stream` on one class · a mix modelled as one ·
Erlang C collapsed to the one-builder form · an undeclared assumption
accepted · `--capacity 0,40` accepted · the document emitted unstamped ·
`littles_law` on the wait too. **None failed to discriminate.** 38
tests, 0.20 s, `test_the_capacity_model_prints_its_assumptions.py`.

### Deviation from the Required Fix

**Text only.** `--format json` is refused with its reason: the document
carries no schema stamp and an unversioned payload is what `UX-190`
stops. Stamping it needs a `rate` member in `QUANTITIES` — its own
filing, not a line here.

**Stated once, named everywhere.** Eleven sentences repeated under three
numbers is a printout nobody reads: each number names its ids, the
legend states each once, guards hold both directions.

**`bga snapshot --help` was already at its cap of 45.** Two two-line
help entries became one line each to pay for the flag — `UX-158`'s own
remedy, in the file the flag lives in.
