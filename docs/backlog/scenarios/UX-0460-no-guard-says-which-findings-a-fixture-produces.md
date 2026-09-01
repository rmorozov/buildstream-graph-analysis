# UX-460: nothing says which findings the fixtures can actually produce

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 72, asked for tracing from the heuristics in `bga analyze` to the tests and examples that cover them | **Serves:** the round that adds a heuristic and has no way to tell whether anything exercises it | **Topic:** guards

## Motivation

`FINDING_READERS` is the registry of what `bga analyze` can conclude —
21 findings, each a heuristic with a reader. Nothing in the suite reads
that registry against the fixtures. So a finding can be added, wired,
documented and shipped while **no committed capture ever produces it**,
and the suite stays green because every test that touches it builds its
own synthetic payload.

Derived by running `analyze` over every committed capture in the tree
and collecting the ids:

```text
21 findings | 7 produced by no committed capture

  build-failed        cache-transfer-cost   certified-headroom
  criticality         execution-bound       failed-task-time
  shared-source-blast
```

Two of those seven are unreachable by construction — `build-failed` and
`failed-task-time` need a build that failed, and every committed
capture is of a build that succeeded. That is a fact worth *declaring*,
which is the difference between a gap and a decision.

**The instrument matters as much as the number.** A first cut of this
census also reported a "named by no test" column, built by scanning the
test sources for the quoted finding id. It claimed `efficiency-score`,
`optimization-horizon` and `certified-headroom` had no test at all; in
snake_case spellings they are in 7, 12 and 7 files. A text scan cannot
tell a name from a spelling of it — fixing guide §5, in the census
written to find §5 gaps. The guard this item asks for must read what
`analyze` **emits**, never what a source file says.

`UX-449` did the same thing for skip reasons and found 25 undeclared on
a green tree; `UX-376` established that a census names what it could
not assess. This is that pattern applied to the findings themselves.

## Required Fix

- **`tools/dev_finding_coverage.py`**: for every id in
  `FINDING_READERS`, which committed captures produce it, derived by
  running `analyze` — not by scanning sources.
- **A guard over it**: every finding is produced by at least one
  committed capture, **or** appears in a declared unreachable map with
  a reason, the way `tests/skip_reasons.py` declares skips. A finding
  that is neither is the failure.
- **The declaration is the deliverable.** "No capture can produce this
  because every capture is of a successful build" is a reviewed
  sentence; silence is not.

## Out of Scope

- **Whether each finding is *correct*** on the data it fires on: that
  is what the per-finding guards already do. This item asks only
  whether anything real reaches them.
- **Coverage of the viewer's rendering of a finding**: `UX-400`'s
  ledgers and the page guards hold that end.
- **Adding the missing captures**: `UX-459`. This item is the
  instrument and the guard; that one is the data.

## Acceptance Test

```bash
python3 tools/dev_finding_coverage.py
python3 -m pytest tests/unit/test_every_finding_reaches_a_fixture.py -q
```

The tool prints the finding-to-capture map; the guard is green, and
goes red when a capture is removed from the tree or a finding is added
to `FINDING_READERS` without either a capture or a declaration.

## Outcome

**Round 73 · 2026-09-01 · Status: 🟢 Done — the instrument was already here; the guard that freezes it was not**

### What existed and what did not

`tools/dev_finding_coverage.py` landed with `UX-464` and does what this
row asked of it — it reads what `analyze` **emits**, over `git
ls-files`-tracked captures, never over source text. What was missing is
the half that makes it a guard rather than a report:

```console
$ ls tests/unit/test_every_finding_reaches_a_fixture.py
ls: cannot access 'tests/unit/test_every_finding_reaches_a_fixture.py': No such file or directory
```

So the census was a number a round had to remember to look at.

### The guard

`tests/unit/test_every_finding_reaches_a_fixture.py`, seven clauses in
two classes:

```text
TestEveryFindingIsReachedOrDeclared
  the census covers the whole registry     - the population, asserted before it is read
  nothing is neither produced nor declared - the item's claim
  a declaration carries a reason           - >= 8 words, the shape tests/skip_reasons.py uses
  a declared finding is not also produced  - a declaration that has quietly become false
  the transfer finding has its own capture - names it, so removing that fixture says which
TestTheCensusReadsTheTreeAndNotTheMachine
  it counts what git tracks by default     - the correction the tool was born from
  the command in the task file runs        - the Acceptance Test, run as a subprocess
```

The fourth clause is the one this row would not have had without
writing it out. `UX-459` had proposed *declaring* `cache-transfer-cost`
unreachable; that declaration would have been false the moment a
capture reached it, and the census would have printed "declared
unreachable" over a finding seven fixtures produce. A declaration that
has gone stale is worse than none, because it asserts a capture cannot
exist while one does.

```console
$ PYTHONPATH=. python3 -m pytest tests/unit/test_every_finding_reaches_a_fixture.py -q
7 passed in 1.26s
```

### Every mutation, and that it went red

Each was applied and **proved to have landed** before the run.

```text
M1  the fixture reaching cache-transfer-cost untracked (git rm --cached)
    git ls-files tests/fixtures/a_build_that_pulls -> 0        3 failed, 4 passed
M2  a "ghost-finding" added to FINDING_READERS, no capture, no declaration
    grep -c ghost-finding bga/findings.py -> 1                 2 failed, 5 passed
M3  a declaration reduced to "n/a"
    grep -c '"failed-task-time": "n/a"' -> 1                   1 failed, 6 passed
M4  cache-transfer-cost declared unreachable although a capture produces it
    grep -c 'stale declaration' -> 1                           1 failed, 6 passed
restored                                                       7 passed
```

M1 reddening three clauses rather than one is the design: the count,
the named fixture and the CLI's own `0 neither` all rest on that
capture, and each says something different about what went.

### Tier

Measured rather than assumed — three single-process runs,
`--durations=0`, setup+call+teardown summed:

```text
1.09  1.22  1.14
```

Over `MEDIUM_FLOOR_S = 1.0` on every one, so it is listed in
`tests/tiers.py`'s `MEDIUM` with the measurement beside it. The cost is
the census itself: `analyze` in-process over all seven committed
captures, which is what the file is for.

### Deviation from the Required Fix

None. The tool clause was already satisfied by `UX-464`; that is
recorded above rather than re-implemented.

### Verification

```text
python3 tools/dev_finding_coverage.py     0 neither
make lint                                  clean
make test                                  5567 passed, 28 skipped in 303.15s
```
