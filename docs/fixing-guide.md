# Fixing Guide — Read This First, Every Session

This is the mandatory entry point for any agent (human or LLM) picking up a fix task on this repository. It exists because a prior fixing session, working with limited context, marked several tasks "🟢 Fixed" that were not actually fixed — including `classify_scheduler_wait()` in `bga/attribution/blame_chain.py`, which still unconditionally `return False` after being marked complete. This guide's rules exist specifically to prevent that failure mode from repeating.

**If you have limited context budget: read only this file, then only the one task file you selected. Do not read `docs/specification.md` end-to-end. Do not read the whole codebase. Every task file tells you exactly which line ranges to open.**

---

## 1. How to pick a task

1. Open `docs/fix-progress-tracker.md`. It's a compact table, not a document to read cover-to-cover.
2. Find the highest-priority row with status 🔴 (Not Started) or 🟡 (In Progress) whose **Depends on** column is empty or all 🟢.
3. Open **only** that task's file under `docs/tasks/`. Each task file is self-contained: it tells you the exact spec lines to read, the exact source lines to open, what to change, what NOT to touch, and how to prove you're done.
4. Do not open a second task in the same session unless the first is fully committed and verified. One task, one commit, one context budget.

## 2. Working a task

1. Read the task file fully. It has five sections: Spec Reference, Current Broken Behavior, Required Fix, Out of Scope, Acceptance Test.
2. Read *only* the cited spec line range, e.g. `sed -n '586,649p' docs/specification.md` — not the whole file.
3. Read *only* the cited source file/line range before editing.
4. Implement the minimal fix described. If the task references a `# Simplified`, `# Would need...`, `# TODO`, `pass`, or hardcoded `return False`/`return True`/`None` placeholder, that placeholder must be replaced with real logic — not left in place with a comment removed.
5. Stay inside the task's declared scope. If you notice an unrelated bug while working, **do not fix it inline** — add a new row to `docs/fix-progress-tracker.md` (status 🔴, brief note, no task file needed yet) and leave it for a future session. Scope creep is what causes low-context sessions to run out of budget before finishing the one thing they started.
6. Never delete, weaken, or skip an existing test to make your change pass. If an existing test's expectation was actually wrong per spec, fixing the test is in-scope only if the task file says so explicitly.

## 3. Definition of Done — mandatory verification

**A task may only be marked 🟢 Fixed & Verified if you have personally run its Acceptance Test in this session and it passed.** Self-assessment ("this looks correct now") is not sufficient — that is exactly how the scheduler-wait regression above happened.

For every task, before marking it done:
1. Run the exact command(s) given in the task's **Acceptance Test** section.
2. Paste the actual command and actual output into the task file's **Verification Log** section (append, don't overwrite prior entries).
3. Also run the full existing suite to confirm you didn't regress anything else:
   ```
   PYTHONPATH=. python3 tests/test_e2e.py
   ```
   (Add `python3 -m pytest -q` too, once `pytest` is available in the environment — see `docs/tasks/P2-02-malformed-input-error-handling.md` area for environment notes; for now the direct-run e2e script is the reliable baseline.)
4. Only then: update the status cell in `docs/fix-progress-tracker.md` to 🟢, and update the task file's own status line.
5. If the acceptance test does **not** pass after your change, leave status at 🟡 (In Progress) with a note on what's blocking, and stop — do not mark it 🟢 "mostly working."

Status legend (same as the tracker):

| Status | Meaning |
|---|---|
| 🔴 Not Started | No work begun |
| 🟡 In Progress | Work underway, or claimed-done-but-unverified (treat as not-done until re-verified) |
| 🟢 Fixed & Verified | Acceptance test run in this session, passed, output pasted into Verification Log |
| ⚪ Blocked / Out of Scope | Needs a product decision or is deliberately deferred — see task file for why |

## 4. Committing

- One task = one commit. Commit message format: `fix(<task-id>): <short description>`, e.g. `fix(P1-02): implement real scheduler-wait detection`.
- Reference the task file path in the commit body if the message needs more than one line.
- Do not bundle multiple task IDs into one commit, even if they touch the same file — this makes it possible to revert or re-review one fix without losing another.

## 5. Hard rules (do not violate these)

- **Never mark a task 🟢 without a pasted, passing verification command.**
- **Never leave a no-op placeholder** (`pass` inside a loop that should compute something, `return False`/`return True`/`None` standing in for real logic, empty dict/list returned where a real computation is expected) and call it "implemented." If you can't finish the real logic in your context budget, leave it 🟡 with an honest note on what's missing — don't disguise it as done.
- **Never widen scope.** Fix only what the task file describes. Log anything else you notice as a new tracker row instead.
- **Never invent data the spec says must be `UNKNOWN`/`unavailable`/absent.** E.g. Part 8 requires an unidentifiable resource holder to be reported as `blocking_tasks = UNKNOWN, ambiguous = true` — never fabricate a plausible-looking holder.
- **Never touch `docs/specification.md`.** It's the ground truth; if you think it's wrong, flag it in the tracker's notes for a human to decide, don't edit it.
- **Prefer exact integer arithmetic** for anything invariant-related (durations, timestamps) per spec Part 3.1 — floats only at the final report-formatting boundary.

## 6. Where things live (context map — don't re-derive this)

```
bga/ingest/          JSON loading, dataclasses (models.py)
bga/normalize/        timestamp quantization, ordering validation (timestamps.py)
bga/occupancy/        sweep-line occupancy, task horizon (sweep.py)
bga/graph/             EDG: depth, reachability, dominators, critical path (edg.py)
bga/attribution/      blame chain, dependency gate, resource/scheduler wait (blame_chain.py)
bga/replay/            deterministic replay scheduler, capacity sweep (scheduler.py)
bga/utilisation/       CPU buckets, oversubscription (__init__.py)
bga/diagnostics/       wall-clock share, blast radius, criticality, leaf analysis (analyzer.py)
bga/structural/        M6 cold/structural analysis, networkx-based (analyzer.py, models.py)
bga/analyzer.py        orchestrator — wires every stage together, BuildEfficiencyAnalyzer
bga/cli.py              argparse CLI, output formatters
tests/test_e2e.py      only existing test file; also runnable directly (has its own main())
docs/specification.md v9 spec, ground truth, 2738 lines — use line ranges, never read whole file
docs/fix-progress-tracker.md  status index — start here every session
docs/tasks/*.md         one file per atomic fix — open only the one you're working
```

## 7. Quick fixture for manual CLI testing

If a task needs an end-to-end CLI check and no fixture exists yet under `tests/fixtures/`, you can build a minimal 3-task run dir like this (adjust as needed — do not commit throwaway fixtures to the repo root, put reusable ones under `tests/fixtures/`):

```python
import json, os
d = "/tmp/bga_test_run"
os.makedirs(d, exist_ok=True)
run_context = {"trace_epsilon_us": 50000, "wall_start_us": 0, "wall_end_us": 450000,
               "max_jobs": 1, "resource_capacities": {"PROCESS": 1}}
graph = {"elements": [{"uid": "a.bst", "cache_key": "k1", "requested_target": True},
                       {"uid": "b.bst", "cache_key": "k2", "requested_target": True},
                       {"uid": "c.bst", "cache_key": "k3", "requested_target": True}],
         "dependencies": [{"predecessor": "a.bst", "successor": "b.bst", "scope": "build"},
                           {"predecessor": "b.bst", "successor": "c.bst", "scope": "build"}]}
trace = {"spans": [{"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 150000,
                     "resources": ["PROCESS"], "primary_resource": "PROCESS"},
                    {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 150000, "dur_us": 150000,
                     "resources": ["PROCESS"], "primary_resource": "PROCESS"},
                    {"task_key": "c.bst|BUILD|BUILD|0", "ts_us": 300000, "dur_us": 150000,
                     "resources": ["PROCESS"], "primary_resource": "PROCESS"}], "phases": []}
json.dump(run_context, open(f"{d}/run-context.json", "w"))
json.dump(graph, open(f"{d}/graph.json", "w"))
json.dump(trace, open(f"{d}/trace.json", "w"))
```
Then: `python3 -m bga.cli analyze /tmp/bga_test_run`

**Known live bug as of this writing, useful as a sanity check:** running this exact fixture through the CLI currently prints an Attribution Breakdown that sums to ~33% of the task horizon (only `execution_on_chain_us` populated at 150000µs, everything else 0, against H=450000µs) — this violates invariant I4 (Σ attribution == H) and is tracked as `P1-03`. If you fix P1-03 correctly, re-running this exact fixture should show the attribution breakdown summing to 450000µs.
