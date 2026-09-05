# UX-720: the browser tier is guarded by nobody but a full local run

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-359 (the page fixture the geometry guards measure), UX-495 (the browser family's CI spread), UX-718 (the census's own class) | **Serves:** R8, who is told a page is within budget by a gate that never opened it | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

CI's `test` job installs no browser:

```text
$ grep -in chrom .github/workflows/ci.yml   # inside job `test` (lines 18-336)
(no output - no chromium step, no playwright install)
$ grep -c "@needs_browser" tests/unit/*.py | awk -F: '{s+=$2} END {print s}'
73        over 34 files
```

So every `@needs_browser` clause **skips** in CI. The page's volume
budgets, its drawing grades, its geometry - the whole tier `UX-359`
built so guards measure the page a user gets - is enforced by one
thing: somebody running `make test` locally on a machine with Chromium.

Measured this round. `UX-681` shipped, `make test-touching` was green,
CI was green on the four Python jobs, and a full local run found three
red:

```text
test_a_drawing_is_graded    the declared strips are 5, the clause said 4
test_the_page_has_a_volume_budget  landed 7,018 px against 7,000
                                   opened 34,678 px against 34,000
```

Two gates said yes and the page had grown past a bound it states in
`docs/design/styleguide.md`. `UX-495` already measured this family's CI
spread, so the cost of running it is known; what is not decided is
whether a page budget is a claim CI makes.

## Required Fix

Decide, and make the decision visible either way.

- **If the tier belongs in CI**: install Chromium in the `test` job (or
  a `browser` job of its own, if `UX-495`'s spread says the matrix
  cannot carry it), and a guard asserts the workflow does it - the
  `UX-354` rule, that a workflow nothing reads is a workflow that
  drifts.
- **If it does not**: `tests/browser.py` says so where the skip is
  raised, naming what a green CI therefore does *not* mean, and
  `make test-touching`'s own contract says the same - because a
  contributor reading two green gates is entitled to know which
  claims neither of them made.

## Out of Scope

- The three budgets `UX-681` restated - already measured and argued
  in place.
- Adding browser guards. This is about who runs the ones there are.

## Acceptance Test

A guard reads `.github/workflows/ci.yml` and holds it against the
decision: either the job that installs a browser exists and the guard
names it, or `tests/browser.py`'s skip reason names the gap and the
guard holds that sentence. Mutation: remove the browser step (or the
sentence) - the guard reds naming which.
