# Fixing Guide — Read This First, Every Session

This is the mandatory entry point for any agent (human or LLM) picking up a task on this repository. It exists because a prior fixing session, working with limited context, marked several tasks "🟢 Fixed" that were not actually fixed — including `classify_scheduler_wait()` in `bga/attribution/blame_chain.py`, which still unconditionally `return False` after being marked complete. This guide's rules exist specifically to prevent that failure mode from repeating - the discipline below applies to any backlog in this repo, not just the one it was originally written for.

**If you have limited context budget: read only this file, then only the one task file you selected. Do not read `docs/spec/specification.md` end-to-end. Do not read the whole codebase. Every task file tells you exactly which line ranges to open.**

> **Two backlogs exist.** `docs/backlog/progress-tracker.md` / `docs/backlog/tasks/` is the original spec-compliance backlog - **closed**, every row 🟢 Done, kept as a historical record. `docs/backlog/scenarios/` is the active backlog (usability, optimization-workflow, and other non-spec-compliance work) - **start there** for anything new. The rest of this guide applies to either.

---

## 1. How to pick a task

1. Open `docs/backlog/scenarios/README.md` for active work (or `docs/backlog/progress-tracker.md` if you're specifically re-verifying the closed spec-compliance backlog). Both are compact tables, not documents to read cover-to-cover.
2. Find the highest-priority row with status 🔴 (Not Started) or 🟡 (In Progress) whose **Depends on** column is empty or all 🟢.
3. Open **only** that task's file. Each task file is self-contained: it tells you the exact spec/background to read, the exact source lines to open, what to change, what NOT to touch, and how to prove you're done.
4. Do not open a second task in the same session unless the first is fully committed and verified. One task, one commit, one context budget.

## 2. Working a task

1. Read the task file fully. It has five sections: Spec Reference, Current Broken Behavior, Required Fix, Out of Scope, Acceptance Test.
2. Read *only* the cited spec line range, e.g. `sed -n '586,649p' docs/spec/specification.md` — not the whole file.
3. Read *only* the cited source file/line range before editing.
4. Implement the minimal fix described. If the task references a `# Simplified`, `# Would need...`, `# TODO`, `pass`, or hardcoded `return False`/`return True`/`None` placeholder, that placeholder must be replaced with real logic — not left in place with a comment removed.
5. Stay inside the task's declared scope. If you notice an unrelated bug while working, **do not fix it inline** — add a new row to the tracker you're working from (status 🔴, brief note, no task file needed yet) and leave it for a future session. Scope creep is what causes low-context sessions to run out of budget before finishing the one thing they started.
6. Never delete, weaken, or skip an existing test to make your change pass. If an existing test's expectation was actually wrong per spec, fixing the test is in-scope only if the task file says so explicitly.

## 3. Definition of Done — mandatory verification

**A task may only be marked 🟢 Fixed & Verified if you have personally run its Acceptance Test in this session and it passed.** Self-assessment ("this looks correct now") is not sufficient — that is exactly how the scheduler-wait regression above happened.

For every task, before marking it done:

1. Run the exact command(s) given in the task's **Acceptance Test** section.
2. Paste the actual command and actual output into the task file's **Verification Log** section (append, don't overwrite prior entries).
3. Also run the full existing suite to confirm you didn't regress anything else:

   ```text
   pip install pytest   # if not already installed in this session - confirmed installable via pip
   PYTHONPATH=. python3 -m pytest tests/ -v
   ```

   `tests/test_e2e.py` is also directly runnable without pytest (`PYTHONPATH=. python3 tests/test_e2e.py`) if you want the fastest possible sanity check, but prefer the full `pytest tests/ -v` run before marking anything 🟢 — it now also covers `tests/test_cli.py` and `tests/test_synthetic_multi_subproject.py` (a larger multi-subproject fixture; see `docs/backlog/tasks/P3-10-synthetic-multi-subproject-large-test.md`), both of which the single e2e script does not run. Tests marked `xfail` (a handful, each pointing at the specific task file that will fix them) are expected — only genuinely new failures are regressions.
4. Only then: update the status cell in the tracker (`docs/backlog/progress-tracker.md` or `docs/backlog/scenarios/README.md`) to 🟢, and update the task file's own status line. **Both, in the same commit.** These are two hand-maintained copies of one fact and they have drifted in three separate rounds — round 11 found a row 🟢 over a 🔴 file, round 12 found row wording drift, round 13 found *five* rows 🔴 over files that were 🟢 with full verification logs, because the closing commit of a range never touched the table. `tests/unit/test_docs_links_and_commands.py::test_the_table_status_matches_the_task_files` now compares the two markers and fails naming the item, so this one is caught rather than trusted (`UX-131`).
5. **If your fix changes a number an earlier task file quotes, annotate that file in the same commit.** Not a rewrite — the old figure stays, with one line naming what changed it and when, the way `UX-118` annotated `UX-106`'s superseded explanation: *"a wrong explanation that was believed for a while is worth being able to recognise again"*. `UX-123`'s exec-chain collapse moved `examples/06` from 822 processes to 813 and left three earlier files describing a parser that no longer exists; a later task then quoted 822 fresh, because the convention lived only where one author remembered it. `git grep <old figure> docs/backlog/scenarios` before you commit. This one is judgment-shaped and cannot be a hard test — it is a checklist item precisely because of that (`UX-132`).
6. If the acceptance test does **not** pass after your change, leave status at 🟡 (In Progress) with a note on what's blocking, and stop — do not mark it 🟢 "mostly working."

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

## 4a. Repository hygiene — mandatory before every commit

**A real incident, so this isn't hypothetical:** a prior fixing session ran `pip install "networkx>=2.8"` in a shell that mangled the unquoted `>`, redirecting command output into a literal file named `=2.8`, then committed it — along with `bga.egg-info/` and every package's `__pycache__/*.pyc` — straight into the repo, even though `.gitignore` already listed all of those patterns. `.gitignore` only stops *new* untracked files from being added by `git add .`/`git add -A`; it does nothing once a file is already tracked, and it does nothing to stop `git add <specific-ignored-path>` or a broad `git commit -a` from re-adding something after the fact.

Rules to prevent a repeat:

1. **Never run `git add -A` or `git add .`.** Stage specific files by name/path so you can see exactly what's going in.
2. **Before every commit, run `git status` and read the full list of staged files.** If anything looks like a build artifact, cache file, log, or a filename you don't recognize authoring, stop and investigate before committing — don't assume it's fine.
3. **Run `make check-clean` before committing.** It fails loudly if any tracked file matches a `.gitignore` pattern (this is exactly the check that would have caught the `=2.8`/`egg-info`/`__pycache__` incident). If it fails on a *pre-existing* tracked artifact you didn't add, still fix it — `git rm -r --cached <path>` and commit that removal — rather than leaving it for the next session.
4. **Watch shell redirection when running install/build commands.** `pip install "networkx>=2.8"` (quoted) is safe; `pip install networkx>=2.8` (unquoted) is a shell redirect waiting to happen in some shells/contexts. Quote version specifiers, and check `git status` immediately after running any command with `>` or `>>` in it.
5. **Temporary/scratch files belong outside the repo**, or at minimum in a path already covered by `.gitignore` (e.g. don't invent new throwaway fixture files under the repo root — put reusable fixtures under `tests/fixtures/`, per `docs/backlog/tasks/P3-01-topology-fixture-library.md`, and anything truly throwaway outside the repo entirely).
6. If you're ever unsure whether something should be committed, leave it uncommitted and note it in the task's Verification Log rather than guessing.

## 5. Hard rules (do not violate these)

- **Never mark a task 🟢 without a pasted, passing verification command.**
- **Never leave a no-op placeholder** (`pass` inside a loop that should compute something, `return False`/`return True`/`None` standing in for real logic, empty dict/list returned where a real computation is expected) and call it "implemented." If you can't finish the real logic in your context budget, leave it 🟡 with an honest note on what's missing — don't disguise it as done.
- **Never widen scope.** Fix only what the task file describes. Log anything else you notice as a new tracker row instead.
- **Never invent data the spec says must be `UNKNOWN`/`unavailable`/absent.** E.g. Part 8 requires an unidentifiable resource holder to be reported as `blocking_tasks = UNKNOWN, ambiguous = true` — never fabricate a plausible-looking holder.
- **Never touch `docs/spec/specification.md`.** It's the ground truth; if you think it's wrong, flag it in the tracker's notes for a human to decide, don't edit it.
- **Prefer exact integer arithmetic** for anything invariant-related (durations, timestamps) per spec Part 3.1 — floats only at the final report-formatting boundary.

## 6. Where things live (context map — don't re-derive this)

```text
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
docs/spec/specification.md v9 spec, ground truth — use line ranges, never read whole file
docs/backlog/progress-tracker.md  spec-compliance backlog index — closed, historical record
docs/backlog/tasks/*.md         spec-compliance task files (closed backlog) — open only if re-verifying one
docs/backlog/scenarios/README.md  active backlog index — start here for new work
docs/backlog/scenarios/*.md    active task files — open only the one you're working
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

A quick correctness sanity check with this fixture: the Attribution Breakdown should sum to the full 450000µs task horizon (I4, Σ attribution == H) - if it doesn't, something regressed in the attribution pipeline, and that's worth investigating before anything else.
