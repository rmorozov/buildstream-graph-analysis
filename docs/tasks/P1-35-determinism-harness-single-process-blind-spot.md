# P1-35: The determinism harness runs N times in one process, so it can't catch per-process nondeterminism

**Priority:** P1 | **Status:** 🟢 Done | **Depends on:** `P1-34` (the harness's blind spot is best demonstrated/regression-tested against that real bug)

## Spec Reference
Part 35 (Determinism Contract) / I11 - "the spec explicitly requires ≥100 canonical-output comparisons" (already the harness's own stated design point, `bga/validation/determinism.py:5-10`, `docs/tasks/P1-12-determinism-harness.md`).

## Background
Raised by an external review; independently verified against the current code before filing.

`run_determinism_check` (`bga/validation/determinism.py:47`) runs the full analysis pipeline `n` (default 100) times **within the same Python process** and compares canonical JSON output across those runs. This is a real, useful check for most sources of nondeterminism (dict iteration order, set iteration order, filesystem listing order, etc. - all of which can vary *within* a single process run to run). But Python's string-hash randomization seed (`PYTHONHASHSEED`) is fixed for the lifetime of one process - `hash(some_string)` returns the *same* value on every call within one process, only varying *between* separate process invocations. A bug like `P1-34`'s (`fifo` replay priority computed from `hash(str(task_key))`) is therefore **structurally invisible** to this harness no matter how large `n` is, since every one of the `n` in-process repeats would agree with each other while still being wrong relative to a different process's run.

Confirmed empirically: `python3 -c "print(hash('abc'))"` run twice as separate processes in this environment returns two different values, proving the randomization is real and active here.

## Required Fix
1. Add a second determinism-verification mode (or extend the existing harness) that runs the analysis pipeline in **genuinely separate Python processes** (e.g. `subprocess.run([sys.executable, "-m", "bga.cli", "analyze", ...])`, mirroring how `tests/test_golden.py` already invokes the CLI via subprocess for a different purpose) and compares canonical output across those separate invocations - this is the only way to catch hash-seed-dependent nondeterminism.
2. This doesn't need to run 100 separate process invocations by default (real, meaningful cost difference from in-process repeats) - a smaller N (e.g. 5-10) across separate processes, run as its own test tier, is enough to catch a real per-process-varying bug while keeping this affordable to run regularly; the existing single-process N≥100 check remains valuable for the nondeterminism sources it does cover and should stay as-is.
3. Once `P1-34` is fixed, this cross-process check should pass; before that fix, it should be the mechanism that actually proves the bug is real (and stays fixed) - sequence accordingly if both are worked in the same session.

## Out of Scope
- Don't replace the existing single-process harness - it's still the cheaper, faster check for the (larger) class of nondeterminism sources it does cover.
- Don't try to enumerate or explicitly test for every possible source of per-process nondeterminism (e.g. `id()`-based ordering, `frozenset`/`set` iteration seeded by hash randomization elsewhere) beyond what's needed to catch `P1-34`-shaped bugs - a real cross-process comparison inherently catches whatever the real behavior actually does, without needing to enumerate causes up front.

## Acceptance Test
1. Before `P1-34`'s fix: the new cross-process check fails (or would have failed, if written and run against the pre-fix code) on a fixture that exercises `priority_rule="fifo"` replay - a directly-verifiable, non-hypothetical regression test for `P1-34`.
2. After `P1-34`'s fix: the same cross-process check passes.
3. The new check is added to the normal test suite (gated behind whatever "slow" marker convention this repo already uses, matching `docs/tasks/P3-07-montecarlo-and-determinism-tests.md`'s "gate the golden/determinism/Monte-Carlo tests behind a slower marker" precedent) so it runs in CI without materially slowing down the default `make test`/`make lint` loop.
4. Full suite green.

## Verification Log
Added `run_cross_process_determinism_check` (`bga/validation/determinism.py`): each repeat is a genuinely separate `python -m bga.cli analyze -f json` subprocess (default n=5), sharing the existing comparison/diagnosis logic (`_compare_canonical_runs`) with the in-process check.

New tests (`tests/unit/test_determinism.py`, 2 new): the real (post-P1-34) pipeline is genuinely process-independent across 3 separate subprocess invocations; a direct demonstration of the mechanism itself via a monkeypatched `subprocess.run` that splices in a real `hash()`-derived field (the exact P1-34 bug shape) without needing to revert that fix, proving the harness would have caught it.

```
$ python3 -m pytest tests/unit/test_determinism.py -v
5 passed
$ python3 -m pytest -q   # full suite
401 passed, 11 skipped
$ make lint
All checks passed!
```
