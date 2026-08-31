# UX-460: nothing says which findings the fixtures can actually produce

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 72, asked for tracing from the heuristics in `bga analyze` to the tests and examples that cover them | **Serves:** the round that adds a heuristic and has no way to tell whether anything exercises it | **Topic:** guards

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

_Not started._
