# UX-456: two bst-gated guards fail on the runner and not on the diff

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 71, driving PR #190 to green — two red `bst-tests` jobs on superseded heads | **Serves:** the contributor whose PR goes red on a job their diff cannot have touched | **Topic:** guards

## Motivation

Two `bst-tests` runs failed during round 71, on different heads, for
two different reasons. **Neither is a content failure**, and three
consecutive later runs of the same job on the same code plus more were
green — which is what says so.

### One: a threshold decided by 0.3 points of build noise

```text
tests/unit/test_the_journey_has_an_answer_key.py:216:
    assert headline["diagnosis"] == "chain_bound", headline
E   AssertionError: {'diagnosis': 'scheduler_bound',
                     'chain_share': 0.897052541648868,
                     'chain_bound_share': 0.9, ...}
E   assert 'scheduler_bound' == 'chain_bound'
====== 1 failed, 5408 passed, 82 skipped in 468.68s (0:07:48) ======
```

`CHAIN_BOUND_RATIO` is 0.9 (`bga/findings.py:207`). The fixture's cold
build measured **0.897** — 0.3 points under the line, on a real
`bst build` on a shared runner. The clause asserts which side of a
threshold a *measured build* landed on, which makes it a coin flip
whenever the fixture's own chain share sits near the cut. Nothing about
the diff moved it, and nothing about the diff could.

This is the fixing guide's §5 in its "ratio at the noise floor" shape,
in a guard rather than in an instrument: the number is real and the
comparison is at the resolution where the runner decides it.

> **Round 71, on measuring it (§3.6):** "0.3 points under the line" is
> an understatement. Twenty cold builds put this fixture's median at
> **0.859**, with 19 of 20 under 0.9 — the clause was not near the cut,
> it was on the far side of it and kept green by CI's load. See the
> Outcome.

### Two: eighteen setup errors from one dead browser

```text
tests/unit/test_a_control_acts_on_what_it_names.py:139: in browser
    with Browser(chrome) as opened:
tests/browser.py:93: in __enter__
    raise RuntimeError(f"{self.binary} did not open a debugging port")
E   RuntimeError: /usr/bin/google-chrome did not open a debugging port
===== 5397 passed, 82 skipped, 5 warnings, 18 errors in 600.39s (0:10:00) ======
```

Eighteen **errors at setup**, every one the same, every one on worker
`gw0`, in one burst. No test body ran, so nothing was asserted about
any page. The run also took `600.39s` — exactly ten minutes — which is
worth checking against whatever bounds that job.

`tests/browser.py` raises this when Chrome does not answer on its
debugging port within whatever window it waits. One dead browser
process took out a whole class; the shape says resource pressure, not
a page.

## Required Fix

- **The chain-bound clause stops asserting a side of a threshold** on a
  measured build. Either the fixture's build is shaped so its chain
  share is not near 0.9 (and the guard says by how much, so a later
  round can see it drift back), or the clause asserts the *published
  chain share against the constant* and leaves the verdict to a fixture
  whose numbers are fixed. The second is what `UX-419`'s family did.
- **`tests/browser.py` says what it waited for**, and retries once. A
  `RuntimeError` that names no timeout cannot tell a slow runner from a
  broken binary, and eighteen identical errors is one fact reported
  eighteen times.
- **Check the 600.39s against the job's own limit** before assuming the
  browser is the whole story.

## Out of Scope

- **Retrying the whole job**: a re-run makes a flake invisible rather
  than fixed, and this row exists so the next one is not diagnosed from
  scratch.
- **`CHAIN_BOUND_RATIO`'s value**: 0.9 is a published threshold with
  its own provenance record. This is about a guard standing on it, not
  about the number.

## Acceptance Test

The chain-bound clause is re-run twenty times against the cold fixture
without flipping, with the fixture's measured chain share pasted and
its distance from 0.9 stated; and `tests/browser.py`'s failure names
the wait it gave up after.

## Outcome, part one (round 71, 2026-08-31) — the browser half

### Why the browser half was done now rather than filed

It recurred on `76648d4` while this row was being written: the same
eighteen setup errors, same file, same worker, `614.66s (0:10:14)`.
Two of ten runs on one PR is not a flake to wait out, and the failing
thing is a **fixture that never started a process** - so there was no
test to quarantine and nothing to weaken.

The discriminating measurement is which job it happens in. On
`9acb5fb` every other job was green, including `test (3.11)`, which
runs the same `make test` in **5m33s**. `bst-tests` runs the `bst`
tier first and then the same suite in **~10 minutes**, on a runner
already loaded. Chrome dies there and nowhere else.

### Two real defects in the launcher

**The port was a race.** `_free_port()` binds a socket, reads the
number and closes it; Chrome binds it later. Between those two moments
the port belongs to whoever asks, and under `-n auto` the things
asking are this suite's own workers. That is why load is the variable.
The retry re-rolls the port rather than re-trying the same one, which
is the only version of a retry that fixes a collision:

```console
G3 ports tried: [55773, 46813] | all distinct: True
```

**The error said nothing.** It named the binary. Eighteen identical
copies of it carried no more information than one - not the port, not
the wait, not whether Chrome was even alive. The two causes are now
distinguished, because they need different fixes:

```console
G1 exits at once (port/sandbox class): raised after 0.2s
    /bin/false did not open a debugging port in 2 attempts of 3s.
    Last: attempt 2 on port 39719 exited 1
G2 runs and never listens (runner class): raised after 4.0s
    .../hang.sh did not open a debugging port in 2 attempts of 2s.
    Last: attempt 2 on port 34277 was still running after 2s
```

G1 returns in 0.2s rather than burning the 30s wait, because a process
that has already exited will never answer.

### The falsification caught a hang I had just written

`_why_it_failed` drains the process's stderr. Called **before**
`_stop()`, that read blocks until EOF - and on the one case the retry
exists for, a browser that runs and never listens, EOF never comes.
G2 hung for the full two minutes instead of raising.

That would have been a suite hang in CI, which is worse than the flake
being fixed. The exit code is now read before the process is stopped
(after `_stop` every code is the signal we sent) and the pipe is
drained after, when the writer is gone. The order is commented in the
code, because it is not obvious and it is load-bearing.

### What was not done then, and why that was wrong

**The `chain_share` half** was left open on the grounds that its
acceptance test needs twenty real `bst build`s and "`bst` is not on
this machine".

**That was false**, and part two begins by correcting it:

```console
$ which bst bwrap && bst --version
/usr/local/bin/bst
/usr/bin/bwrap
2.7.0
```

`bst` 2.7.0 and `bwrap` are both installed here, and the whole
bst-gated tier runs. The acceptance test was runnable the entire time
and was not run. Recorded rather than quietly fixed, because a wrong
claim about what an environment can do is how an item gets deferred
for rounds.

### Verification

```console
$ python3 -m pytest tests/unit/test_a_control_acts_on_what_it_names.py -q
18 passed in 37.04s          <- the file whose 18 errors this is about

$ make lint
All checks passed!

$ make test
5490 passed, 28 skipped, 1 warning in 308.22s (0:05:08)
```

Neither figure proves the CI flake is gone - it never reproduced here,
which is the whole difficulty. What is proved is that both failure
classes now report which one they were, that a collision gets a second
port, and that neither path hangs.

## Outcome, part two (round 71, 2026-08-31) — the `chain_share` half

### The acceptance test, run

Twenty cold builds of `examples/06`, each into a fresh tree with its
own `XDG_CACHE_HOME` — the `walked` fixture's own isolation — reading
`headline.chain_share` off `bga analyze` each time:

```text
 1  chain_share 0.916457  chain_bound
 2  chain_share 0.885665  scheduler_bound
 3  chain_share 0.884593  scheduler_bound
 4  chain_share 0.875534  scheduler_bound
 5  chain_share 0.863477  scheduler_bound
 6  chain_share 0.860699  scheduler_bound
 7  chain_share 0.855943  scheduler_bound
 8  chain_share 0.857829  scheduler_bound
 9  chain_share 0.856568  scheduler_bound
10  chain_share 0.860922  scheduler_bound
11  chain_share 0.854802  scheduler_bound
12  chain_share 0.856024  scheduler_bound
13  chain_share 0.881378  scheduler_bound
14  chain_share 0.866356  scheduler_bound
15  chain_share 0.853143  scheduler_bound
16  chain_share 0.856442  scheduler_bound
17  chain_share 0.863334  scheduler_bound
18  chain_share 0.856322  scheduler_bound
19  chain_share 0.856592  scheduler_bound
20  chain_share 0.856325  scheduler_bound

n=20  min 0.853143  max 0.916457  median 0.859264
below the 0.9 line: 19 of 20
```

**Nineteen of twenty.** The clause was not sitting near the line and
occasionally slipping under it — it was *on the wrong side of the
line*, and green in CI because CI's load pushes the share up: the two
CI excursions this row was filed on, 0.888 and 0.897, are both
**higher** than this machine's median of 0.859.

That is the strongest form of the defect the item names. A guard whose
verdict is decided by how loaded the runner is tells you about the
runner. It was never telling anyone the build was chain-bound.

### The fix: assert the rule, not the side

The Required Fix's second option, and now with a reason to prefer it
that is measured rather than argued. `test_the_headline_names_the_chain`
becomes three clauses:

- **the rule** — `diagnosis` follows `chain_share` against
  `chain_bound_share`, both published in the same headline. A function
  of two numbers, so no runner can decide it;
- **the sentence** — it quotes the measured share and the line, which
  is `UX-220`'s rule on this field and true on either branch;
- **the fixture** — `chain_share >= CHAIN_BOUND_FLOOR`, 0.75.

`CHAIN_BOUND_FLOOR` is sized from the twenty-two measurements rather
than chosen: the twenty above span 0.853–0.916 (range 0.063) and CI's
two lowest are 0.888 and 0.897. **0.75 is 0.103 below the lowest of
the twenty-two, about 1.6 whole observed ranges.** It is not
`CHAIN_BOUND_RATIO` and is not meant to be — `CHAIN_BOUND_RATIO`
stays exactly where it is, which the Out of Scope required.

### No classification coverage was lost

The verdict is still guarded on **both** branches, against two
committed run directories whose bytes do not move —
`test_the_first_screen_is_a_decision.py`, the golden run at 0.875
(`scheduler_bound`) and `examples/06`'s recorded capture at 0.936
(`chain_bound`). Which is itself the point: the *same project*,
recorded, reads 0.936, and rebuilt live reads 0.853–0.916. The
variance is the build, not the analysis.

Asserted rather than assumed — B1 below reddens seven of that file's
clauses.

### Mutations

| # | mutation | clause that went red |
|---|---|---|
| B1 | `diagnose`'s comparison inverted | `..._follows_its_own_published_numbers`, **and 7 clauses of `test_the_first_screen_is_a_decision.py`** |
| B2 | both sentences drop the measured share | `..._sentence_carries_the_share_it_decided_on` |
| B3 | `chain_share` published as `ratio / 2` | `..._is_still_a_chain_dominated_build` |

B1 is the one that matters twice: it reddens the new rule clause (so
the rule really is guarded on the live build) *and* the deterministic
guard (so moving the verdict off the measured build cost nothing).

### The third clause: the 600.39s

Checked, and there is no limit to check it against:

```console
$ grep -n "timeout" .github/workflows/ci.yml
53:      # nothing finer. A wall-clock step timeout cannot separate a
62:        run: timeout 120 make test-small
180:      # partition guard's regex stopped at the first `timeout` in this
183:        run: PYTEST_XDIST= timeout 120 make test-small

$ python3 -c "...yaml...jobs['bst-tests']..."
job-level timeout-minutes: None
steps: 11 - none carry one
```

Both `timeout 120` are on the `test` job's small-tier steps.
`bst-tests` has no job timeout and no step timeout, and the run in
question *completed* — 18 setup errors, not a kill. On `9acb5fb` the
same step took **626s** and passed. So 600.39s was the duration and
the browser was the whole story, which is what the clause asked to
rule out.

### The browser half, one round of evidence later

Two more `bst-tests` runs since the fix, and neither had a Chrome
error:

```text
14cdf8d   bst-tests green
799b144   bst-tests red - 1 failed, 5435 passed in 547.29s
          test_the_headline_names_the_chain, chain_share 0.888022
```

`799b144`'s failure is this item's *other* half, now fixed. Against a
base rate of 2 Chrome failures in 12 runs, two clean samples is not
proof and is not claimed as any.

### The replacement clauses, twenty times, against twenty cold builds

The Acceptance Test's own shape, run on what replaced the clause:

```console
$ for i in $(seq 1 20); do
    PYTEST_XDIST= python3 -m pytest tests/unit/test_the_journey_has_an_answer_key.py \
      -q -k "published_numbers or sentence_carries or chain_dominated"
  done
RESULT 20 pass / 0 fail over 20 cold builds
```

Twenty module-scoped fixtures, so twenty fresh `bst build`s of the
example into twenty fresh caches — the same population the twenty
shares above came from, and no flips.

### Verification

```console
$ make lint
All checks passed!

$ make test
5505 passed, 28 skipped, 1 warning in 279.48s (0:04:39)
```

### Deviation from the Required Fix

The Acceptance Test asks for the clause "re-run twenty times without
flipping". The old clause **cannot** satisfy that — it flips 19 times
in 20, which is the finding. What was run instead is the twenty builds
above, plus twenty runs of the three replacement clauses against
twenty fresh cold builds. The distance from 0.9 is stated as the
Acceptance Test asks, and it is a distance the item did not expect:
the median is 4.1 points *below* the line, not above it.
