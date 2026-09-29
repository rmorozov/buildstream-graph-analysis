# bga quality gates and validation pipelines: audit, 2026-09-29

Scope: every gate a change meets on its way to `main` — the agent's edit hooks, `make lint`,
`make push-check`, `make test`, `.github/workflows/ci.yml`, `quality.yml`, `mutation.yml`,
and the records/adopt machinery. Tree: `main` at `f97f65b` (after #300). Host for local
readings: this 4-core cloud container, Python 3.11. CI readings: GitHub jobs API over the
last 400 `ci.yml` runs (2026-09-07 .. 09-29), medians over the newest 100.

## 0. The one-paragraph answer

The gates are not weak; they are **heavy and unevenly aimed**. A pull request spends a
median **56 minutes** of wall clock and ~78 runner-minutes, of which the one full-suite
run on the PR's interpreter is **11 minutes** (675 s). The rest is mostly (a) the same small tier run three
times, (b) a 22-minute jobserver *experiment* that is not a gate, and (c) waiting on
`test` before the bst jobs may start. Locally, `make lint` costs **~2m50s**, and **96 s of
that is PyMarkdown reading one 729 KB file** (`closed.md`). Meanwhile the checks that
guard the *product's* correctness are thinner than the size of the machinery suggests:
no coverage floor, no property or fuzz tests, a C `LD_PRELOAD` hook built with no
warnings and never under a sanitizer, no shellcheck over 460 lines of bash in YAML, and
pyright only as a ratchet. Roughly half of the 10,572 tests guard the process (docs,
backlog, ledgers, registers, agent config) rather than bga.

Analogy: the factory has three quality inspectors checking that the paperwork of each
shipment is filed correctly, and one inspector who glances at the product. The paperwork
is immaculate. Nobody drops the product on the floor to see if it breaks.

## 1. The principal contradiction

**Process guards grow faster than the product they protect.** In the last two weeks, 1,604
file touches landed under `docs/`, `.claude/`, and the root `*.md`, against 459 under
`bga/` and `tools/` (`git log --since=2026-09-15 --name-only`). The workflow review of
2026-09-23 already measured 87% of new filings as process. Each process incident (a flake,
a register conflict, an adopt commit with no CI) was resolved by *adding a guard*, which
is locally correct and globally the thing that makes the next round slower and the next
conflict likelier. The guards are the negation of the previous failure; nothing yet
negates the guards themselves (a guard never retires).

The resolution is not "fewer guards" but **a budget and a retirement path**: every gate
pays rent in wall-clock and in conflicts, and a gate whose failure class has not fired in
N rounds moves from the per-PR path to a scheduled one (§6, row D1). The next
contradiction this predicts: once guards can retire, someone must own deciding which, and
that judgement competes with product rows for the 40% bookkeeping cap. It belongs to the
weekly `retro`, which already groups bookkeeping.

The secondary contradiction: **instrument vs gate inside CI.** `bst-examples` is described
as "not correctness-gating" (`ci.yml:1336-1343`) yet it runs on every PR, blocks the run
when red, and is the longest job (2,064 s median over the newest 100 runs, against the 620-964s spread the examples-clock ledger still records). Its biggest step, the UX-1004 calibration
(1,332 s median), only emits `::notice::` lines. This is the jobserver
instrument/intervention boundary Ruslan drew for the product (2026-09-20) not yet drawn
for CI.

## 2. Measurements

### 2.1 CI (median seconds, newest 100 runs)

| job | PR | push | note |
|---|---|---|---|
| **run wall** | **3,350** (p90 3,715) | **3,498** (p90 4,035) | queue ≈ 3 s |
| bst-examples | 2,064 | 2,070 | calibrate step 1,332; 11-serial-giant 436 |
| test (3.12) | 1,300 | 1,304 | 3.9/3.10/3.11 on push: 1,372-1,403 |
| bst-tests | 1,134 | 1,149 | re-runs the whole suite (927 s) + `-m bst` 153 s |
| docs-lane | 340 | — | docs-only PR wall 356 s |
| installed-capture | 90 | 92 | runs on docs-only PRs too |
| packaging | 41 | 42 | runs on docs-only PRs too |

`test (3.12)` steps on a PR: full suite 675 s, **small tier single-process 250 s**, **lint
174 s**, **small tier backstop 140 s**, install 13 s.

Critical path on a PR: `changes` 9 → `test` 1,300 → `bst-smoke` 29 → `bst-examples` 2,064.
`bst-tests` and `bst-examples` wait on `test` and use nothing it produces
(`ci.yml:1156, 1218, 1354`).

Failures, 400 runs: 100 failed (25%), 2 cancelled. By step: "small tier, with a
backstop" **129** (the first test step, so mostly real failures), Lint 22, `11-serial-giant` 19, tier-drift gate 14, `tier-reference-adopt`
8, `flake-ledger-adopt` 7. No top-level `concurrency:` / `cancel-in-progress`, so a
superseded push keeps burning its ~55 runner-minutes.

### 2.2 Local (4-core container)

| gate | wall | note |
|---|---|---|
| `make lint-docs` (PyMarkdown, 1,303 files, 10.6 MB) | **154 s** | single process |
| — of which `docs/backlog/scenarios/closed.md` alone (729 KB) | **96 s** | superlinear in file size |
| — same, `xargs -P4 -n80` | 111 s | parallelism barely helps: closed.md dominates |
| `ruff check` | < 1 s | cached |
| `dev_baseline.py --check` (pyright inside) | 14 s | |
| `make push-check` | **166 s, red** | red on a clean `main` (`e88c2773`): the PATH pyright 1.1.408 invents `reportOperatorIssue tools/bst_cache_logs.py`; the lock pins 1.1.414 |
| full suite `-n auto` | **405 s** | 10,372 passed, 200 skipped; 1,468 CPU-s in junit |

Fresh-container readiness: the container this audit ran in was shallow and lacked
`networkx`/`zstandard`; `git fetch --unshallow` 10 s, `pip install -r requirements.lock`
14 s. And `make lint` calls bare `ruff`, which resolved to `/root/.local/bin/ruff`
**0.15.8** while the lock pins **0.16.8**, and bare `pyright` to 1.1.408 against 1.1.414.
The second one is why `push-check` reds on a clean tree here (UX-1113).

### 2.3 Where the tests point (heuristic classification, 679 files, 10,572 tests)

| bucket | files | tests | CI CPU-s |
|---|---|---|---|
| product: `bga/` analysis, report, schemas | 176 | 2,070 | 186 |
| viewer / browser page | 207 | 3,030 | 1,067 |
| capture tools, hook, spine | 148 | 2,040 | 167 |
| process: docs, backlog, ledgers, commits, agent config | 89+ | 2,347+ | 96 |
| dev tooling (`tools/dev_*`, 11,487 lines) | 59 | 1,085 | 313 |

The process bucket is undercounted (ties went to viewer). One file,
`test_the_register_is_terse.py`, is 1,142 tests, 11% of the suite. Process tests are cheap
in seconds; their cost is in **conflicts and rework**, not CPU — 40 of 47 catch-up
conflicts in the 2026-09-23 review were registers.

## 3. Inefficient

1. **The small tier runs three times per PR** (backstop 140 s, inside the full suite, then
   single-process 250 s). The backstop exists to catch a hang (UX-421); `pytest-timeout`
   per test catches a hang and names the test, at zero extra runs. The single-process
   re-run (UX-336, ordering assumptions) is a legitimate check but belongs on push or
   nightly, not every PR. Saving: ~390 s of the 1,300 s job.
2. **`bst-examples`/`bst-tests` wait for `test`.** Dropping `test` from their `needs`
   takes the PR critical path from ~3,400 s to ~2,100 s (estimate from medians; the ledger's `bst-examples` spread, 620-964s, is stale against today's 2,064 s). Cost:
   they run even when `test` is red — acceptable, since `cancel-in-progress` plus a
   fail-fast `if` on `test`'s result can still cancel them.
3. **The UX-1004 calibration (1,332 s) runs on every PR.** It is a measurement, not a
   gate. Move it to `workflow_dispatch` + weekly schedule + a `jobserver` PR label.
   Saving: 22 min off the longest job. With (2), PR wall ≈ 13-15 min for the suite path.
4. **`bst-tests` re-runs the whole suite (927 s)** that `test (3.12)` already ran, to add
   "with bst present". Only the ~24 `mark.bst` files and the skip-gated ones change
   outcome with bst present; run `-m bst` plus the files whose skip reason is "no bst".
5. **Lint runs in every matrix cell** (174-218 s each, 4 cells on push) and again in
   `docs-lane`. One interpreter is enough (the lock pins the tools).
6. **PyMarkdown re-scans 10.6 MB of markdown on every lint**, 62% of it on one append-only
   file. Lint only files changed against the merge-base on `push-check` and in the
   edit loop; keep the full scan in CI once. Or split `closed.md` by year/quarter — it is
   append-only history and the linter's cost is superlinear.
7. **No workflow-level `concurrency: cancel-in-progress` on PRs.** 2 cancels in 400 runs.
8. **No `cache: pip`**, 12 separate dependency installs, 4 `apt-get update`s. Small (10-20 s
   each) but free to fix.
9. **Coverage on 3.11-push is a whole extra suite run (874 s)** used only to build the
   touching map. Collect it in the one run 3.12 already makes, weekly, or on push only
   when `bga/`/`tools/` changed.
10. **Docs-only PRs still run `packaging` and `installed-capture`** (no `changes`
    dependency).

## 4. Insufficient (gap analysis by check type)

| check type | state | gap |
|---|---|---|
| unit / integration / golden | strong | — |
| e2e with real bst | present (bst-smoke/tests/examples) | 11-serial-giant is the flakiest step (19 failures) |
| coverage floor | **collected, never gated** | no `fail_under`; a module can lose all tests silently |
| property-based / fuzz | **absent** | the log parser and schema readers eat untrusted text; `hypothesis` over the parsers is the highest-yield addition |
| type checking | pyright *basic*, baseline ratchet, 274 held findings, `strict = []` | no module is strict; `bga/schemas.py` and `bga/graph/` are the obvious first |
| C hook (`LD_PRELOAD`) | built `cc -shared -fPIC -O2` (`bst_native_build_tracer.py:174`) | no `-Wall -Werror`, no ASan/UBSan run, no clang-tidy/cppcheck; this code runs inside every build process of a user's build |
| shell | **absent** | ~460 lines of bash in `ci.yml` steps, `tools/dev_run.sh`, `native_trace/wrappers/_common.sh`, `examples/*.sh`; no shellcheck |
| JS (viewer, 23 files) | eslint with **2 rules**, only in `quality.yml` | no `recommended` set, no `// @ts-check`, not in `make lint` |
| accessibility | agent walks only | no axe-core run in the Chromium harness that already exists |
| security | CodeQL, pip-audit, ruff S baselined | no secret scan (gitleaks), no dependency-review on PRs |
| cross-platform | ubuntu x86_64 only | aarch64 only via the CodSpeed probe; the tool is meant for agents of several arches |
| CI logic | **untested** | adopt/records/gating logic lives in YAML bash; the 460 lines of `bst-examples` have no test |

Product-code lint findings the current rule set misses (`ruff --select`, `bga/` + `tools/`):
blind `except Exception` BLE001 **7 + 19**; `subprocess.run` without `check=` PLW1510
**3 + 45**; implicit Optional RUF013 0 + 17; mutable class default RUF012 0 + 5; `global`
PLW0603 2 + 5. Small numbers, real bug classes — cheap to add to the baseline families.

## 5. Duplicate

- Lint: every test cell, `docs-lane`, `push-check`, and the edit hook.
- Suite: `test (3.12)` full + `bst-tests` full + 3.11 coverage run on push = three full
  suites per push-to-main commit, plus 3.9/3.10.
- Small tier: three runs per PR (above).
- Size ledger: `push-check` and `quality.yml`'s `sizes` job.
- Custom AST guards that are linter rules in disguise: the 25-line docstring limit (ruff
  `D` + a pydocstyle max isn't available, so this one earns its keep), the size ledger's
  longest-function cell overlaps `PLR0915`/`C901` (already baselined), absolute-import
  bans that `flake8-tidy-imports` (`TID251/252`) expresses as config.

## 6. Linters and suppressions

The suppression picture is **healthy**: 8 `# noqa`, 1 `# type: ignore`, 0 `pyright: ignore`,
and UX-705 already counts every suppression as a finding. The ratchet
(`tests/quality_baseline.json`, 573 findings, identity = rule, file, normalised line
text and nth) is a good design. Problems:

1. **The baseline entries carry no reason.** Only the 25 forced batches name a task. A held
   `S603` in `tools/` and a held `reportOptionalMemberAccess` in `bga/analyzer.py` read the
   same. Add a `reason` (task id or "accepted: <one line>") and make `--check` print
   unreasoned counts.
2. **The baseline burns down only by accident.** 573 held; the pace of closing is nobody's
   row. Top holders: `tools/bst_native_build_tracer.py` 70, `bga/structural/analyzer.py` 61,
   `bga/analyzer.py` 36, `bga/diagnostics/analyzer.py` 36.
3. **No formatter.** `ruff format --check`: 839 of 852 files would change. Adopting one is a
   single mechanical commit plus `.git-blame-ignore-revs`; it removes the whole class of
   whitespace/quote review noise and the W293 (626) class.
4. `tools/**` ignores `T201`, which is not selected (dead config).
5. Local `ruff` resolves to a different version than the lock (§2.2). Call
   `python3 -m ruff` in the Makefile and the edit hook.

### Should bga adopt a style guide?

Yes, but a **thin, executable** one, not a document. Recommendation: **PEP 8 as enforced by
`ruff format`** (Black-compatible) for layout, **Google docstring convention** (`ruff`
`D` with `convention = "google"`, only `D1xx` off) for docstrings, and the repo's own
register rules for tone. The value is not taste; it is that every rule becomes a tool
output instead of a review comment or a custom AST test. Everything else in `REVIEW.md`
and `rules.md` that a tool can check should be a tool; what remains prose should be short.

## 7. Other problems with the gates, and the workflows they shape

1. **A gate with no local twin surprises.** Size ledger, eslint, CodeQL, the tier-drift
   gate and the perf ratchet exist only in CI (or only on 3.12). Every one of them has at
   least once turned a locally-green push red (project memory). `push-check` should run
   the cheap ones (eslint ≈ seconds) and name the rest.
2. **Timing gates in a correctness pipeline.** The tier-drift gate failed 14 runs and the
   adopt jobs 15, none of them a product defect. (The backstop's 129 are mostly *real*
   small-tier failures: it is simply the first step that runs tests.) A timing gate on a
   shared runner is a noise source by construction (UX-421 says so itself). Move timing
   *adoption* and *drift* to a scheduled job that files a row, and keep only a hang
   timeout per PR.
3. **Records written from red runs.** `area-pages-publish` runs with `!cancelled()`, so it
   publishes after a red `test`; carry caches save under `always()`.
4. **Fresh containers are not gate-ready.** Shallow clone and missing locked deps
   (§2.2) — a `SessionStart` hook that runs `git fetch --unshallow` and
   `pip install -r requirements.lock` would stop every thread re-discovering it (project
   memory records it at least three times).
5. **Agent-side gate latency.** `push-check` = lint (~170 s) + selector + sizes + close
   check. For an agent that pushes several times per round, lint-docs alone is the
   dominant term, and it is spent re-reading history files the diff never touched.
6. **A check that is red on every PR.** `github-advanced-security` concluded `failure`
   with no output on #299's and #300's heads, both merged, and on this audit's own PR. A red
   that every merge overrides teaches the reader to override red; it should be fixed or
   removed from the PR's checks.
7. **Fail-open `docs_only`:** `CLAUDE.md`, `REVIEW.md` and `.claude/**/*.md` steer the
   agents and take the docs lane; `agent-config` covers them, which is fine, but a skill
   change that alters what a verifier runs gets no suite run. Acceptable; worth knowing.

### 7a. What #299's `**Guard:**` lines make possible

Read from #299's head (`claude/project-thread-2veul9`): 1,060 task files, every one carries
the line; **395 say `none`**, **457 (43%) are `inferred r149`**; the rest name 471 distinct
test files. **215 of 686 test files (31%) are named by no task.** The most-named guard,
`test_docs_links_and_commands.py`, answers for 35 tasks.

That map is the missing half of row D1. With it, each gate's cost (CI seconds per file,
`tests/ci_reference.json`) sits beside its reason (the task that asked for it), so the
retro can ask of the 215 unnamed files "whose failure is this?", and of a file named by
35 tasks "is this one guard or 35 folded together?". Before retiring anything on the
strength of an `inferred` line, confirm it: 43% of the map is a model's reading of prose.

## 8. Proposed rows

Filed as UX-1108..UX-1117: C1 1108, C2 1109, C3 1110, C4 1111, S1 1112, S3 1113, S4 1114,
D3 1115, G2 1116, G1 1117. The rest are drafts awaiting a pick.

Speed — local:

- **S1** `lint-docs` lints only markdown changed against the merge-base in `push-check`;
  the full scan stays in CI once. Est. −150 s per push.
- **S2** Split `closed.md` into per-quarter files (append-only). Est. full lint-docs
  154 s → ~60 s.
- **S3** Makefile and edit hook call `python3 -m ruff`/`-m pyright`; `dev_env_check`
  names the lock's versions.
- **S4** `SessionStart` hook: unshallow + install the lock.

Speed — CI:

- **C1** Workflow `concurrency: {group: ci-${{ github.ref }}, cancel-in-progress: true}` on PRs.
- **C2** `bst-tests`/`bst-examples` drop `test` from `needs`. Est. PR wall −20 min.
- **C3** UX-1004 calibration off the PR path (dispatch, weekly, `jobserver` label).
  Est. −22 min of the longest job.
- **C4** Replace the small-tier backstop with `pytest-timeout`; move the single-process
  small tier to push-to-main. Est. −390 s per PR.
- **C5** `bst-tests` runs `-m bst` plus bst-skip-gated files, not the whole suite. Est.
  −800 s of runner time per run.
- **C6** Lint on one interpreter; `cache: pip`; one composite action for apt + sysctl.
- **C7** Coverage folded into an existing run (weekly or path-gated), not a fourth suite.

Gaps:

- **G1** `hypothesis` property tests over the scheduler-log parser and the Plane 2 readers.
- **G2** The hook compiled `-Wall -Wextra -Werror` in CI, plus one ASan/UBSan capture of a
  small example.
- **G3** `shellcheck` over `tools/**/*.sh`, `examples/**/*.sh`, and CI `run:` blocks
  (via `actionlint`, which runs shellcheck on them).
- **G4** A coverage floor per package (ratchet, like the baseline), not a global number.
- **G5** eslint `recommended` + `// @ts-check` on the viewer, in `make lint`.
- **G6** Pyright `strict` on `bga/schemas.py` and `bga/graph/`.
- **G7** Add BLE, PLW1510, RUF012/013 to the baselined families.
- **G8** axe-core in the existing Chromium harness on the golden page.

Lint/style:

- **L1** Adopt `ruff format` in one mechanical commit + `.git-blame-ignore-revs`.
- **L2** Google docstring convention via ruff `D`.
- **L3** Baseline entries carry a reason; `--check` prints the unreasoned count.

Process:

- **D1** A guard budget and retirement rule: each per-PR gate records its last true
  catch; one not fired in N rounds moves to the scheduled lane. Owned by `retro`, built on
  #299's `**Guard:**` map (§7a): cost per file joined to the tasks that name it.
- **D2** Timing gates (tier drift, perf ratchet) move from per-PR red to a scheduled job
  that files a row.
- **D3** `area-pages-publish` gated on `needs.test.result == 'success'`.
- **D4** Extract the `bst-examples` bash into `tools/ci/*.sh` so it can be shellchecked and
  unit-tested.

Suggested first batch (fastest payback, no product risk): **C1, C2, C3, C4, S1, S3, S4,
D3**. Together they take a PR from ~56 min to an estimated ~15-20 min wall and a push
from ~3 min of local lint to under 30 s. G2 and G1 are the highest-value product-safety
additions.
