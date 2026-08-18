# P1-29: CLI help text and docs claimed replay computes an "optimal" makespan

**Priority:** P1 (terminology/framing violation - low functional risk, but a direct spec-text contradiction shown to every user who reads `--help`) | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## Spec Reference
Part 1.2 Non-Goals: "`bga` does not claim to calculate: the mathematically optimal real scheduler." Part 18: "`T_C` is a deterministic feasible replay" (not "optimal"). Part 43's terminology avoid-list names "Mathematically optimal schedule" explicitly.

## How this was found
Same independent re-audit that found `P1-27`/`P1-28`. `P1-17`'s original terminology audit (task file, "zero matches, no code change needed") only grepped for Part 43's exact banned phrases; "optimal makespan" and "often optimal" don't literally match "mathematically optimal schedule" as a string, so that audit missed this semantically-equivalent overclaim.

## Current Broken Behavior (before this fix)
- `bga/cli.py:280` (`--replay`'s argparse help text): `'Run deterministic replay scheduler to compute optimal makespan (T_C)'`.
- `docs/guides/cli.md:49`: "Run the deterministic replay scheduler to compute the optimal makespan ($T_C$) under perfect scheduling:"
- `docs/guides/cli.md:54`: "`lpt` (Longest Processing Time first) - Default, often optimal."

All three directly contradict Part 1.2's own explicit non-goal and Part 18's "not used for primary attribution... does not prove the real BuildStream scheduler" framing - the exact claim the spec goes out of its way to disclaim, shown to every user who runs `bga analyze --help` or reads the CLI docs.

## What was fixed
Reworded all three to describe `T_C` accurately: a feasible makespan under the *chosen heuristic*, explicitly framed as a counterfactual model (Part 18: scheduler comparison, capacity sweep, model slack, what-if analysis) rather than a claim of scheduling optimality. `lpt`'s description now says "a common, reasonable heuristic, not guaranteed optimal" instead of "often optimal."

## Out of Scope
- Did not re-run a full terminology audit against every Part 43 banned phrase again - `P1-17`'s literal-phrase audit result stands; this fix addresses specifically the semantic gap that audit's methodology couldn't catch (paraphrase, not exact-phrase, matching).

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_cli_subcommands.py -v` (new regression test asserts the overclaiming phrase is gone from `--help` output).

## Verification Log
```
$ grep -n "optimal" bga/cli.py docs/guides/cli.md bga/report/*.py bga/replay/*.py
bga/cli.py:280: ...not a claim of scheduling optimality (Part 18)
docs/guides/cli.md:49: ...not a claim that $T_C$ is the mathematically optimal schedule:
docs/guides/cli.md:54: ...not guaranteed optimal.
# All 3 remaining mentions now explicitly disclaim optimality rather than claim it.

$ PYTHONPATH=. python3 -m pytest tests/unit/test_cli_subcommands.py -v
11 passed   # includes new test_replay_help_does_not_overclaim_optimality

$ PYTHONPATH=. python3 -m pytest tests/ -q
241 passed   # cumulative with P1-27/P1-28's regression tests

$ make check-clean
OK: no ignored files are tracked
```
