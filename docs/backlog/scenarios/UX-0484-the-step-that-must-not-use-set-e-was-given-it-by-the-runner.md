# UX-484: the step that must not use `set -e` was given it by the runner, and its guard read the wrong half

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 73, five consecutive red `bst-examples` runs on PR #191 | **Serves:** the round that trusts a green suite and a guard that reads the workflow, and ships a CI step that has never once reached its own last line | **Topic:** guards

## Motivation

`UX-473` added the `bst-examples` step that generates a failing
project, captures it, and runs the finding census over the capture
with `--also`. It has failed on **every run since it landed** — five
in a row on PR #191 alone (`a0aeb54`, `84eb4cf`, `e1c6393`, `4ca1517`,
`75be32b`), always the same way:

```text
{"out": "artifacts/generated-a-build-that-fails/project", "name": "a-build-that-fails", "elements": 7}
##[error]Process completed with exit code 255.
```

The step prints the generator's line and stops. Neither the `echo`
after the snapshot, nor the `test -d`, nor the census ever runs.

The step body opens with `set -uo pipefail`, deliberately and with a
comment saying why: the build is *meant* to fail, so `bga snapshot`
exits non-zero and the step must not obey that status. What the body
cannot do is take `-e` **off**, because GitHub Actions does not start
the body with a bare shell:

```text
shell: /usr/bin/bash -e {0}
```

That is the runner's default for `run:`. `set -uo pipefail` sets three
options and clears none, so `-e` was live for every one of those five
runs and the deliberately failing command ended the step on its own
exit status — the exact failure the comment above it says it is
avoiding.

## The guard that should have caught it

`tests/unit/test_ci_builds_a_generated_project.py::test_a_failing_build_does_not_fail_the_step_on_its_exit_status`
reads the step's `run:` block and asserts:

```python
assert "set -euo pipefail" not in run
assert "set -uo pipefail" in run
```

It is a text scan for the *spelling of a line in the body*, standing
in for the question "does a non-zero exit end this step". Those are
different questions, and the runner's `shell:` default is the whole
distance between them. Fixing guide §5, in a guard written to hold a
§5 property — and it passed on every one of the five red runs.

`UX-473`'s Outcome records a mutation, `N3 set -e restored`, that
reddened it. That mutation edited the body, which is the half the
guard reads; the half that actually decided was never touched.

## Required Fix

- **The step stops depending on which options the shell was started
  with.** Capture the status instead of hoping it is ignored:
  `... || status=$?`, then echo `$status`. A command whose failure is
  handled is not a failing command under `-e`, so the step is correct
  under either shell.
- **The guard reads the mechanism.** It must fail when the snapshot's
  exit status is left unhandled, whatever `set` lines the body carries
  — and the mutation that proves it is deleting the `|| status=$?`,
  not restoring `set -e`.
- **Annotate `UX-473`** (fixing guide §3.6): its Outcome claims a step
  that runs the census in CI, and no run of it ever has.

## Out of Scope

- **The census's own contents** — the counts are measured locally in
  this round and are not what failed here, since the step never
  reached the command that prints them.
- **Making the census a gate.** `UX-473`'s Out of Scope argued for
  printing rather than gating until there is a spread to size a bound
  from, and that argument is untouched.
- **The other `bst-examples` steps**, which use `set -euo pipefail`
  correctly: their commands are meant to succeed, so `-e` is right for
  them.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_ci_builds_a_generated_project.py -q
```

green, with the `|| status=$?` deleted reddening it — and the
`bst-examples` job on the next push reaching
`(a clone + 1 generated) N findings | ...` in its log.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

Five consecutive `bst-examples` failures on PR #191 — `a0aeb54`,
`84eb4cf`, `e1c6393`, `4ca1517`, `75be32b` — every one the same:

```text
2026-09-01T15:01:32Z  {"out": "artifacts/generated-a-build-that-fails/project",
                       "name": "a-build-that-fails", "elements": 7}
2026-09-01T15:01:37Z  ##[error]Process completed with exit code 255.
```

Five seconds, and the generator's line is the whole output. The
`echo`, the `test -d` and the census never ran, so `UX-473`'s claim
that CI builds a generated project and counts it has been supported by
**no run at all**.

The runner's own preamble says why:

```text
shell: /usr/bin/bash -e {0}
```

`set -uo pipefail` in the body sets `-u`, `-o pipefail` and clears
nothing. `-e` was live, and the deliberately failing `bga snapshot`
ended the step on its exit status — the exact failure the comment
above it says it is avoiding.

### After

```yaml
status=0
(cd "$OUT/project" && bga snapshot -- bst build all.bst) \
  > "$OUT/snapshot.txt" 2>&1 || status=$?
echo "bga snapshot exited $status (the build is meant to fail)"
```

A command whose failure is handled is not a failing command under
`-e`, so the step is correct whichever shell the runner gives it —
which is the property to want, since the body cannot see that choice.

### The guard read the wrong half

```python
assert "set -euo pipefail" not in run
assert "set -uo pipefail" in run
```

A text scan for the spelling of a line in the body, standing in for
"does a non-zero exit end this step". Measured against the shipped
defect — the workflow as it actually ran for five reds:

```text
the OLD guard's two assertions, against the shipped defect:
  'set -euo pipefail' not in run -> True
  'set -uo pipefail' in run      -> True
```

Both hold. The guard could not have caught it, and `UX-473`'s N3
mutation (`set -e` restored) reddened it by editing the half that
never decided anything.

The clause now asserts the mechanism: the snapshot's status is
captured, and the captured status is printed so a reader can tell a
failing build from a broken step. The `set` line stays asserted as a
second belt rather than as the claim.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| R1 | the `or`-handler `&#124;&#124; status=$?` deleted — the shipped defect, exactly | 1 of 10, and the old clause passed under it (measured above) |
| R2 | `set -uo pipefail` → `set -euo pipefail` in the body | 1 of 10 — the second belt still speaks |

### Deviation from the Required Fix

None. All three clauses done, including the `UX-473` annotation, which
is written as a block quote inside the sentence it falsifies rather
than appended at the end, so a reader of that claim meets the
correction with it.

### What is still unproven

**That the step now works.** Everything above is measured locally and
from the failed logs; the only thing that can show the census running
in CI is a green `bst-examples` with
`(a clone + 1 generated) N findings | ...` in its log, and that is one
push away rather than in hand. The row closes on the fix and its
guard; the log line is the next run's to produce, and if it does not,
this row reopens rather than a new one being filed.

### The runs

```text
python3 -m pytest tests/unit/test_ci_builds_a_generated_project.py
                                              10 passed in 1.53s
make test                                     5626 passed, 27 skipped, 1 warning
                                              in 322.78s (0:05:22)
make lint                                     All checks passed!
```
