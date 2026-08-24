# UX-276: a guard can rest on a path no clone has

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-213 | **Serves:** the maintainers, and CI | **Topic:** guards

## Motivation

Found by CI on round 37's own pull request, which is the only reason it
was found at all: the full suite passed locally three times.

Round 37 shipped two guards whose whole value is that they
**recompute** pasted figures from a real run rather than comparing
against a stored expectation. Both were pointed at

```text
examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/
```

which `bga snapshot` had written on the machine that ran the build, and
which is ignored **by design**:

```text
$ cat examples/06-macro-micro-optimization/.bga/.gitignore
# Written by `bga snapshot` (UX-126). Captures are build
# artifacts: they are reproducible from the build and are
# large. Delete entries under runs/ whenever you like.
*

$ git ls-files examples/06-macro-micro-optimization/.bga | wc -l
0
```

CI failed on all four Python versions, before a single assertion ran:

```text
FAILED tests/unit/test_the_journey_reaches_what_if.py::…::test_the_run_the_guide_quotes_still_exists
FAILED tests/unit/test_the_builders_question_has_a_document.py::…::test_the_snapshot_the_chapter_quotes_exists
E   FileNotFoundError: [Errno 2] No such file or directory:
E   '…/examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/run/run_context.json'
==== 5 failed, 2236 passed, 15 skipped, 1148 deselected, 3 errors in 48.05s ====
```

This is `UX-213`'s defect — a guard that only guards one machine — in
the form its fix did not cover. `UX-213` made the *environment*
portable (node, browser, tier selection) and said nothing about the
**data**.

And the rule was already written down. Three test files over, in a
comment:

> `UX-213`: every guard an acceptance names runs on a run that is **in
> the repository**. The real capture stays as extra coverage where it
> exists, but it is never the only place a mutation would be caught.

Four guards follow it — `test_the_page_that_answers_why.py`,
`test_the_first_screen_is_a_decision.py`,
`test_one_click_from_investigation.py`,
`test_focused_graphs_not_a_dag_viewer.py` — each pairing
`GOLDEN = "tests/fixtures/…"` with `REAL = "examples/06/.bga/…"`. Two
guards written in one afternoon did not, and nothing measured the
difference. A convention four files keep and a fifth breaks is not a
convention, it is a habit.

## Required Fix

1. The two guards read a **committed** run.
2. The rule is mechanical: a test may not rest *only* on a path git
   does not track.
3. The exemption the four correct files rely on survives — an untracked
   capture beside a committed fixture is extra coverage and stays
   allowed.

## Out of Scope

- Committing capture archives generally. `UX-189` settled that and it
  is right; the fixture here is 72 KB against the snapshot's 712 KB.
- Making `bga snapshot` stop writing its `.gitignore`. The store is
  correct; the guard was wrong.

## Acceptance Test

Reverting either guard to the ignored path reddens the check, and the
four files that name that path deliberately stay green.

## Outcome — 🟢 Fixed & Verified

**The data moved into the repository.** `tests/fixtures/macro_micro/`
holds the three documents `bga`'s loader reads (11 KB, verbatim) and the
capture's Plane 2 report **without its `processes` array** — 813
per-process records, 458 KB of the original 584 KB. The whole fixture is
72 KB against the snapshot's 712 KB.

Dropping the process list changes nothing either guard reads, measured
rather than assumed:

```text
                full report          without `processes`
cores_busy      1.603977885512677    1.603977885512677
pinned          ['core.bst']         ['core.bst']
envelope @ 4    613.69921875 MB      613.69921875 MB
elements measured           9                      9
```

`peak_memory.per_element` carries the peaks the envelope sums and the
capacity summary reads aggregates; neither walks the process list. Every
figure the two guides paste is unchanged, which is the check that the
fixture reproduces the run rather than replacing it.
`tests/fixtures/macro_micro/README.md` records what was kept and what
was dropped, and says plainly that a guard needing per-process records
needs a different fixture.

**The rule is mechanical now** —
`tests/unit/test_a_guard_reads_only_what_a_clone_has.py`, 6 tests. It
sweeps every test file for repository path literals and flags a file
whose *only* data is a path that **exists here and git does not track**.

Three decisions in it are load-bearing:

- **"Exists here and untracked", not "untracked".** A path that exists
  nowhere cannot produce the green-here-red-there failure, and tests
  name plenty on purpose — asserting a module was *not* added, or
  naming a path they then create. The first draft flagged all of them:
  `bga/viewer/graph.js`, `tools/bst_`, `examples/01`.
- **The committed-fixture exemption.** The four files that pair `GOLDEN`
  with `REAL` are *right*, and a check that pushed them into deleting
  the extra coverage would make the suite worse.
  `test_the_files_that_use_a_real_capture_as_extra_coverage_are_allowed`
  asserts that exemption is still exercised, so it cannot quietly become
  a hole.
- **`__pycache__` is build output, not data.** Untracked and present on
  every machine that has run the suite once — a permanent false
  positive otherwise.

**The guard's own self-check caught a bug in the guard, on its first
run.** `TestTheCheckItselfDiscriminates` asserts the path extractor
actually finds a path it knows is there, and it failed:

```text
E   AssertionError: the extractor found no fixture path in a file that names one: []
E    +  where the compiled pattern put its alternation of roots outside the group
```

The alternation of directory roots was ungrouped, so the trailing
character class bound to the last root only and the pattern matched
almost nothing — the main check would have
passed on every file in the repository for a reason that has nothing to
do with what it claims. That is the non-discriminating guard, caught by
construction rather than by luck, and it is the argument for writing the
"does this check anything" test *first*.

Falsified, four mutations:

```text
M1  point the journey guard back at the ignored snapshot   -> no_test_rests_only_on_an_untracked_path
    (the exact literal CI failed on)                        + it_finds_the_paths_that_are_there
M2  point the builders guard back at it                    -> no_test_rests_only_on_an_untracked_path
M3  remove the committed fixture from a file that pairs    -> no_test_rests_only_on_an_untracked_path
    both (test_the_page_that_answers_why.py)
M4  point COMMITTED_DATA at a directory nothing uses       -> both checks, including the
                                                              exemption-is-exercised one
```

M1 is the acceptance test written as a mutation: the defect that reached
CI now reddens locally, in 0.3s, before a suite run.

**Deviation worth naming.** This item was filed and closed in the same
round, which the fixing guide normally treats as a smell. It is
deliberate here: the defect was found by CI on an open pull request for
that same round, and leaving the branch red to file a row first would
have been process for its own sake. The filing is written as the
round's post-mortem rather than as a plan.

### Verified where it failed, not where it passed

A local green is what shipped this defect, so the fix was checked in a
real clone — `git clone` of the branch into a fresh directory, which is
what `actions/checkout` gives CI:

```text
$ git clone --branch claude/build-optimization-audit-hk2xne . /tmp/realclone
$ [ -e /tmp/realclone/examples/06-…/.bga ] || echo "absent — as in CI"
absent — as in CI

$ cd /tmp/realclone && python -m pytest tests/ -q
3362 passed, 51 skipped in 420.81s (0:07:00)
```

The five tests CI failed on pass there. The 51 skips against the local
run's 3 are `UX-213`'s design working: the guards that use the real
capture as *extra* coverage stand down when it is absent, and each skip
carries its reason into `conftest`'s census.

**The clone run caught a second bug, in this guard.**
`test_the_files_that_use_a_real_capture_as_extra_coverage_are_allowed`
asserts the exemption is still exercised — and in a clone there is
nothing untracked to exempt, so it failed:

```text
FAILED …::test_the_files_that_use_a_real_capture_as_extra_coverage_are_allowed
E   assert []
```

That is the same defect one level up: a check that can only be
evaluated on a machine that has run the build. It now **skips with the
reason**, after first asserting that test files naming such a capture
still exist — so "we could not look" cannot decay into "we looked and
it was fine", and the exemption cannot quietly become dead code:

```text
SKIPPED [1] no local capture to exempt: 5 test file(s) name one and
           none is present in this checkout
```

Two rounds of this defect in one afternoon, in the fix for the defect
itself, is the argument for the check existing at all.
