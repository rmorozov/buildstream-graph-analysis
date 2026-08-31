# UX-456: two bst-gated guards fail on the runner and not on the diff

**Priority:** Medium | **Status:** 🟡 In Progress | **Found by:** round 71, driving PR #190 to green — two red `bst-tests` jobs on superseded heads | **Serves:** the contributor whose PR goes red on a job their diff cannot have touched | **Topic:** guards

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

## Outcome (round 71, 2026-08-31) — 🟡 the browser half is fixed

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

### What is not done

**The `chain_share` half.** Its Acceptance Test is twenty runs of a
real `bst build` against the cold fixture, and `bst` is not on this
machine. Nothing about it changed; the row stays open for it, and the
Motivation above is unedited.

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
