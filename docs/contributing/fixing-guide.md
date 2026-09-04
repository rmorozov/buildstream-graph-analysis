# Fixing Guide — Read This First, Every Session

This is the mandatory entry point for any agent (human or LLM) picking up a task on this repository. It exists because a prior fixing session, working with limited context, marked several tasks "🟢 Fixed" that were not actually fixed — including `classify_scheduler_wait()` in `bga/attribution/blame_chain.py`, which still unconditionally `return False` after being marked complete. This guide's rules exist specifically to prevent that failure mode from repeating - the discipline below applies to any backlog in this repo, not just the one it was originally written for.

**Start at [`rules.md`](rules.md)** — every rule below as one line with
its guard, an order of magnitude smaller than this file (`UX-505`). Come
here for the paragraph behind the rule you are about to break: this file
is ~40 KB because each one carries the incident that produced it, and
that is why it is trusted, not padding.

**If you have limited context budget: read the card, then only the one task file you selected. Do not read `docs/spec/specification.md` end-to-end. Do not read the whole codebase. Every task file tells you exactly which line ranges to open.**

> **Two backlogs exist.** `docs/backlog/progress-tracker.md` / `docs/backlog/tasks/` is the original spec-compliance backlog - **closed**, every row 🟢 Done, kept as a historical record. `docs/backlog/scenarios/` is the active backlog (usability, optimization-workflow, and other non-spec-compliance work) - **start there** for anything new. The rest of this guide applies to either.

**Three procedures here are also skills** (`UX-240`), for a session
that would otherwise re-derive them: `.claude/skills/verify` (§3 as a
sequence you can run), `.claude/skills/falsify` (the mutation
discipline, with the failure modes that have cost this repository
something), and `.claude/skills/measure` (the golden snapshot, the
scale run, the export split, re-timing the tiers). They are entry
points, not second copies — where a skill and this guide disagree, this
guide is right and the skill is a bug.

---

## 1. How to pick a task

1. **First decide which stream you are in** (`§6a`). Only *feature* and *fix* start from a backlog row; *design* and *audit* produce rows and have none to pick, and *documentation* and *refactor* may start from either. If your instruction was "audit the last range" or "where should this go", steps 2-4 do not apply to you — `§6a` says what does.
2. Open `docs/backlog/scenarios/README.md` for active work (or `docs/backlog/progress-tracker.md` if you're specifically re-verifying the closed spec-compliance backlog). Both are compact tables, not documents to read cover-to-cover.
3. Find the highest-priority row with status 🔴 (Not Started) or 🟡 (In Progress) whose **Depends on** column is empty or all 🟢.
4. Open **only** that task's file. Each task file is self-contained: it tells you the exact spec/background to read, the exact source lines to open, what to change, what NOT to touch, and how to prove you're done.
5. Do not open a second task in the same session unless the first is fully committed and verified. One task, one commit, one context budget.

## 2. Working a task

1. Read the task file fully. It has five sections: Spec Reference, Current Broken Behavior, Required Fix, Out of Scope, Acceptance Test.
2. Read *only* the cited spec line range, e.g. `sed -n '586,649p' docs/spec/specification.md` — not the whole file.
3. Read *only* the cited source file/line range before editing.
4. Implement the minimal fix described. If the task references a `# Simplified`, `# Would need...`, `# TODO`, `pass`, or hardcoded `return False`/`return True`/`None` placeholder, that placeholder must be replaced with real logic — not left in place with a comment removed.
5. Stay inside the task's declared scope. If you notice an unrelated bug while working, **do not fix it inline** — add a new row to the tracker you're working from (status 🔴, brief note, no task file needed yet) and leave it for a future session. Scope creep is what causes low-context sessions to run out of budget before finishing the one thing they started.
6. **Touching the web report? Run the conformance checklist before you commit** (`UX-305`, [`docs/design/styleguide.md`](../design/styleguide.md) §7). Three questions, and each has a rule behind it: **is the shape in the §1 table?** (a shape it does not cover is a design task — it lands in the guide with its control, then in the code); **is the sentence written?** (a drawing owes its reader one sentence and its `n`); **is the budget kept?** (one emphasized element per block, one accent, status tone never on text and never alone). A section that cannot answer all three either changes or amends the guide — and the guards in `test_the_mapping_is_law.py`, `test_the_palette_is_validated.py`, `test_the_shape_before_the_rows.py` and `test_emphasis_is_a_budget.py` will say which. Round 44 added four more questions and `UX-320` made each one a walk over the whole page: **is every drawing graded, at a box from the scale?** (§2a — `test_a_drawing_is_graded.py`); **is every control's explanation with the control, and the header identity only?** (§2b — `test_apparatus_in_its_place.py`); **does every fold say how deep it goes, and does nothing scroll inside a scrollbox?** (§3a — `test_the_fold_says_how_deep_it_goes.py`); **is every section's content two interactions from its rail entry?** (§3b — `test_the_chain_folds_and_clicks_are_counted.py`). `test_the_page_conforms_to_its_sections.py` runs all four over the booted page, which is what catches a surface none of the four items enumerated.
6. Never delete, weaken, or skip an existing test to make your change pass. If an existing test's expectation was actually wrong per spec, fixing the test is in-scope only if the task file says so explicitly.

## 3. Definition of Done — mandatory verification

**A task may only be marked 🟢 Fixed & Verified if you have personally run its Acceptance Test in this session and it passed.** Self-assessment ("this looks correct now") is not sufficient — that is exactly how the scheduler-wait regression above happened.

**Some acceptance tests cannot run here.** A claim about behaviour
across machines — more than one runner, a loaded runner, CI's own clock —
has no local instrument, and `make test` in this container cannot falsify
it. CI runs on `pull_request` and pushes to `main` only, so for that kind
of work open the PR (draft is fine) before starting rather than after.
The `verify` skill's section 7 has the sequence and its limits.

**This environment hands you a shallow clone** (`UX-637`). Ask
`git rev-parse --is-shallow-repository` before measuring anything from
history; `git fetch --unshallow` is the fix, and **a history figure taken
before that is worth nothing**. Round 86 read 562 commits, 1202 after, and
`merge-base --is-ancestor v0.2.0 origin/main` flipped from exit 1 to 0 —
costing a filed row, a user decision and four CI runs. CI sets
`fetch-depth: 0` and was right every time. A guard that reads history
declines rather than concluding
(`test_a_guard_that_reads_history_declares_its_depth.py`).

For every task, before marking it done:

1. Run the exact command(s) given in the task's **Acceptance Test** section.
2. Paste the actual command and actual output into the task file's **Verification Log** section (append, don't overwrite prior entries).
3. **While you work, run the tests that touch what you changed** (`UX-336`): `make test-touching` maps the working diff to the test files that name it - 11-126 of 470 test files, median 17, over every module the map names, not the seconds one machine spent on one of them (`UX-632`). `python3 tools/dev_touching.py --spread --write` is the only thing that writes that figure. Wider than one module, run the tier (`UX-238`). Every target runs `-n auto`. **The suite's wall clock is a property of the machine, not of the suite** (`UX-551`), so budget a round against the spread and not a figure:

```text
round 46   3m15s                                     4 cores
round 74   5m28s   5,635 passed,  81 skipped, 328s   4 cores
round 80   8m52s   6,181 passed,  29 skipped, 533s   4 cores
round 81   3m45s   6,256 passed,  29 skipped, 226s   4 cores, quiet
  and round 80's own tree (`ca825c3`) re-measured in round 81:
           3m32s   6,097 passed, 124 skipped, 212s   worktree
```

Round 80's 8m52s is **not reproducible on the tree that produced it**: the same commit reads 3m32s on a quiet machine. The suite grew by 621 tests between rounds 74 and 81 and got *faster* in wall clock. So a single dated sample dates the afternoon, not the suite — measure it yourself when the number matters, and record the load average beside it. The small tier is 20s:

   | target | measured at `-n auto` | what is in it |
   |---|---|---|
   | `make test-touching` | 11-126 of 470 test files, median 17 | the test files that name what your diff touched |
   | `make test-small` | **20s** | pure Python over in-memory fixtures — the default tier |
   | `make test-medium` | ~2m50s | spawns a process or a node harness |
   | `make test-large` | ~2m05s | scale fixtures, real process trees |
   | `make test-fast` | ~3m10s | small + medium: everything needing no real `bst` |
   | `pytest -m bst` | — | the enormous tier; needs a real `bst`/`bwrap` build |

   Re-measured 2026-09-03 (`UX-584`) on the same 4-core container, with
   `uptime` beside each run because wall clock here moves more than 2x
   with load: `time make test-small` read 20.8s (3,698 passed, 36
   skipped) at 1-minute load **0.13**; medium read 2m53s at load
   **1.05** and large 2m06s at load **6.02**, both with other
   worktrees running, so those two are the machine's number and not
   the tier's. `PYTEST_XDIST=` turns the parallelism off for a run
   that needs one process.

   Tiers come from measured per-file duration (`tests/tiers.py`), not from taste. Use them for the edit-run loop and for re-running one guard after a mutation — **not** as a substitute for the next step.

4. Also run the full existing suite to confirm you didn't regress anything else. **`UX-500` asked whether this could become one run per *batch* and the answer is no**, measured over two rounds rather than argued: run `dev_touching.select` over each responsible commit's own diff and ask whether the guard that caught the defect is in the set the cheap gate would have chosen. Round 75 (Regime A, 7 items): **2 of 5**. Round 80 (Regime B, 24 items, six parallel tracks): **4 of 9** — it did not fall when the batch got three times larger. The four have a shape: the selector maps a diff to the guards that *name* what it touched, and three of them read a **consequence** — a new contract landing in every committed fixture, a reworded sentence another file greps for, a file's own duration crossing a tier floor. No grep over a diff can find those. Figures in [`docs/audits/round-80.md`](../audits/round-80.md) and [`round-75.md`](../audits/round-75.md); the batch gate stays *in addition*, not instead:

   ```text
   pip install pytest   # if not already installed in this session - confirmed installable via pip
   PYTHONPATH=. python3 -m pytest tests/ -v
   ```

   `tests/test_e2e.py` is also directly runnable without pytest (`PYTHONPATH=. python3 tests/test_e2e.py`) if you want the fastest possible sanity check, but prefer the full `pytest tests/ -v` run before marking anything 🟢 — it now also covers `tests/test_cli.py` and `tests/test_synthetic_multi_subproject.py` (a larger multi-subproject fixture; see `docs/backlog/tasks/P3-10-synthetic-multi-subproject-large-test.md`), both of which the single e2e script does not run. Tests marked `xfail` (a handful, each pointing at the specific task file that will fix them) are expected — only genuinely new failures are regressions.
5. Only then: update the status cell in the tracker (`docs/backlog/progress-tracker.md` or `docs/backlog/scenarios/README.md`) to 🟢, and update the task file's own status line. **Both, in the same commit.** These are two hand-maintained copies of one fact and they have drifted in three separate rounds — round 11 found a row 🟢 over a 🔴 file, round 12 found row wording drift, round 13 found *five* rows 🔴 over files that were 🟢 with full verification logs, because the closing commit of a range never touched the table. `tests/unit/test_docs_links_and_commands.py::test_the_table_status_matches_the_task_files` now compares the two markers and fails naming the item, so this one is caught rather than trusted (`UX-131`).
6. **If your fix changes a number, a mechanism or an explanation an earlier task file presents as current, annotate that file in the same commit.** Not a rewrite — the old figure stays, with one line naming what changed it and when, the way `UX-118` annotated `UX-106`'s superseded explanation: *"a wrong explanation that was believed for a while is worth being able to recognise again"*. `UX-123`'s exec-chain collapse moved `examples/06` from 822 processes to 813 and left three earlier files describing a parser that no longer exists; a later task then quoted 822 fresh, because the convention lived only where one author remembered it. `git grep <old figure> docs/backlog/scenarios` before you commit. This one is judgment-shaped and cannot be a hard test — it is a checklist item precisely because of that (`UX-132`). **It covers mechanisms, not only figures** (`UX-144`), and the precedent `UX-132` itself cites is a mechanism: `UX-118` annotated `UX-106`'s superseded *explanation*. The scope was written as "a number" and the very next range showed why that is too narrow — `UX-130` deleted `UX-118`'s entire seen-set (`g_seen`/`first_stop_for`/`forget_pid`) and `UX-128`'s `initial` restart site, leaving both files describing code that no longer exists, including the worked example the convention was built on. `git grep` the removed identifier as well as the old figure.
7. **If your fix renames or removes a key in a published JSON output, bump that output's schema version.** `analyze/v6`, `compare/v2` and `blast/v2` (`bga/schemas.py`, spec Part 32.5) are what a consumer pins; `test_the_process_documents_derive_their_figures.py` reads the three ids off `schemas.py` so this sentence cannot age. The first bump was `UX-288`, which took the report to `analyze/v2` by removing three fields that republished element membership. Adding a *permitted* key is not a breaking change and does not bump — the schemas set `additionalProperties: true` for exactly that reason — but a key entering **`required`** under a live id **is** (`UX-629`): a document a consumer already wrote stops validating, which is a break by the only reading a consumer has. A key the emitter writes on every document therefore lands permitted-and-always-written — declared in the schema's own `bga:always_written` so `--schema` states the choice, and guaranteed against the real payload by a guard rather than by `required`. A rename is a break too, and the round-19 range shipped one (`runs_outside_band` → `edges_outside_band`) with nothing to signal it, which is what `UX-190` was filed against. `tests/unit/test_output_schemas.py` catches a removal; `ANALYZE_FULL_KEYS` catches a rename of an `analyze` key the schema cannot mark required.

8. **Does this change which roles are served, or how well? Then `docs/design/roles.md`'s table changes in the same commit.** The gap analysis round 27 wrote — four roles served thoroughly, four barely — only stays true if the tracing is routine (`UX-231`). A new direction carries a `Serves:` line at birth; a new filing carries one in its header.

9. **A guard that asserts an order must read the order the page has, not restate it.** `UX-235` found two that did not: the harness built the expected sequence as a literal over three separately invoked renderers, so `root.prepend(decision)` mutated to `append` left it green — measured, 26 passed before and 26 after. Worse, the one harness that boots the real exported page implemented `prepend` as `append`, so *no* order guard written against it could have meant anything. The pattern, for the next "X above Y" claim: boot the page, walk the root's children, compare indices — never write the expected sequence down. `tests/unit/test_the_order_the_page_has.py` is the worked example. The same rule generalises: **a guard that names one file will not see the second one.** Round 21's seam-6 guard banned a module-scope `importorskip` in `test_output_schemas.py` by name, and a file added four rounds later walked straight past it with twenty-one guards behind one import.

10. **Does this change what `docs/design/architecture.md` or the spec says is true? Then they change in the same commit.** The user's observation, and it is measurable: when `UX-233` was filed, `architecture.md` still described three analysis planes and stopped at round 20 — before the entire viewer axis (the server, the schema-driven page, the export) and before the contract wave that followed it — and five of the eight published schemas were named in no document at all. Documentation that has fallen a whole axis behind is what makes a big refactor expensive to price, which is exactly the cost the observation names. The mechanical half is guarded: `tests/unit/test_the_documents_keep_up_with_the_contracts.py` asserts every schema id the code emits appears in the spec's Part 32.5 and in the architecture inventory, and that neither names one nothing emits. The judgment half — a *mechanism* the document describes and your change moved — is a checklist item for the same reason item 6 is.

11. **Does this change need documentation you are not writing now? File it before the commit lands.** There were two escape valves for work a session cannot do — a bug you notice becomes a tracker row (`§2.5`), and a doc your change made *wrong* is fixed in the same commit (item 10) — and no door at all for the third and commonest shape: *this needs a proper explanation, and writing it well is half a session's work.* That thought had nowhere to go, so it became a comment, or nothing. Round 28 produced three instances and all three survived only because someone happened to say so out loud: `capacity_recommendation` and `memory_envelope` reach no consumer, and `bga/whatif.py`'s convention was documented only in its own docstring. The rule is the same shape as `§2.5` and costs the same: a row in `docs/backlog/scenarios/README.md` — id, one line, 🔴, topic `docs` — in the commit that creates the debt. A task file can come later; naming the gap is the minimum. If you decide the gap is not worth documenting, say that in the Outcome instead — a stated decline is a decision, and silence is not. `tests/unit/test_documentation_debt_has_a_door.py` holds the mechanical half: a filing that defers documentation must name where it went (`UX-237`).
12. **`docs/spec/specification.md` is ground truth, and Part 32 is the one Part a round may edit.** `UX-556` is what settled the boundary, because a round hit it and read it two ways. The spec's contract registry said "The last four are **written but not printable**" of a set that is six (`unprintable()` less `superseded()`) and that four rows follow; `UX-549` fixed the architecture's copy of the same sentence and filed the spec's, reading the rule as forbidding the edit. It does not: the sentence is at line 1671 and Part 32 spans 1515-1940, so it was inside the permitted region the whole time (the range is derived by `test_the_spec_outside_part_32_is_read_only.py`, which also digests everything outside it). **The Part, not the table** — a rule that lets you correct a registry row but not the sentence counting the rows is not a boundary, it is an accident of where someone drew the line. Everything outside Part 32 stays read-only for a round; a factual error there is filed, not fixed. And the second half, which is what stops this recurring: **a counted figure in Part 32 is derived by a guard, never restated in prose.** Both copies of this error were prose nothing checked. `tests/unit/test_a_counted_figure_is_derived.py::TestTheSpecCountsItsOwnTable` reads the count and the position off the table's own rows.

13. If the acceptance test does **not** pass after your change, leave status at 🟡 (In Progress) with a note on what's blocking, and stop — do not mark it 🟢 "mostly working."

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
- **Never let an instrument read a proxy for the thing it names.** This is the defect this repository repeats most: a sweep in round 68 found about thirty sightings across about twenty-six items, in four shapes. Before writing a guard, ask what quantity it actually reads, whether that is the quantity its name claims, and whether at the magnitudes it will see it can tell the two answers apart. The four shapes, one worked example each: a **text scan that cannot tell code from data** (`UX-403` — a regex matched `find_chrome()` inside a string literal; tokenise instead of lengthening the pattern); a **ratio at the noise floor** (`UX-420` — thirty-one files reported on an unchanged suite, one of them a 20 ms file reading ×18; require an absolute magnitude too); a **comparison across machines** (`UX-418` — per-file timings from another runner cannot be compared in any form, not absolute, not scaled, not ranked); and the **wrong artifact or population** (`UX-359` — every browser guard measured a page 14% shorter than the one users get). The `measure` skill carries the same three questions at the point they get asked.
- **Prefer exact integer arithmetic** for anything invariant-related (durations, timestamps) per spec Part 3.1 — floats only at the final report-formatting boundary.

## 6. Where things live (context map — don't re-derive this)

Regenerated by `UX-239`; a guard
(`tests/unit/test_the_context_map_is_the_tree.py`) fails if a module
appears here that does not exist, or exists and does not appear — over
`git ls-files`, recursively under `tools/` (Python, C, shell), into
`bga/viewer/` (`UX-573`) and into each `bga/` package (`UX-631`),
because a non-recursive walk left the LD_PRELOAD hook and the ptrace
spine off the map and the guard green, and a package standing in for
its own files gave every module inside it a home for free — 21 of the
26 were on no row. A module is named by its filename **on its
directory's row**: the rule was a substring of the whole map, which
`bga/report/rate.py` satisfied through the `rate` inside `generated`. The
previous version described a tree from the repository's first week —
it said `tests/test_e2e.py   only existing test file` when
`tests/unit/` alone held 218 — which is worse than no map, because it
was confidently wrong exactly where confidence had been requested.

**The pipeline** — one run in, one analysis out:

```text
bga/ingest/            loader.py, models.py - JSON loading and dataclasses
bga/normalize/         timestamps.py - quantization and ordering validation
bga/occupancy/         sweep.py - sweep-line occupancy, task horizon
bga/graph/             edg.py - EDG: depth · reachability · dominators · critical path
bga/attribution/       blame_chain.py - blame chain, dependency gate, resource/scheduler wait
bga/replay/            scheduler.py - deterministic replay and the capacity sweep
bga/utilisation/       detection.py - CPU buckets and oversubscription
bga/diagnostics/       analyzer.py - wall-clock share · blast radius · criticality · leaf analysis
bga/structural/        analyzer.py, batching.py, consolidation.py, models.py, serialization_points.py - networkx-based cold/structural analysis
bga/floors/            capacity.py, cold.py, observed.py, serialization.py - the certified floors
bga/validation/        determinism.py, invariants.py, provenance.py - the hard and soft gates
bga/analyzer.py        orchestrator - wires every stage together, BuildEfficiencyAnalyzer
```

**What it concludes, and what it publishes:**

```text
bga/findings.py        every conclusion the report draws, as data with stable ids
bga/provenance.py      why each claim is made: evidence refs, rule, trace query (UX-229)
bga/schemas.py         every published contract + view-hints; `--schema` prints from here
bga/contracts.py       the derived inventory of every contract, printable or not (UX-248)
bga/producer.py        which build wrote an artifact, and the contract set it had (UX-249)
bga/report/            text.py, json.py, ci_comment.py - renderers · _shared.py the section names they share · rate.py converts build seconds into the reader's unit (UX-596)
--format               text, json, csv, ci-comment - what a run can be asked for
```

**The commands that are not `analyze`:**

```text
bga/compare.py         two runs, the noise band, the verdict, the culprits
bga/blast.py           what rebuilds if one resource changes
bga/correlate.py       the two planes joined on element uid
bga/whatif.py          the projection for a chosen set of fixes (UX-230)
bga/cache_trend.py     a series of runs, not a pair
bga/cache_effectiveness.py  the cache's own numbers
bga/store_aggregate.py the store as a distribution, per host class (UX-234)
bga/capacity_model.py  Allen-Cunneen M/G/c over that distribution, each
                       assumption recorded where the arithmetic uses it (UX-595)
bga/run_store.py       .bga/runs, the @last/@prev aliases, prune
bga/bundle.py          a capture packed to carry, and what the far
                       side refuses to half-read (UX-520)
bga/sources.py         the source inventory and resource identity
bga/plane2.py          what a Plane 2 report is, and which shape one is
bga/hostinfo.py        the host manifest; the cross-host refusal
bga/units.py           the payload's units, and the two input
                       boundaries that convert into them (UX-341)
bga/suspend.py         did this capture sleep
bga/cli.py             argparse CLI and dispatch
bga/tools_dispatch.py  the `tools/` aliases `bga` exposes as subcommands
bga/progress.py, help_format.py, logging_config.py, exceptions.py
```

**Every command `bga` answers to** (`UX-608`) — the subcommands, then
the `tools/` aliases `bga/tools_dispatch.py` exposes, and where each
one's work is done:

```text
analyze         bga/analyzer.py
blast           bga/blast.py
bundle          bga/bundle.py
cache-trend     bga/cache_trend.py
compare         bga/compare.py
correlate       bga/correlate.py
diagnostics     bga/diagnostics/
floors          bga/floors/
graph           bga/graph/
replay          bga/replay/
sweep           bga/replay/        the capacity sweep, not a slice of one analysis
utilisation     bga/utilisation/
whatif          bga/whatif.py
baseline          tools/bst_baseline_set.py
cache-logs        tools/bst_cache_logs.py
capture           tools/bst_native_build_tracer.py
checkout-cost     tools/bst_checkout_cost.py
chrome-to-trace   tools/chrome_trace_to_bga_trace.py
cross-check       tools/bga_cross_check.py
doctor            tools/bga_doctor.py
extract           tools/bst_extract_run.py
gen-synthetic     tools/gen_synthetic_scale_run.py
graph-from-show   tools/bst_show_to_graph.py
log-to-chrome     tools/bst_log_to_chrome_trace.py
native-to-chrome  tools/native_trace_to_chrome_trace.py
rebuild-set       tools/bst_rebuild_set.py
release-notes     tools/bga_release_notes.py
run-context       tools/bst_run_context.py
snapshot          tools/bga_snapshot.py
timeline          tools/bga_timeline.py
view              tools/bga_view.py
wrap              tools/bst_run_wrapped.py
```

**The viewer** (`UX-193`..`UX-235`) — hand-written ES modules, no build
step, no framework:

```text
bga/viewer/app.js      boots the page, loads the documents, wires everything
bga/viewer/views.js    the renderers; imports drawings, controls, primitives
                       (derived: `dev_js_deps.py --graph`, never read off)
bga/viewer/nav.js      table of contents, jump box, command palette
bga/viewer/focus.js    focus and marks (UX-222/225/228)
bga/viewer/tables.js   sortable/filterable tables · viewstate.js  URL state
bga/viewer/questions.js  the Perfetto query library · trace_context.js  the handoff
bga/viewer/perfetto.js   the deep link · style.css, index.html
bga/viewer/chapters.js   the ordering authority: which chapter a section
                         is in, and in what order (UX-286/UX-301)
bga/viewer/shapes.js     the styleguide §1 dispatch table as code -
                         published shape + hint -> the one control (UX-302)
bga/viewer/rawjson.js    the per-section "view as JSON" toggle (UX-302)
bga/viewer/drawings.js   the sparkline and the density strips (UX-303)
bga/viewer/primitives.js the primitives under every chapter - what makes the
                         module graph acyclic at all (UX-337)
bga/viewer/format.js     the `bga:` hint keys, their readers and formatters,
                         and `el`, the one node constructor (UX-337)
bga/viewer/controls.js   a form control the browser can name: label, id, name,
                         so the Issues panel is readable (UX-334)
bga/viewer/element.js    the element object - one element, everything known
                         about it; split out of views.js (UX-337)
bga/viewer/decision.js   the decision panel, UX-207's first screen (UX-337)
bga/viewer/structured.js a value becomes a table, and the table becomes
                         interrogable: filters, sort, Top-N, folds (UX-337)
bga/viewer/tablefocus.js table focus, and the depth a fold announces (UX-318)
bga/viewer/sections.js   the section walk - payload plus schema to DOM, split
                         from app.js, which boots and wires (UX-450)
bga/viewer/perfetto.html the page `bga view --perfetto` lands on: how to open
                         the trace, then what to ask it (UX-194/198/373)
bga/viewer/sql.html      a redirect into that page's second half (UX-373)
bga/viewer/perfetto_page.js  its module - it was an inline script the page's
                         own `default-src 'self'` refused (UX-266)
```

**Capture and the tools** — everything a build actually runs through:

```text
tools/bst_run_wrapped.py     the wrapper that records the real invocation
tools/bst_extract_run.py     wrapped log -> run-context/graph/trace
tools/bst_native_build_tracer.py  Plane 2: the LD_PRELOAD hook and the ptrace spine
tools/bst_cache_logs.py      Plane 3: BuildStream's own kept logs
tools/bga_snapshot.py        the local loop: capture, analyze, compare
tools/bga_doctor.py          can this machine capture at all
tools/bga_view.py            the viewer's server and `--export`
tools/bga_timeline.py        one trace, both planes
tools/bst_baseline_set.py    assembling a baseline set from published refs
tools/bst_show_to_graph.py, bst_rebuild_set.py, bst_checkout_cost.py,
tools/bga_release_notes.py  a release body, generated from the closed rows (UX-252)
tools/bga_cross_check.py, gen_synthetic_scale_run.py, chrome_trace_to_bga_trace.py,
tools/native_trace_to_chrome_trace.py, bst_log_to_chrome_trace.py,
tools/bst_run_context.py, _run_context_common.py
tools/dev_touching.py        the tests that name what your diff touched, plus the census
                             they can never name (UX-336, UX-522)
tools/dev_touch_map.py       which test files executed which module, off CI's own
                             coverage run - the import chain a grep cannot see (UX-524)
tools/dev_close_task.py      the mechanical tail of closing a row (UX-336)
tools/dev_refresh_analysis.py  the rule a committed analysis is written
                             under, and the command that rewrites one
                             from a fresh run (UX-486)
tools/dev_process_bands.py  what the process did to itself, from the committed Outcomes
tools/dev_tier_drift.py      which files outgrew their tier, from the
                             suite's own junit report (UX-418)
tools/dev_junit_tail.py      which tests failed, from the junit a red job
                             kept - when the log tail is the wrong 400 lines (UX-554)
tools/dev_js_deps.py         the viewer's module graph, derived: order, cycles, what would cross a cut (UX-340)
tools/dev_perfetto_queries.py  the canned questions, run against a real
                             trace with Perfetto's own reader (UX-432)
tools/dev_finding_coverage.py  which findings a committed capture really
                             produces, read off analyze (UX-460)
tools/dev_track_cost.py      where an implementer track's tokens went,
                             by phase, from the agent transcript (UX-525)
tools/dev_trace_coverage.py  which captured field reaches the emitted
                             trace, and which Perfetto carriers it uses (UX-466)
tools/bga_gen_project.py     a BuildStream project `bst build` accepts,
                             from a topology spec (UX-465)
tools/dev_plane_capability.py  what Plane 2 and Plane 3 could record and
                             do not, both sides run rather than read (UX-470)
tools/dev_run.sh             one command from "I changed something" to a
                             rendered report, on a committed fixture
tools/native_trace/hook.c    Plane 2's LD_PRELOAD hook: a START line as the
                             linker loads it, an END line as the process exits
tools/native_trace/spine.c   the ptrace spine - what the hook cannot see,
                             because a static executable never loads it (UX-106)
tools/native_trace/trackevent.py  Perfetto's own TrackEvent format, written as
                             a stream by the stdlib (UX-298, Direction 15)
tools/native_trace/bwrap_shim.py  a `bwrap` shim ahead of the real one in
                             `$PATH`, so the hook reaches inside the sandbox
```

**Tests and docs:**

```text
tests/unit/                one file per item, named for its claim - the bulk of the suite
tests/tiers.py             which tier each file is in, from measurement (UX-238)
tests/conftest.py          the tier hook and the skip census (UX-235)
tests/ci_reference.json    one CI run's per-file seconds, so drift is CI against CI (UX-420);
                           refreshed from CI's ci-reference-candidate artifact, never from a
                           local --record - the `verify` skill's §3 has the four steps (UX-447).
                           A file it does not carry is adopted by the default branch's own run,
                           not failed on - `--adopt`, and no commit of yours (UX-503)
tests/touch_map.json       module -> the test files CI measured executing it; adopted by
                           the default branch's own run, never recorded locally (UX-524)
tests/dom_shim.mjs         the one DOM every viewer guard runs on (UX-264)
tests/viewer.mjs           the viewer's exports as one namespace, so a guard names a symbol not a module (UX-337)
tests/cdp.mjs              headless Chrome over CDP, no dependencies (UX-257)
tests/browser.py           what drives it from a test; every geometric claim goes through here
tests/pages.py             the exported page every browser guard measures - the *snapshot* is copied, not the run (UX-359)
tests/trace_processor.py   the one gate for the optional Perfetto reader, and its skip reason (UX-321)
tests/skip_reasons.py      every skip reason as *written*, parsed not grepped - the census reads what fired (UX-449)
tests/installed_command_sweep.py  every documented command, run against an installed wheel (UX-325)
tests/degenerate_store.py  a real store with one row damaged, for both readers (UX-335)
tests/test_e2e.py          the whole pipeline on a committed run · test_golden.py  byte-for-byte
tests/test_cli.py          argument parsing and exit codes, at the CLI boundary
tests/test_synthetic_multi_subproject.py  the multi-project ingestion path
tests/support/             shared helpers · tests/fixtures/  committed run dirs
docs/spec/specification.md v9 spec, ground truth - use line ranges, never read whole file
docs/design/architecture.md  all three planes plus the viewer axis and the contracts
docs/design/directions.md    where the tool is going, argued · roles.md  who it answers to
docs/backlog/scenarios/README.md   active backlog index - start here
docs/backlog/scenarios/closed.md   every closed row, verbatim
docs/backlog/progress-tracker.md   closed spec-compliance backlog - archaeology only
CLAUDE.md                  the day-one page, loaded every session; this guide is the rule
```

## 6a. Which kind of session is this?

Eight streams run in this repository, and they do not start the same way.
`§1`'s "pick the highest-priority 🔴 row" is right for two of them and
wrong for the rest — an audit has no row until it has been done.

| stream | starts from | produces | done when |
|---|---|---|---|
| **design** | a question about where the tool should go | an argued section in `docs/design/directions.md` + filings | the argument names who it serves (`UX-231`) and what it declines |
| **audit** | a landed range, or external feedback | a round document in `docs/audits/` + filings | every claim it makes is a pasted measurement |
| **feature** | a 🔴 row whose Depends on is clear | code + guards + an Outcome section | §3, in full |
| **fix** | a defect, from CI or a report | the failing case first, then the fix | the case that reproduced it is a committed guard |
| **documentation** | a doc that is wrong, or a gap filed per `§3.11` | the correction, in the same register | the guard that would have caught it exists, or its absence is stated |
| **refactor** | a measured cost — size, duplication, a budget | the change, plus before/after | the measurement moved, and no behaviour did |
| **review** | the diff since the last row in [`architecture-review.md`](../audits/architecture-review.md) | filings, and that document's next row | every checklist item is answered with a measurement or a filing (`UX-241`) |
| **release** | a contract that moved, and a review at or after the last release | a row in [`CHANGELOG.md`](../../CHANGELOG.md), a derived version, a tag | the derivation guard is green and the head names what a consumer must do (`UX-251`) |

Two rules cut across all eight:

- **A stream's output is another stream's input.** Design and audit
  produce filings and no code; feature and fix consume them. If a
  session finds itself doing both, it is two sessions.
- **The verification discipline (§3) does not vary by stream.** An
  audit's measurements are pasted like a feature's acceptance test;
  a refactor's before/after is a measurement like any other.

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
