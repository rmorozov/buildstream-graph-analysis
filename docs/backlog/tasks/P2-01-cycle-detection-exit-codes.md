# P2-01: No cycle detection; exit code 3 never produced

**Priority:** P2 | **Status:** 🟢 Fixed & Verified — was actually already implemented; this task's original diagnosis was stale (2026-08-13) | **Depends on:** none

## Correction: this was already fixed before this task file was ever written
Re-verifying before starting work (per `docs/contributing/fixing-guide.md`'s mandatory rule) found that `bga/graph/edg.py::compute_unweighted_depth` and `compute_weighted_depth` **already** raise `ValueError("Graph contains a cycle involving elements: ...")` when Kahn's-algorithm-based topological processing doesn't reach every node, and `bga/cli.py::cmd_analyze` **already** catches this specific `ValueError`, checks for `'cycle'` in the message, and returns exit code `3` — all landed in commit `ad8a2db` (the same P0-fixing commit this whole tracker was originally built from). The very first version of this task file mis-diagnosed this as unstarted without independently re-running the reproduction — exactly the failure mode the fixing-guide's verification rule exists to prevent, now caught on the fixing side too, not just on prior "Fixed" claims.

Confirmed empirically (not just by reading code) with a genuine two-element cycle fixture: `python3 -m bga.cli analyze <cyclic-fixture>` prints "Error: Graph contains a cycle - Graph contains a cycle involving elements: a.bst, b.bst" and exits `3`; a non-cyclic fixture exits `0`. See `tests/unit/test_cli_exit_codes.py` (new) for a permanent regression test.

No code changes were needed for this task specifically - see `P2-02`'s task file for two small, related gaps found in the same investigation (missing-file exit code, `load_graph`'s JSON error wrapping) that were real and got fixed.

## Spec Reference
This is a "just works" issue, not a spec-nuance one, but it's also documented behavior: `sed -n '1,136p' docs/guides/cli.md` — find the exit-code table (documents `0` success, `1` bad args/missing files, `2` ingestion failure, `3` analysis failure e.g. graph cycles).

## Current Broken Behavior
- No code anywhere checks the dependency graph for cycles before running topological-sort-based algorithms.
- `bga/graph/edg.py::compute_unweighted_depth` (and likely the weighted variant) — the "handle any remaining elements" fallback (around line 108-112) just defaults unreached nodes (which, in a cyclic graph, means nodes stuck in the cycle and never dequeued by Kahn's algorithm) to depth 0, rather than detecting and reporting the cycle.
- `bga/cli.py:246-252` — a single broad `except Exception` maps every runtime failure (ingestion or analysis) to the same exit code. Exit code 3 is never produced anywhere in the code, despite being documented.

## Required Fix
1. Add explicit cycle detection: in the Kahn's-algorithm-based traversal (wherever `compute_unweighted_depth`/`compute_weighted_depth`/similar topological sorts run), if any nodes remain un-dequeued after the queue empties, that's a cycle — collect those node UIDs.
2. Raise a typed exception (see `P2-03`'s exception hierarchy if that task has landed yet; otherwise a plain `ValueError`/`RuntimeError` subclass is fine as a placeholder, but prefer coordinating with whichever task lands the exception hierarchy first — check the tracker) carrying the offending cycle's node list in the message.
3. In `bga/cli.py`, catch this specific exception type and exit with code `3`, distinct from ingestion failures (which should map to code `2`) and bad-args failures (code `1`, likely already handled by argparse itself).
4. Do not let the analysis silently proceed with a partially-wrong result (depth 0 for cyclic nodes) — fail loudly and specifically.

## Out of Scope
- Don't build the full custom exception hierarchy here if `P2-03`'s logging task also wants to own that — coordinate via the tracker; if `P2-03` isn't done yet, add a minimal `class GraphCycleError(Exception)` locally and let `P2-03` fold it into the broader hierarchy later without changing its behavior.

## Acceptance Test
1. Build a fixture with a genuine cycle (A depends on B, B depends on A) and confirm `python3 -m bga.cli analyze <cyclic-fixture>` exits with code `3` and a message naming the cycle's nodes (check exit code via `echo $?` after running).
2. Confirm a non-cyclic fixture still exits `0` (no regression).
3. `PYTHONPATH=. python3 tests/test_e2e.py` still passes.

## Verification Log
```
$ python3 -m bga.cli analyze <cyclic 2-element fixture>
Error: Graph contains a cycle - Graph contains a cycle involving elements: a.bst, b.bst
exit: 3

$ python3 -m bga.cli analyze <non-cyclic fixture>
exit: 0

$ PYTHONPATH=. python3 -m pytest tests/unit/test_cli_exit_codes.py -v
5 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
43 passed
```
