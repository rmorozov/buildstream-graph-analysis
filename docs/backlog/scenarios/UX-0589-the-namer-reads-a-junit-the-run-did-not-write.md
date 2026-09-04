# UX-589: the failure namer reads a junit the run did not write

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-554 (the namer), UX-558 (its position), UX-588 (which met it) | **Found by:** round 83, chasing two tests that had not failed | **Serves:** every session reading a red CI job | **Topic:** guards

## Motivation

`tools/dev_junit_tail.py` names the failing tests so a log-tail reader
does not have to scroll. Round 83 filed this claim: when the suite
dies at **collection** no junit is written, and the namer then reads
whatever junit an earlier step of the same job left on disk, naming
*its* failures as this run's.

What that round measured, on run 33751159258, `test (3.9)`, where the
real failure was four collection errors from `UX-588`:

```text
the junit could not be read ([Errno 2] No such file or directory:
'/home/runner/work/_temp/junit.xml'); the suite's own output above is
all there is
```

— is the *correct* refusal, and it was read as the exception. The run
before it, 33750369347, printed:

```text
2 test(s) failed, named here because the log tail above may be truncated (UX-554):
  FAILURE tests.unit.test_the_rail_takes_a_step...test_next_walks_the_order_the_page_declares
  FAILURE tests.unit.test_the_rail_takes_a_step...test_previous_walks_back
```

**The premise is false, and this file said so for a round.** Round 84
read run 33750369347's own `Test` step, four lines above the namer:

```text
  -     '#headline',
        '#findings',
  +     '#overview',
    ]
=========== 2 failed, 6233 passed, 164 skipped in 323.28s (0:05:23) ============
make: *** [Makefile:51: test] Error 1
```

The junit was that step's own — uploaded from it, 146,873 bytes, at
11:42:05, and read at 11:42:06 — and the two names were true.
`UX-592` found why they fail only sometimes: the rail's walk began
before the page marked `data-current`, 2 red in 19 runs under load.

Nor is there a mechanism for the hazard as filed. `runs-on:
ubuntu-latest` gives each job a fresh `runner.temp`; exactly one step
per job writes that path (the three `--junitxml` steps are mutually
exclusive on `matrix.python-version`); `make test` runs pytest once;
no pytest config sets a default `junitxml`; nothing downloads an
artifact into it.

What round 83 actually paid four measurements for is that the names
are **unfalsifiable to their reader**. The namer prints ids and
nothing else, so a reader who doubts them — rightly, since they had
not reproduced locally — has no cheap way to check whose junit they
came from. That is the gap this item closes.

## Required Fix

The namer's output carries the evidence a reader needs to place it:
the junit's own recorded totals and its age, on every path including
the one where it records no failure. A reader must be able to match
the report against the suite's summary line above it without leaving
the log.

Not a refusal gate on mtime, as this file first asked: no step of this
workflow can produce a junit the run did not write, so a threshold
would be a constant invented to guard nothing.

## Out of Scope

`UX-588`'s floor guard, which is what exposed this. The naming step's
position in the workflow (`UX-558`) is right and is not touched.
Deleting the junit before the suite runs — declined: it defends a
mechanism measured not to exist, and would cost a step to say so.

## Acceptance Test

A junit aged three hours, and the namer saying so on its own output line — beside a junit written now, which must read differently.

## Outcome

**Round 84**, 2026-09-03. Closed by refuting its own Motivation and
keeping the cost the round underneath it actually paid.

### The gap, measured

The filed mechanism does not exist. Run 33750369347's `Test` step
printed its own summary four lines above the namer's output:

```text
=========== 2 failed, 6233 passed, 164 skipped in 323.28s (0:05:23) ============
make: *** [Makefile:51: test] Error 1
```

then uploaded 146,873 bytes of junit at `11:42:05`, and the namer read
that file at `11:42:06`. The `- '#headline'` / `+ '#overview'` diff in
the same step is `test_next_walks_the_order_the_page_declares`'s own
assertion. `UX-592` closed the race that produced it.

Nor can a stale junit reach that path. Enumerated:

```text
$ grep -c "runs-on: ubuntu-latest" .github/workflows/ci.yml     # ephemeral runner.temp
10
$ grep -n "junitxml" .github/workflows/ci.yml                   # three, mutually exclusive on matrix
68:  run: make test PYTEST_ARGS="--junitxml=${{ runner.temp }}/junit.xml"
84:    --junitxml=${{ runner.temp }}/junit.xml"
88:  run: make test PYTEST_ARGS="--junitxml=${{ runner.temp }}/junit.xml"
$ grep -n "pytest" Makefile | grep -c "^51:"                    # make test runs it once
1
$ grep -rn junit setup.cfg pytest.ini pyproject.toml            # no default path
(none)
```

The real gap: the names are unfalsifiable to their reader. Before —
nothing on these lines can be checked against anything:

```text
2 test(s) failed, named here because the log tail above may be truncated (UX-554):
  FAILURE tests.unit.test_b::test_red
```

### The close, measured

```text
$ python3 tools/dev_junit_tail.py <a junit from a 6-test run>
the junit records no failure - the suite failed elsewhere (collection, a plugin, or the make target itself)
  read from .../j.xml: 6 test(s) recorded, 0 failure(s), 0 error(s), written 0s
  before this read - match that against the suite's own summary line above
```

`6 test(s) recorded` against pytest's `6 passed`. On run 33750369347
that line would have read `6399 test(s) recorded, 2 failure(s)`
against `2 failed, 6233 passed, 164 skipped` — and the round would
have stopped there instead of spending four measurements.

### Mutations

| mutation | result |
|---|---|
| `totals()` counts 0 for every key | 2 red |
| `_age` always the seconds branch | 1 red |
| `_age` never the seconds branch | 1 red |
| provenance printed only when something failed | 1 red |
| mtime read as `0.0` age | 1 red |

Five applied, five red, 10 passed restored.

### Deviation from the Required Fix

**One, and the Required Fix was rewritten to record it.** No mtime
refusal gate: the enumeration above measures the hazard out of
existence, so a threshold would be a constant guarding nothing. The
age is *reported* instead — no invented number, and it still says
"this junit predates the run" if one ever does.

### Tier and suite

Unlisted in `tests/tiers.py`, so small; 10 tests in 0.53s.
