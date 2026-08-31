# UX-456: two bst-gated guards fail on the runner and not on the diff

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 71, driving PR #190 to green — two red `bst-tests` jobs on superseded heads | **Serves:** the contributor whose PR goes red on a job their diff cannot have touched | **Topic:** guards

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

## Outcome

_Not started._
