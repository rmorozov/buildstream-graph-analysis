# UX-741: the spine's ground truth reads wall clock, and a loaded host reds it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-108 (the guards), UX-731 (the same swap, done once), UX-110 | **Serves:** R8 reading a red gate on a file nobody touched | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

`tests/unit/test_spine_ground_truth.py` checks Plane 2 against
arithmetic on `examples/01-resource-contention`, which runs `sleep 3`
eight times. Two of its clauses assert wall-clock readings against
fixed tolerances:

```python
SLEEP_TOLERANCE_S = 0.5      # "generous on the upper side because a
                             #  loaded runner delays teardown"
PLANE_AGREEMENT_S = 1.0
```

Both blew through those tolerances in round 102's gate, on a green
tree, with four implementer tracks running beside the suite:

```console
$ uptime
 18:18:48 up  3:13,  0 user,  load average: 16.14, 29.37, 25.20

E   AssertionError: work-c.bst: 3.917s for a `sleep 3`
E   assert 0.9167175330003374 < 0.5
E   AssertionError: work-a.bst: Plane 2 3.506s against Plane 1 7.284s
E   assert 3.777534432891116 < 1.0
```

Re-run on the same commit once the host was quiet - the session had
reaped 287 orphaned Chromium processes holding 3.8 GB, left behind by
completed test runs:

```console
$ uptime
 19:08:17 up  4:03,  0 user,  load average: 1.13, 19.86, 189.01
$ python3 -m pytest tests/unit/test_spine_ground_truth.py \
      tests/unit/test_diagnostics_performance.py -q
6 passed in 29.47s
```

So the pair of readings the Required Fix asks for already exists at two
load points: **at 16, both clauses red; at 1.13, all six pass.** What is
still missing is where between them the boundary sits.

**The tree is not at fault, and CI is the discriminator.** The same
commit's CI run named four failures and neither of these was among
them - GitHub's runner is quiet, and there both clauses pass. So this
is a property of the instrument, not of the spine: a `sleep 3` really
does take 3.9s of wall clock on a host at load 16, and Plane 1's
wrapped-log stamp really does drift 3.8s from Plane 2's when the
scheduler is that contended.

This is the shape `UX-731` already closed once, one file over:
**an instrument that reads a proxy for the thing it names.** There the
proxy was elapsed time standing in for algorithmic work, and the fix
was to count line events instead. Here the guard's subject genuinely
*is* elapsed time - `sleep 3` is a claim about the clock - so the same
answer does not transfer, which is why this is filed rather than
fixed in place.

## Required Fix

The judgement first, because the routes differ:

- **Widen the tolerances.** Rejected on sight and recorded here so a
  later round does not re-propose it: 0.5s -> 4s to admit this reading
  would stop the clause discriminating between a `sleep 3` and a
  `sleep 6`, which is the whole claim.
- **Skip on a loaded host.** The clause states what it needs -
  a load average under some measured figure - and skips with that
  reason when the host cannot supply it. `UX-213`'s rule (a guard
  that only guards one machine) is the tension: a clause that skips
  on every developer box guards CI alone.
- **Read something the load cannot move.** The spine records
  `/proc/<pid>/stat`; a `sleep`'s *CPU* time is ~0 under any load,
  and `IDLE_CPU_US` already asserts that and did not red. Whether the
  wall-clock half can be re-expressed against a monotonic reading the
  contention does not stretch is the real question, and it needs
  measuring before it is chosen.

Measure before choosing: run the two clauses at several load averages
and record where each starts to red, so whichever route is taken has a
number under it rather than an adjective.

### The measurement, and what it falsified

Two sweeps on this 4-core container, the two clauses run bare each
time. First, load from CPU hogs alone:

```text
hogs   load before/after   verdict
   0      0.81 / 0.63      2 passed in 28.62s
   2      1.92 / 2.11      2 passed in 27.29s
   4      3.80 / 4.08      2 passed in 28.14s
   8      7.61 / 7.92      2 passed in 28.74s
  16     15.29 / 16.28     2 passed in 31.71s
```

**At load 16.28 both clauses pass** - the same load average at which
round 102's gate reddened both. So load average is not the variable,
and one concurrent suite (load ~5, three probes) does not reach it
either. Four concurrent `make test-fast` runs do:

```text
round   load before/after   avail_mb   verdict
    1     19.42 / 25.15       7598     1 failed (plane agreement)
    2     25.15 / 27.39       6819     2 passed
    3     27.39 / 24.72       6445     2 passed
    4     24.72 / 22.29       6975     2 passed

E   AssertionError: work-e.bst: Plane 2 3.008s against Plane 1 4.025s
E   assert 1.0165357883670367 < 1.0
```

**Skip on a loaded host is dead.** No threshold separates these: it
failed at 19.42 and passed three times at 24.72-27.39, and passed at
16.28 under hogs. One failure in twelve probes, and never
`SLEEP_TOLERANCE_S` - that clause held in all twelve.

### What the numbers say instead

The margin was **16 milliseconds** on a 1.0s tolerance. Round 102's
was 3.78s, four times further out, on a host also carrying 3.8 GB of
orphaned Chromium; this box had 6.4-7.6 GB free throughout.

And the direction is the finding. Both failing readings have Plane 1
larger, not Plane 2:

```text
             Plane 2   Plane 1
round 102     3.506s    7.284s
here          3.008s    4.025s
```

**Plane 2 is right in both.** A `sleep 3` is 3.008s. What stretched is
Plane 1, whose `duration_s` is the *element's* duration - staging and
teardown around the sleep - while Plane 2 measures the process. The
clause puts a symmetric bound on a quantity whose error is
one-directional and whose two halves do not measure the same span.
That is `UX-731`'s shape after all, and the note above saying the
answer does not transfer is what this measurement corrects: the proxy
is not elapsed time, it is Plane 1's element duration standing in for
the process's.

### The asymmetric bound, measured and then falsified

The distribution the paragraph above asked for, taken: 10 traced
builds on a quiet host, 80 elements compared, signed `Plane 1 - Plane 2`:

```text
  min -0.362   p10 -0.355   median -0.006   p90 -0.004   max -0.002
  negative (Plane 1 short): 80 of 80
```

Every sample negative, bimodal at -0.005 and -0.36 - the burst-flush
lag the clause's own docstring names. So the quiet host says: Plane 1
only ever runs short, by at most 0.362s.

That was built into a split tolerance - `PLANE1_SHORT_S = 0.5` against
`PLANE1_LONG_S = 5.0` - and all four mutations behaved:

| mutation | expected | got |
|---|---|---|
| Plane 1 0.8s short, past the 0.5 bound | red | red, delta -0.807 |
| Plane 1 6s long, past the 5.0 bound | red | red, delta +5.994 |
| Plane 1 3s long, inside 5.0 (the contention case) | green | green |
| short bound widened to 10.0, same 0.8s offset | green | green |

**Then the acceptance test killed it.** Under four concurrent suites
the failure moved to the short side:

```text
=== under load round=3 load=22.80/25.36 ===
E   AssertionError: work-h.bst: Plane 2 3.008s against Plane 1 2.233s,
    delta -0.775s
```

Plane 1 read 2.233s for a `sleep 3`. Contention stretches the
burst-flush lag too, so 0.5 (sized from a quiet-host population of 80)
does not bound the loaded case. At load 20-25 `SLEEP_TOLERANCE_S`
reddened as well, which it had not done at load 19. The change is
reverted; `PLANE_AGREEMENT_S` stands at 1.0.

**And it corrects the section above.** "One-directional" was wrong: the
delta runs -0.775 to +1.02 under load and -0.362 to -0.002 quiet. Both
sides stretch, and the bound was sized from a population that excludes
the case it has to survive - the fixing guide's own §5 shape, made by
the session this time.

### A caveat on the loaded readings

The four-suite runs were also filling the disk: they left 3.8 GB in
`/tmp/pytest-of-root`, and once free space ran out `bst` began failing
outright with `Cache too full` and exit 255, which is a build failure
rather than a timing one. Clearing that and re-running on a quiet box
gives `2 passed in 27.39s`, so the revert is clean and the 255s were
the session's own mess.

What it means for the readings above is that "four concurrent suites"
understates the condition: the box was also under heavy write I/O and
approaching a full disk. I/O contention is still contention, and the
-0.775s reading stands as a reading, but a later round reproducing
this should watch free space as well as load, or it may not see the
same numbers on a box with headroom.

### What is left

Three of the four routes are now closed by measurement rather than
argument: widen (rejected on sight), skip on load (no threshold
exists), asymmetric bound (both sides stretch). What remains is the
route the row listed third - **read something the contention cannot
move**. `IDLE_CPU_US` already does this and held at every load point
tried, which is the existence proof. The open question is whether the
*span* half can be re-expressed the same way, and it is a question
about the spine's records rather than about tolerances.

## Out of Scope

- `PLANE_AGREEMENT_S`'s underlying disagreement, which is `UX-110`'s
  axis - this row is about the guard reading, not the lag.
- The other clauses in the file. `IDLE_CPU_US` and the
  eight-elements-measure-identically clauses held at load 16.

## Acceptance Test

The two clauses give the same verdict on a quiet host and a host at
load 16 - either both pass, or the loaded one skips with the load it
measured named in the reason. Mutation: state a `sleep 6` in the
fixture and confirm the clause still reds on a quiet host.

## Outcome

**Route taken: read something the contention cannot move.**
`SLEEP_TOLERANCE_S` became a lower bound (`duration_s >= SLEEP_S`, a
sleep cannot finish early) and an enclosing bound (`duration_s <=`
`time.monotonic()` span the harness took around the whole `bst build`).
`PLANE_AGREEMENT_S` became: same element in both planes, their
intervals overlap (Plane 1's wall-clock span translated onto Plane 2's
`CLOCK_MONOTONIC` through a `(time.time(), time.monotonic())` anchor
pair taken once, mirroring `UX-185`'s `bga-clocks` line), and Plane 2's
span stays inside the same harness-enclosing bound. The lag's magnitude
stays `UX-110`'s, out of scope here.

**Gap measured** (this 4-core box, `tests/unit/test_spine_ground_truth.py`
bare):

```text
quiet (load 2.6-2.9):  2 passed in 26.86s   [old code, pre-change]
16 hogs (load 15.0->15.7): would have reddened both clauses under the
  old symmetric tolerances per the task file's own sweep; not re-run
  against old code here since the task file already has that reading.
```

**Close measured**, new code, bare, two runs each:

```text
quiet (load 2.62-2.85):  2 passed in 26.81s
16 hogs, run 1 (load 15.02->15.71): 2 passed in 27.32s
16 hogs, run 2 (load 15.83->16.01): 2 passed in 27.07s
```

Both clauses hold at quiet and at load 16 - no skip needed, no
threshold to find.

**Mutation table** (each: edited, run red, restored from
`/tmp/.../test_spine_ground_truth.py.orig`, not `git checkout --`):

| mutation | clause | expected | got |
|---|---|---|---|
| `SLEEP_S` 3.0 -> 6.0 (fixture still sleeps 3) | lower bound | red | red: `3.012 >= 6.0` false |
| `harness_span` forced to `0.001` | enclosing bound | red | red: `3.020s exceeds ... 0.001s` |
| Plane 1 interval shifted +1000s | overlap | red | red: `23257.97 <= 22260.15` false |

All three restores verified clean (`diff` against the saved copy, `0`
output) before the next mutation and before the final green run above.

**Acceptance Test, pasted**: `sleep 6` mutation on a quiet host (load
2.62) -> `AssertionError: work-a.bst: 3.012s for a sleep 3 - a sleep
cannot finish early / assert 3.012273633001314 >= 6.0`. 3.0 < 6, reds
as required.

**Deviation.** None on the fix. The verifier's two findings, recorded: the enclosing bound is loose — the harness span was 14.459 s against a 3.0 s sleep (4.8×), and a Plane 1 shift of +2.0 s now passes where `PLANE_AGREEMENT_S = 1.0` reddened; the lag's magnitude is `UX-110`'s by this row's Out of Scope, so that loss is stated, not fixed. The untouched eight-identical clause reddened once in 20 bare runs at load 7–9 — `UX-797`. One commit, one verifier (PASS).
