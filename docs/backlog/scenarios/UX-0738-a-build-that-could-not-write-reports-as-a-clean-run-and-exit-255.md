# UX-738: a build that could not write reports as a clean run and exit 255

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-156 (a failed build must not verdict as if it finished), UX-324, UX-148 | **Serves:** anyone whose disk fills mid-capture, and the round that then reads the report | **Topic:** capture | **Shape:** judgement | **Area:** tools

## Motivation

Round 100's gate went red with eighteen fixture errors in
`tests/unit/test_the_journey_has_an_answer_key.py`. The assertion
prints `stdout[-4000:] + stderr[-4000:]`, and what it printed was a
**complete, normal-looking analysis**:

```text
Attribution Breakdown:
  Execution On Chain            0.00s (  0.0%)
  Dependency Wait               0.00s (  0.0%)
  Idle                          8.95s ( 76.5%)
  Untracked Head                2.58s ( 22.0%)
Critical Path Length: 4 elements
  Path: toolchain.bst → core.bst → app.bst → all.bst
...
This snapshot: 167.6K. …/.bga/runs: 167.6K over 1 snapshot(s).

assert 255 == 0
```

Nothing in four thousand characters of either stream says what went
wrong. The only signal is the exit code, and the report beside it
reads as a build that ran and was simply idle — the one shape
`UX-156` exists to stop.

The cause, found by elimination and then confirmed:

```console
$ du -sh /tmp/pytest-of-root
4.4G    /tmp/pytest-of-root
$ rm -rf /tmp/pytest-of-root/*
$ pytest tests/unit/test_the_journey_has_an_answer_key.py -q
25 passed in 42.11s
```

The build could not write. Two things about the diagnosis are the
finding, not the anecdote:

- It reproduced **identically at a commit whose `make test` was fully
  green an hour earlier**, which is what ruled the round's own diff
  out. Nothing in the tool said so; that took a checkout and a re-run.
- `df` reported 13 G available throughout. Whatever ran out, it was
  not the figure a human or a guard would check first, so "check the
  disk" is not the lesson — "say which write failed" is.

`UX-156` made a *failed* build refuse to verdict. This is the same
class one layer down: a build whose sandbox could not write produces
a report of a build that did nothing, and the tool passes the exit
code up without a sentence.

## Required Fix

`bga snapshot` must say why it is exiting non-zero, in the stream the
reader is already looking at. At minimum, when the wrapped command
exits non-zero:

- the last line of output names the wrapped command's exit code and
  that the analysis below describes a build that **did not complete**;
- an analysis with zero execution on the chain and a non-zero wrapped
  exit is refused rather than printed as a verdict, the way `UX-156`
  refuses one for a failed element;
- where the failure is a write, the path that could not be written is
  named. `bst`'s own diagnostics carry it; the wrapper discards it.

**The decision, taken here: 255 survives, unmapped.**
`docs/guides/cli.md:194` already states the contract — *`bga snapshot`
exits with the wrapped build's own exit code* — and 255 is `bst`'s,
not a code `bga` invented. Mapping it would break the one property a
CI job depends on (the wrapped build's code reaches the caller) to
compensate for a missing sentence, which is the wrong layer. The
defect is that nothing in either stream says why; the number is
correct and is not the finding.

What the exit-code table does owe the reader is that this
pass-through exists at all, so the fix states it where a reader
meets the codes rather than only at line 194.

## Out of Scope

- The container's disk allowance. That is an environment fact; this
  row is about the tool's silence, which would be the same on any
  machine that filled up.
- The journey guard's own fixture. It reported the failure correctly
  as far as it could see — the four-thousand-character window was
  full of report because the report is what the tool produced.

## Acceptance Test

A capture whose sandbox cannot write exits non-zero **and** the last
line of its output says the build did not complete, naming the wrapped
exit code; no attribution verdict is printed for it. Mutation: make
the wrapped command exit non-zero after producing a partial trace —
the clause reds if a verdict is printed anyway.

## Outcome

**Gap measured:** `bga snapshot`'s only signal for a write failure was
the numeric exit code; neither stream said why, and a run with zero
execution measured on the chain and a non-zero exit printed a full
Attribution Breakdown as if it had run and been idle (round 100's
`assert 255 == 0` reproduction).

**Close measured:** `main()` now prints one line, last, whenever
`build_exit != 0`: `bst exited N - the analysis above describes a
build that did not complete.`, plus `Could not write PATH.` when the
wrapped log's tail carries an OS-level write error (Python's own
`[Errno N] <strerror>: 'path'` rendering). `_analyze()` refuses the
printed verdict, in `UX-156`'s own "THIS BUILD DID NOT FINISH"
wording, exactly when `build_exit` is non-zero **and**
`execution_on_chain_us` is zero; a fully-cached, exit-0 build with the
same zero execution still prints — both proven by one guard's two
assertions. Simulated the failing write via a fixture wrapped log
carrying a synthetic `OSError` line rather than filling this
container's disk: faithful because `bst_run_wrapped.emit` writes
`bst`'s real stdout/stderr verbatim into that same log, and Python's
`OSError.__str__` is the interpreter's own rendering, not invented.

**Mutation table:**

| clause | mutation | reddened | result |
|---|---|---|---|
| 1: exit line | deleted the trailing `if build_exit: print(_exit_summary_line(...))` block | `TestAnExitThatSaysWhy::test_the_last_line_names_the_exit_code_and_incompletion` | 1 failed, 1 passed |
| 2: refuse not print | `if build_exit and not executed_us:` → `if not executed_us:` | `TestZeroExecutionRefusesAVerdict::test_a_cached_build_with_zero_execution_still_prints` | 1 failed, 1 passed |
| 3: name the path | `named = f" Could not write {where}." if where else ""` → `named = ""` | `test_a_write_failure_names_the_path_from_the_wrapped_log` | 1 failed, 32 passed elsewhere |

`tests/unit/test_snapshot.py -q`: 33 passed, 1 skipped (clean, no
mutation). `make lint`: clean. `make test-touching`: 1422 passed, 30
skipped. `tests/unit/test_the_journey_has_an_answer_key.py`: 25
skipped (no `bst`/`bwrap`/staged toolchain in this container — the
same environment gate it always had, not a regression).
