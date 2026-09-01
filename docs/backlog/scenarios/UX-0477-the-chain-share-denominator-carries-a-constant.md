# UX-477: one graph, two verdicts — the chain-bound line is decided by how long the build is

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 72, `UX-468`'s planted walk — a six-element strict chain was diagnosed "scheduler-bound, not chain-bound" | **Serves:** the graph-owner whose build really is a chain and is told the time is going somewhere other than the chain | **Topic:** analysis

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

**Round 73 · 2026-09-01 · Status: 🟢 Done — the denominator is the task horizon, and the distribution the row asked about now has a gap in it**

### The change

`diagnose()` divides by the **task horizon** — `total_duration_us`
minus the untracked head and tail — which is Part 12's own identity
(`UNTRACKED_HEAD + task-horizon attribution + UNTRACKED_TAIL ==
wall_clock`) read the other way round. Which span was used is published
as `headline.chain_share_of`, and it distinguishes *"we subtracted and
it was zero"* from *"we could not look"*: a capture whose attribution
never ran reports `wall_clock`, because claiming `task_horizon` over a
subtraction that did not happen is the overclaim the field exists to
prevent.

### Every committed capture, before and after

```text
capture                          T_inf    wall   head   tail  horizon  wall%  horiz%  old -> new
a_build_that_pulls               12.00   12.00   0.00   0.00    12.00  1.000   1.000  chain -> chain
ample_capacity                    3.70    3.70   0.00   0.00     3.70  1.000   1.000  chain -> chain
macro_micro                      43.20   46.13   2.72   0.22    43.20  0.936   1.000  chain -> chain
one_source_many_elements          4.00   16.00   0.00   0.00    16.00  0.250   0.250  sched -> sched
same_build_twice_cold             8.00    8.00   0.00   0.00     8.00  1.000   1.000  chain -> chain
same_build_twice_incremental      2.00    2.00   0.00   0.00     2.00  1.000   1.000  chain -> chain
shared_base_wide                  6.20   11.30   0.00   0.00    11.30  0.549   0.549  sched -> sched
with_timeline                    43.20   46.13   2.72   0.22    43.20  0.936   1.000  chain -> chain
golden/mixed_task_kinds           0.01    0.02   0.00   0.00     0.01  0.875   1.000  sched -> chain   ***
planted-serial-chain (4.5s)      26.90   28.31   1.26   0.15    26.90  0.950   1.000  chain -> chain
planted-fat-shared-base          22.00   23.75   1.28   0.28    22.20  0.926   0.991  chain -> chain
planted-one-heavy-element         7.20    8.65   1.28   0.17     7.20  0.833   1.000  sched -> chain   ***
planted-serial-chain (1.5s)       8.95   10.35   1.25   0.14     8.95  0.865   1.000  sched -> chain   ***
```

Three flips, all in one direction, and every one is a graph whose
critical path is the whole of its own task window. **The two genuinely
scheduler-bound captures do not move at all** — 0.250 and 0.549, before
and after — because neither has a head to remove. The change subtracts
time the graph cannot explain and nothing else.

### `CHAIN_BOUND_RATIO = 0.9`, re-checked against the new denominator

The row required this, and the answer is different from `UX-458`'s:

```text
  old (wall-clock)   0.250  0.549  0.833  0.865  0.875  0.926  0.936  0.950  1.000 x5
  new (horizon)      0.250  0.549  0.991  1.000 x10
```

Against wall-clock the values crowd the line — 0.865, 0.875, 0.926,
0.936, 0.950 straddle 0.9 within eight hundredths. Against the horizon
there is an **empty band from 0.549 to 0.991**, and 0.9 sits inside it
with room on both sides. So the constant stays where it is, and now for
a reason rather than for want of a better idea: it is no longer near
anything.

`UX-456` measured `examples/06` twenty times and read 0.853–0.916 as a
clause standing too near a cut. It was not dispersion around a value —
it was a denominator with a constant in it, and the recorded run read
0.936 while the live rebuilds read lower because the recorded run is
longer and its fixed head is a smaller share of it.

### The guard, and every mutation

`tests/unit/test_the_diagnosis_follows_the_shape.py`, 13 clauses. The
first two are the pair: one asserts the two scales agree, the other
asserts that **against wall-clock they would not** — without the
second, a guard would still pass if the denominator went back and the
threshold moved to cover both, which is the mutation not
discriminating.

```text
P1  the denominator goes back to wall-clock       5 failed, 8 passed
P2  the tail is left in the denominator           1 failed, 12 passed
P3  chain_share_of always claims the horizon      1 failed, 12 passed
P4  the sentence says "of wall-clock" again       1 failed, 12 passed
restored                                         13 passed
```

Each was applied and proved to have landed (`grep -c` on the mutated
line printed 1) before the run. Three single-process timings:
`0.000 / 0.000 / 0.000` — pure arithmetic over hand-built objects, so
it stays in the default tier.

### What else moved, and why each is the change working

Twenty-six clauses reddened. None of them was the change being wrong;
all of them were a fixture or a document that had been standing on the
old verdict.

- **`test_the_first_screen_is_a_decision`** kept its scheduler-bound
  branch by moving it off the golden run and onto `shared_base_wide`,
  which is scheduler-bound *by shape* — six modules over one base on
  two lanes — rather than by startup. Same for `test_copy_a_finding`'s
  five blast-radius clauses and `test_the_readme_block`'s two-rules
  clause, which now reads across two runs because the two rules that
  gate on `CHAIN_BOUND_RATIO` sit on opposite sides of the same branch
  and no single capture publishes both.
- **`test_the_next_step_is_a_command`** gained a clause of its own:
  *the sweep is not offered on a chain*. `UX-468`'s walk 3 is why —
  "more builders would buy" was being offered on strictly serial
  graphs. The golden run no longer offers it, and the guard now says
  so out loud.
- **`test_no_level_carries_nothing`**: the golden's deepest leaf went
  5 → 7 and its deeper-than-three ratio 0.462, against a 0.45 bound.
  Nothing about the document got deeper: 7 is
  `findings.[].evidence.steps.[].entering.[]`, the chain-bound arm's
  own shape, which `macro_micro` has always published and the tree
  already accepts at 7. The ratio is still below the 0.574 `UX-344`
  filed. Both bounds restated with that measurement rather than
  raised.
- **The export**: +7,932 B on the golden, and **the page half did not
  move at all** — 291,588 B before and after, by the file's own
  splitter. All of it is data: the chain-bound arm publishes four
  findings with evidence where the other published one ranking. The
  note also records that the recorded 391,543 B was 2,037 B stale, so
  the old bound had 420 B of headroom rather than the ~4 KB it claimed.
- **The README** block and the golden snapshot were regenerated. The
  paragraph under the block used to say *"88% sounds chain-bound, and
  the sentence says the opposite"*; it now says why the two lines above
  it name two different denominators, which is a better thing for a
  front door to teach.

### A divergence this surfaced, and how it was resolved

`test_why_bga_believes_what_it_believes` asserted that the page shows
`str(value)` for each evidence value. Python spells a whole float
`1.0`; JavaScript spells it `1`. No evidence value on that fixture had
ever been whole, so the two had never disagreed — and a `chain_share`
of exactly 1.000 is ordinary against the horizon. The guard now
compares numbers **as numbers** and everything else exactly, because
the claim it makes is that the page shows no value the record does not
hold, and 1 and 1.0 are one value. Recorded rather than quietly
widened: a guard that demanded a JavaScript renderer reproduce Python's
number formatting would be asserting the wrong thing.

### What this did to the rows behind it

`UX-478` is partly answered by this change alone. The golden run's
published reader index gained `graph-owner` and `recipe-author`, and
`sweep-the-capacity` left its next steps — visible in the golden
snapshot's diff. What remains of `UX-478` is that R3's presence is
still a function of the diagnosis rather than of the graph, which is
that row's own Required Fix.

### Deviation from the Required Fix

None. All three clauses are done: the denominator, the re-check of
`CHAIN_BOUND_RATIO` against it, and the guard that reddens on the pair.

### Verification

```text
make lint                  clean (ruff + PyMarkdown)
dev_close_task.py --check  0 problems
make test                  5604 passed, 27 skipped in 309.59s
```
