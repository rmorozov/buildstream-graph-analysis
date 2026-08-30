# UX-439: the blast-radius ranking ties, and the tie-break is unstable

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 69, `bst-tests` red on PR #188 with a diff that touches no analysis code | **Serves:** anyone who reads "the first thing to fix" and expects the same answer twice | **Topic:** analysis

## Motivation

`bst-tests` failed on `984e4c5`:

```text
assert 'core.bst is the first thing to fix' in '...'
```

The run had printed `codegen.bst is the first thing to fix`. Two
clauses of `test_the_journey_has_an_answer_key.py` fail together —
`test_the_first_thing_to_fix_is_core` reading the payload, and
`test_the_terminal_says_it_too` reading the words.

**The ranking key ties exactly.** From a real capture of the same
project (`examples/06`, full rebuild, both planes):

```text
                downstream  weighted_duration_us  risk_score  own duration
core.bst                 8            15,500,000           8         10.0s
codegen.bst              8            15,500,000           0          3.0s
```

`blast_radius_ranked_by` is `measured-rebuild-time`, and that is the
tied value. The tie is **structural, not coincidental**: every
`lib-*.bst` declares a build dependency on both `core.bst` and
`codegen.bst`, so the two have the same downstream set and therefore
the same downstream weighted duration, on every run, forever. It is
the shape `examples/06` was deliberately built to have — `codegen.bst`
is the over-declared dependency that only `lib-f.bst` uses.

With the key tied, which one ranks first falls to whatever the sort
does with equal keys, and that is not stable across machines.

**The two published rankings already disagree on one machine.** In the
same `analyze.json`:

```text
top_blast_radius     ["toolchain.bst", "codegen.bst", "core.bst", ...]
optimization_horizon ["core.bst", "codegen.bst", "lib-a.bst"]
```

One puts `codegen.bst` ahead of `core.bst`; the other reverses them.
No diff can cause that — it is two orderings over the same tie, and it
is the clearest evidence that the tie-break is unspecified rather than
merely unlucky.

**Why it is not the PR that surfaced it.** The diff on that commit is
backlog files and an index row; the branch's other commits are docs, a
dev tool nothing imports, and tier lists. Both failing clauses pass on
that branch locally:

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_journey_has_an_answer_key.py \
    -k "first_thing_to_fix or terminal_says_it_too"
2 passed, 13 deselected in 46.33s
```

`bst-tests` was green on the base (`0952195`, job 99283114205), which is
one sample of a coin, not proof the coin has one face.

**`risk_score` is the discriminator the data already carries** — 8
against 0, and `core.bst` is on the critical path where `codegen.bst`
is not. Whether it should be the tie-break is a decision about what
the tool recommends, which is why this is a filing and not a quiet
patch.

## Required Fix

- **Decide the tie-break and write it down**, in
  `blast_radius_ranked_by`'s own vocabulary so the page can say which
  rule ordered the list. `risk_score`, then critical-path membership,
  then the element's own duration, then uid for determinism — a
  candidate, not a decision.
- **Make it total.** Whatever the rule, the last key is the uid, so two
  elements can never be ordered by chance.
- **One ranking, or a stated reason for two.** `top_blast_radius` and
  `optimization_horizon` disagreeing about the same pair is either a
  bug or a distinction nothing documents.
- **A guard that ties on purpose**: two elements with identical
  downstream sets, asserted to come out in a stated order every time.
  The current clauses assert `core.bst` and pass or fail on the coin.

## Out of Scope

- **Changing what blast radius measures**: `UX-171` and `UX-173`
  settled the metric and its published `ranked_by`, and this orders
  equals rather than re-defining the key.
- **The journey test's expectation**: `core.bst` is the right answer
  for that project and the test is not what is wrong here.
- **Any other tie in the tool** — `test_tie_break.py` exists and covers
  its own case; this item does not sweep for more, though a later one
  should.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
bga analyze @last --format json
```

`core.bst` ranks ahead of `codegen.bst` in both `top_blast_radius` and
`optimization_horizon`, and does so on repeated runs and on a second
machine. A mutation that removes the final uid key must redden the
guard.

## Outcome

_Not started._
