# UX-480: the bst-tier pin is written twice and the guard read the half that does not decide

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 72, PR #191 — `bst-tests` failed on a run where all 45 bst-gated tests passed | **Serves:** the contributor whose PR is red on a job that has just reported everything green | **Topic:** guards

## Motivation

`ci.yml`'s `bst-tests` job pins how many `bst`-marked tests must run, so
a silently absent `bst` cannot skip the tier and read as a pass. That
pin is written in **two** places in the same step:

```yaml
          grep -qE "(^|[[:space:]=])43 passed([[:space:],]|$)" /tmp/bst-tier.txt || {
            echo "Expected exactly 45 bst-gated tests to run. Got:" >&2
```

The `grep` is what fails the step. The `echo` is what a reader sees.
`UX-465` raised the tier from 43 to 45, edited the `echo`, and missed
the `grep` — and CI stayed green on that commit and the next, because
the tier only runs when `test (3.11)` passes and `test (3.11)` was red
on both. The first run where the whole gate actually reached the tier
was `0edcdc1`:

```text
tests/unit/test_a_generated_project_builds.py::TestBstAcceptsWhatItWrites::test_the_acceptance_spec_builds PASSED
tests/unit/test_a_generated_project_builds.py::TestBstAcceptsWhatItWrites::test_the_failing_spec_really_fails PASSED
...
=============== 45 passed, 5543 deselected in 119.90s (0:01:59) ================

Expected exactly 45 bst-gated tests to run. Got:
=============== 45 passed, 5543 deselected in 119.90s (0:01:59) ================
##[error]Process completed with exit code 1.
```

Forty-five ran, forty-five passed, and the job says it expected exactly
forty-five and did not get it. The message and the assertion disagree,
so the failure *cannot be read* from the output.

The guard that exists to stop this —
`test_the_pinned_bst_tier_count_matches_the_number_of_marked_tests`,
written for `UX-91` on exactly this class of defect ("stop writing the
number down anywhere a check cannot reach") — was **green throughout**:

```python
    pinned = re.search(r"Expected exactly (\d+) bst-gated tests to run", workflow)
```

It read the `echo`. The `echo` was correct. This is fixing guide §5 in
the guard itself: an instrument reading a proxy — the human-readable
message — for the thing it names, which is the assertion.

## Required Fix

- **Correct the `grep` to 45**, which is what collects.
- **Make the guard read the `grep`**, and read it *against* the `echo`
  as well as against the collected count, so the two copies cannot
  drift apart again in either direction.
- **Fail loudly if the `grep` is gone.** A guard that regex-matches a
  workflow line silently stops guarding when the line is rewritten;
  absent means red, not skipped.

## Out of Scope

- **Collapsing the pin to one copy** — an env var read by both, say.
  It would be better and it is a workflow refactor rather than a fix
  for a red build; the guard now makes the duplication safe, which is
  the smaller change with the same effect. Filed as nothing, because
  the duplication is no longer a hazard once both halves are read.
- **The `bst-smoke` and `bst-examples` jobs**, which pin nothing of
  this shape — they assert on the exit status of scripts, not on a
  count.
- **Whether 45 is the right number** — it is what `pytest -m bst
  --collect-only` reports, and the guard asserts the pin against that
  rather than against a figure anybody typed. Which tests should carry
  the marker at all is a different question and not this row's.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_docs_links_and_commands.py -q \
    -k bst_tier
```

green, and red under each of: the `grep` number changed alone, both
numbers changed together to one that does not collect, and the `grep`
removed.

## Outcome

**Round 72 · 2026-09-01 · Status: 🟢 Done**

### The gap, measured

Run `33497620898`, job `bst-tests` at `0edcdc1` — pasted in the
Motivation above: `45 passed`, and `exit code 1`. `git log -S` on the
two literals says when they parted:

```console
$ git log --oneline -1 -S'Expected exactly 45 bst-gated' -- .github/workflows/ci.yml
d334d60 UX-465: a BuildStream project bst builds, from a topology spec
$ git show d334d60 -- .github/workflows/ci.yml \
    | grep -E '^[-+].*(Expected exactly|passed|bst-gated tests ran)'
-            echo "Expected exactly 43 bst-gated tests to run. Got:" >&2
+            echo "Expected exactly 45 bst-gated tests to run. Got:" >&2
-          echo "43 bst-gated tests ran, none skipped."
+          echo "45 bst-gated tests ran, none skipped."
```

**Both `echo`s changed and the `grep` did not.** The number appears
three times in that step and the one that decides is the one nobody
edited — which is also the one the guard did not read. Nothing caught
it for two commits.

### The fix, and that it discriminates

The `grep` now says 45, and the guard reads it:

```python
    asserted = re.search(r"grep -qE \"\(\^\|\[\[:space:\]=\]\)(\d+) passed",
                         workflow)
    assert asserted, (...)
    assert int(asserted.group(1)) == int(said.group(1)), (...)
    assert int(asserted.group(1)) == marked, (...)
```

```console
$ PYTHONPATH=. python3 -m pytest tests/unit/test_docs_links_and_commands.py -q -k bst_tier
1 passed, 38 deselected in 2.49s
```

Three mutations, each applied and **proved to have landed** before the
run — the process failure this round already recorded once was a
mutation reported green without that proof:

```text
M1  the exact defect that shipped: grep 43, echo 45
    grep -c '=\])43 passed' ci.yml -> 1        1 failed
M2  both copies moved together to 46, which does not collect
    grep -c '46' ci.yml -> 3                   1 failed
M3  the grep replaced by `true`, echo left alone
    "M3 landed; grep line now: ['true || {']"  1 failed
        AssertionError: the bst-tests job no longer greps for `N passed`
restored                                       1 passed
```

M3's first attempt was a `sed` whose expression was rejected
(`unknown option to 's'`) and the guard passed — a mutation that never
landed, reported as a green. Re-run through Python with the landing
asserted, it reddens. Recorded because that is the second time this
shape has appeared in one round.

### Deviation from the Required Fix

None.

### Verification

```text
make lint                  clean (ruff + PyMarkdown)
dev_close_task.py --check  0 problem(s) over 3 properties, 478 backlog rows
make test                  5560 passed, 28 skipped, 1 warning in 317.34s (0:05:17)
```

One run in between was red on
`test_the_handoff_box_is_measured_served.py::...[390-844]`, a Chrome
geometry clause this branch does not touch
(`git log origin/main..HEAD -- that file and bga/viewer/` is empty).
It passes alone — `16 passed in 30.12s` — and passed on the run above
and on the two full runs before it. Recorded rather than re-run
silently: it is the contended-Chrome shape `UX-456` part one is about,
and this is a fourth sighting of it.
