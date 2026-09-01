# UX-473: nothing in CI builds a generated project

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-465` stages 1-4, which shipped | **Found by:** round 72, closing `UX-465`'s first four stages | **Serves:** the round whose spec change breaks a build nobody runs until someone runs it by hand | **Topic:** guards

## Motivation

`UX-465` stage 5, split out so the item could close on what it did.
`tools/bga_gen_project.py` works and `tests/unit/test_a_generated_project_builds.py`
builds two generated projects where `bst` is present — but the census
that says what those builds *cover* runs nowhere:

```text
$ python3 tools/dev_finding_coverage.py
(a clone) 21 findings | 18 produced by a capture | 2 declared unreachable | 1 neither
```

Eighteen, because a generated capture is not committed (`UX-189`) and
so a clone cannot see it. The two findings `UX-465` reached —
`build-failed` and `failed-task-time` — are reachable by a command
nobody runs on a schedule, which is the same "true on one machine"
shape `UX-213` and `UX-459` are both about.

## Required Fix

`bst-examples` builds one generated project per CI run — it has `bst`,
`bwrap` and a builder already — and runs
`tools/dev_finding_coverage.py --local` over the capture, printing the
count. A drop in what a real build can produce then shows up in a job
log rather than in a round that happens to look.

Printing rather than asserting, at least at first: the census over a
generated capture has never run twice on the same runner, and a gate
whose bound nobody has measured is `UX-458`'s open question one axis
over.

## Out of Scope

- Committing a generated capture — `UX-189` settled that a clone does
  not ship one, and this item does not reopen it.
- Axis G at scale. A 1,202-element *real* build is a different budget
  question and `gen_synthetic_scale_run.py` covers the analysis side
  already.
- Turning the printed count into a gate — that needs the spread
  `UX-458` is waiting on, and is a row of its own when it exists.

## Acceptance Test

A `bst-examples` job log showing a generated project built and the
census's count for it, and a guard over `ci.yml` that the step is
there — `test_the_workflow_runs_what_it_says.py`'s shape.

## Outcome

**Round 73 · 2026-09-01 · Status: 🟢 Done — 21 of 21 findings, once a generated build is in the count**

### The gap, and the number that closes it

```console
$ python3 tools/dev_finding_coverage.py --quiet | tail -1
(a clone) 21 findings | 19 produced by a capture | 2 declared unreachable | 0 neither

$ python3 tools/bga_gen_project.py --spec tests/fixtures/specs/a-build-that-fails.json --out /tmp/fails
$ (cd /tmp/fails && bga snapshot -- bst build all.bst); echo "exit $?"
exit 255
$ python3 tools/dev_finding_coverage.py --quiet --also /tmp/fails/.bga/runs/*/run | tail -1
(a clone + 1 generated) 21 findings | 21 produced by a capture | 2 declared unreachable | 0 neither
```

`build-failed` and `failed-task-time` are the two, and they stay
*declared* unreachable because the claim the declaration makes is still
true — no **committed** capture produces them, and `UX-189` says a clone
ships none. What changed is that something reaches them on a schedule
rather than on a command somebody remembers.

### `--also`, and why the census needed it

The generated capture is outside the tree on purpose, so the tool's two
discovery globs (`examples/*/.bga/runs/*/run`, `tests/fixtures/*/run`)
cannot find it, and putting it where they could would be reopening
`UX-189`. `--also` takes a run directory and nothing else. It also
needed `label()` to stop assuming every run is under the repository —
`Path.relative_to` raises for anything outside it, and a census that
crashes on the run it was told about is worse than one that never had
it.

### The step

`bst-examples`, before the artifact upload, because that job already has
`bst`, `bwrap` and a builder. Three things in it are load-bearing and
each has a clause:

- `set -uo pipefail`, **not** `set -e`. The build is *meant* to fail —
  that is how it reaches `build-failed` — so `bga snapshot` exits 255
  and `set -e` would end the step before the census ran.
- the generator runs first, or the census prints the number a clone
  already prints;
- `--also` joins the two halves.

Printed rather than gated, per this row's own Out of Scope: the count
over a generated capture has never run twice on the same runner, and a
bound nobody has measured is `UX-458`'s open question one axis over.

### Every mutation, and that it went red

`tests/unit/test_ci_builds_a_generated_project.py`, ten clauses. A
guard that reads YAML can pass on a step that exists and does nothing,
so the clauses assert the pieces rather than the name. Each mutation was
applied and proved to have landed before the run.

```text
N1  the whole step removed              grep -c dev_finding_coverage -> 0   6 failed, 4 passed
N2  the generator invocation dropped    the census left standing            1 failed, 9 passed
N3  `set -e` restored                                                       1 failed, 9 passed
N4  `--also` dropped from the command   grep -c '--also' -> 0               2 failed, 8 passed
N5  `--also` stops adding the run       in dev_finding_coverage.captures     1 failed, 9 passed
restored                                                                   10 passed
```

N5 is the one worth having: N1–N4 all read the workflow, and a guard
made only of those is a guard over text. N5 mutates the *mechanism* the
step rests on, and the two clauses in
`TestTheCensusCanBeToldAboutARunOutsideTheTree` are what see it.

### Tier

Three single-process runs, setup+call+teardown summed: `0.32 / 0.33 /
0.33`. Under `MEDIUM_FLOOR_S = 1.0`, so it stays in the default (small)
tier and is listed nowhere — which is what `tests/tiers.py` means by
small.

### Deviation from the Required Fix

The Required Fix said the step should run `dev_finding_coverage.py
--local`. `--local` is the wrong flag: it counts untracked captures
under `examples/`, and this job writes its example runs to
`artifacts/`, not to `.bga/`. So `--local` would have found nothing and
printed a clone's number. `--also` is what the step actually needed and
is what was built; recorded here because the row's own instruction
would not have worked.

### A guard of my own that another gate already caught

The first version of this file opened with

```python
yaml = pytest.importorskip("yaml", reason="PyYAML is a dev dependency")
```

and `make test` reddened on
`test_no_test_module_collects_behind_an_importorskip` — `UX-197`'s
sixth seam, whose whole subject is that a module-scope `importorskip`
hides *every* guard in its file. Ten clauses would have vanished
silently on any runner without PyYAML. The sibling that already reads
this workflow, `test_the_candidate_reaches_a_log.py`, plainly
`import yaml`, and so does this one now. Recorded rather than quietly
fixed: it is the exact defect the seam exists for, walked into while
writing a guard.

### Verification

```text
python3 tools/dev_finding_coverage.py --also <generated run>   21 produced, 0 neither
make lint                                                       clean
make test                                                       5577 passed, 28 skipped in 300.57s
```

