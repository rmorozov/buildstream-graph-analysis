# UX-477: one graph, two verdicts — the chain-bound line is decided by how long the build is

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 72, `UX-468`'s planted walk — a six-element strict chain was diagnosed "scheduler-bound, not chain-bound" | **Serves:** the graph-owner whose build really is a chain and is told the time is going somewhere other than the chain | **Topic:** analysis

## Motivation

`diagnose()` is the branch every consumer reads (`UX-207`):

```python
    ratio = t_infinity / total
    name = (DIAGNOSIS_CHAIN_BOUND if ratio >= CHAIN_BOUND_RATIO
            else DIAGNOSIS_SCHEDULER_BOUND)
```

`t_infinity` is the critical path; `total` is `result.total_duration_us`
— **wall-clock**, which carries a fixed BuildStream head the graph
cannot explain. The run's own `wait-category` finding names it:

> Biggest wait category: 12.1% of wall-clock time is UNTRACKED HEAD
> (1.25s) — real time before the tracked-task window started
> (BuildStream startup, cache query, sandbox staging) — see Pipeline
> Overhead, **not a scheduling issue**

That constant is in the denominator, so the ratio falls as the build
gets shorter, whatever its shape.

`UX-468` measured it on a project generated for the purpose — six
elements in one strict line, no branch anywhere — with only the
per-element seconds changed between the two runs:

```text
  spec                          per link  critical path  chain_share  diagnosis
  planted-serial-chain.json       1.5s        8.95s         0.865     scheduler_bound
  the same spec, seconds -> 4.5   4.5s       26.9s          0.950     chain_bound
```

```text
1.5s: "This build is scheduler-bound, not chain-bound: the critical path is 87%
       of wall-clock, below the 90% chain-bound line, so the time is going
       somewhere other than the chain."
4.5s: "This build is chain-bound, not scheduler-bound: the critical path is 95%
       of wall-clock, at or above the 90% chain-bound line, so the way to a
       shorter build is a shorter chain."
```

The graph is byte-identical. `Parallelism Profile: min=1.0x, avg=1.1x,
max=2.0x` in both. The first sentence is false about the first run: the
time is *not* going somewhere other than the chain, it is going to
BuildStream's startup, which the same report identifies correctly one
block above.

Two things follow from the wrong verdict on the short run, both
measured in `UX-468`:

- the front door offers `bga sweep` — *"the sweep says what more
  builders would buy"* — on a graph where a second builder buys
  nothing;
- the **graph-owner reader is dropped entirely** (`UX-478`), and no
  blast radius is published for an actionable element (`UX-479`),
  because both key off this branch.

`UX-456` measured `examples/06` twenty times and found 0.853–0.916,
19 of 20 below the line, and read it as a clause standing too near a
cut:

> the same *project*, recorded, reads 0.936, and rebuilt live reads
> 0.853–0.916

That is the same effect: the recorded run is longer than the live
rebuild, so its fixed head is a smaller share. It is not dispersion
around a value — it is a denominator with a constant in it.

## Required Fix

- **Take the head out of the denominator, or say why it belongs.** The
  candidate is the tracked-task window rather than wall-clock — the
  span the graph is actually responsible for, which `wait-category`
  already isolates. Whatever is chosen, the argument goes in
  `diagnose`'s docstring with the two runs above as the population, and
  the sentence has to stay true of both.
- **Re-check `CHAIN_BOUND_RATIO = 0.9` against the new denominator**,
  and only then — `UX-456` explicitly left the value alone because
  nothing had established what it was a ratio *of*. Do not move the
  constant to paper over the denominator.
- **A guard that reddens on the pair.** The two runs above are one
  spec and a `seconds` multiplier, so the guard is: the same graph at
  two scales must produce the same `diagnosis`. It reddens today.

## Out of Scope

- **`wait-category` and the Pipeline Overhead block.** Both already say
  the head is not a scheduling issue, and say it correctly. The defect
  is that `diagnose` does not read what they know.
- **The sweep's own recommendation** (`UX-339`'s contract). It is
  offered because the diagnosis said scheduler-bound; fix the
  diagnosis and the offer goes with it. If it survives a correct
  chain-bound verdict, that is a separate row.
- **Long builds.** `planted-fat-shared-base` at 22.0s critical path
  reads 0.928 and is diagnosed correctly. Nothing here says the branch
  is wrong on a real freedesktop-sdk build; it says it is wrong on
  short ones, and short is where a curated fixture lives.

## Acceptance Test

```bash
python3 tools/bga_gen_project.py \
    --spec tests/fixtures/specs/planted-serial-chain.json --out /tmp/short
python3 tools/bga_gen_project.py \
    --spec tests/fixtures/specs/planted-serial-chain-long.json --out /tmp/long
for d in /tmp/short /tmp/long; do
  (cd $d && bga snapshot -- bst build all.bst >/dev/null &&
   bga analyze @last --diagnostics --format json |
     python3 -c 'import json,sys; h=json.load(sys.stdin)["headline"]; print(h["diagnosis"], round(h["chain_share"],3))')
done
```

prints the **same** diagnosis for both, and
`tests/unit/test_the_shape_conclusions_have_a_negative_case.py` (or a
sibling) carries the scale-invariance clause.

## Outcome

_Not started._
