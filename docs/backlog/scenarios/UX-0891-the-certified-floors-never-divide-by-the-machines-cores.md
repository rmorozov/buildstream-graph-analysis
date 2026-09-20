# UX-891: the certified floors never divide by the machine's cores

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 131, [`docs/design/in-step-parallelism.md`](../../design/in-step-parallelism.md) §8 — the design document argued the axis and named this as the one increment that needs no new capture | **Serves:** R5 (the capacity operator asking whether zero headroom on a four-core box is true), R2 second | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

Every floor in Part 16 divides work by a *builder slot* count.
`compute_default_capacities` reads `resource_capacities['PROCESS']`,
falling back to `run_context.max_jobs`
(`bga/floors/capacity.py:43-46`), so `LB` certifies against the
scheduler's width and never against the machine's. The CPU the same
capture measured is published a few sections further down the same
report and is joined to nothing:

```text
$ python3 -m bga.cli analyze tests/fixtures/macro_micro/run \
    --plane2 tests/fixtures/macro_micro/plane2.json -f json -o /tmp/mm.json
$ python3 - <<'PY'
import json
f = json.load(open("/tmp/mm.json"))["floors"]
p = json.load(open("tests/fixtures/macro_micro/plane2.json"))
c = p["cpu_time"]
r = json.load(open("tests/fixtures/macro_micro/run/run-context.json"))
n = r["host_cpu_count"]
print("lb %d  headroom %d  efficiency %s  occupancy %.4f"
      % (f["lb"], f["certified_headroom"], f["efficiency_score"], f["occupancy_share"]))
print("total_cpu_us %d  wall_span_s %.3f  cores_busy %.2f"
      % (c["total_cpu_us"], p["wall_span_s"], c["total_cpu_us"] / 1e6 / p["wall_span_s"]))
print("host_cpu_count %s  cpu_budget %s  max_jobs %s  PROCESS %s"
      % (n, r.get("cpu_budget"), r["max_jobs"], r["resource_capacities"]["PROCESS"]))
print("total_cpu_us // host_cpu_count %d   coverage %d/%d"
      % (c["total_cpu_us"] // n, c["measured_processes"],
         c["measured_processes"] + c["unmeasured_processes"]))
PY
lb 43200000  headroom 0  efficiency 1.0  occupancy 0.2905
total_cpu_us 69786259  wall_span_s 43.508  cores_busy 1.60
host_cpu_count 4  cpu_budget None  max_jobs 4  PROCESS 4
total_cpu_us // host_cpu_count 17446564   coverage 663/813
```

Four builder slots 29.1% used, certified headroom zero — and 1.60 of
four cores busy over the same span. The report's own
`capacity_model_note` says the axis is unmodelled; nothing turns that
sentence into a number.

## Required Fix

A `bga/floors/cpu.py` beside `capacity.py` computing
`total_cpu_us // governing_cores` from the joined Plane 2 report, and
four keys in `floors`:

| key | value |
|---|---|
| `lb_cpu_us` | the floor, integer µs; **absent** without Plane 2 or without a governing core count, never `0` |
| `lb_cpu_coverage` | `measured_processes / (measured + unmeasured)` |
| `lb_cpu_governing_cores` and `lb_cpu_cores_source` | the number, and whether it came from `cpu_budget` or `host_cpu_count` |
| `lb_cpu_binds` | whether `lb_cpu_us > lb` |

Reuse `_check_process_oversubscription`'s own term rather than
recomputing it: `governing_cores = cpu_budget if cpu_budget is not None
else host_cpu_count` with its `capacity_source` is already written at
`bga/analyzer.py:1066-1067`.

The Certified Floors block gains one line and the standing note one
clause naming which floor binds. `lb`, `certified_headroom`,
`efficiency_score` and every other Part 16 term are untouched, so
`analyze/v6` gains keys under the rule that additive keys do not bump a
contract — but `lb_cpu_us` must not enter `required`, which
`test_a_required_set_grew_under_an_unchanged_id.py` reads.

The four keys are declared in `bga/schemas.py` beside the existing
`floors` properties (`bga/schemas.py:3696-3720`), which is why this is
a contract surface and not a self-contained module.

Print the assumptions with the number, in the form
`bga/capacity_model.py:36-89` already uses: CPU work is assumed
conserved under a different schedule; the coverage share is what it is;
the governing cores are the whole machine and a co-tenant is not
modelled.

## Decomposition

surfaces: `bga/floors/cpu.py` (new), `bga/analyzer.py` (the floors block and the standing note), `bga/schemas.py` (four additive `floors` properties, none in `required`)
guards: `test_the_cpu_floor_divides_by_cores.py` (new); `test_a_required_set_grew_under_an_unchanged_id.py` (existing) must stay green
gap: a co-tenant on the same box is not modelled, and the coverage share is published rather than corrected for — both are printed assumptions, not silent ones
track: independent of UX-892, UX-893 and UX-894; none of them is a precondition for this one, and this is the measurement each of them is validated against
gate: not yet scheduled

Input classes: Plane 2 present with a governing core count → the floor;
Plane 2 present, no `cpu_budget` and no `host_cpu_count` → every key
absent; no Plane 2 → every key absent and the existing note unchanged;
`total_cpu_us` present but zero → the floor is `0` and present, which is
not the absent case; coverage 1.0 and coverage below 1.0 → the same
floor, a different published share.

## Out of Scope

Changing `lb`, `certified_headroom`, `efficiency_score` or any Part 16
term — the new floor is published beside them, never folded in
(section 4c of `in-step-parallelism.md`). Editing
`docs/spec/specification.md`
outside Part 32. Recommending a `--max-jobs` value from the new floor:
`compute_max_jobs_advice` (`bga/correlate.py:1246`, `UX-677`) owns that
question and a second recommender on one question is the drift this
repository fixes most often. Any new capture.

## Acceptance Test

`tests/unit/test_the_cpu_floor_divides_by_cores.py`, two cases.

On `tests/fixtures/macro_micro`: `lb_cpu_us == 17446564`
(69786259 // 4), `lb_cpu_coverage` from 663/813,
`lb_cpu_governing_cores == 4` with `lb_cpu_cores_source ==
"host_cpu_count"`, and `lb_cpu_binds` false against `lb` 43200000. On
`tests/fixtures/golden/mixed_task_kinds` (no Plane 2) every key is
absent and the report's existing note is byte-identical to today.

**The trap this guard has to clear.** `macro_micro` has
builders == cores == 4 (`PROCESS 4`, `host_cpu_count 4` in the block
above), so a floor divided by the *builder* count returns the same
17446564 — and `compute_default_capacities` reads exactly that field
one attribute away. A guard that runs only this fixture is one another
gate already excludes, the shape `CLAUDE.md` lists third. So the second
case runs a copy with `host_cpu_count` edited to 8, where the two
candidate divisors give 8723282 and 17446564.

**Mutations** (`falsify`), one per assertion:

1. Drop one element's `cpu_us`. The floor falls; coverage does not
   move. Catches a floor summed from the wrong field.
2. Move ten processes from `measured_processes` to
   `unmeasured_processes`. Coverage falls; the floor does not move.
   Catches a coverage derived from the floor's own inputs.
3. Halve `host_cpu_count`. The floor doubles. Catches the divisor.

## Outcome
