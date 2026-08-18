# P4-16: Real BuildStream example projects + `bst-examples` CI job (user-proposed)

**Priority:** P4 (usability/tooling/maintenance infrastructure, not spec-mandated) | **Status:** 🟢 Done | **Depends on:** P4-06, P4-13

## Background
User-proposed: before further tool work, enrich CI to build real BuildStream projects on every push/PR, gathering real corner-case data (chrome traces, full `bga` run directories, reports) for future development - real measured data rather than only hand-built fixtures. The user explicitly scoped the CI trigger to match the existing validation-build triggers (no new trigger surface).

## What was built
1. `examples/01-resource-contention/`: eight independent, real multi-second (`sleep 3`) elements, all simultaneously buildable, built with `--builders 2` (smaller than the fan-out) to force genuine `RESOURCE_WAIT`/`SCHEDULER_WAIT` gaps for `P1-31`/`P1-32`'s future work.
2. `examples/02-deep-chain-mixed-kinds/`: a real depth-4 chain across mixed element kinds (`import`/`manual`/`compose`) plus a junction reached through a runtime-only dependency - a real build, not just `bst show`, for `P4-12`.
3. `examples/03-project-refs-identity/`: a real `kind: git`-sourced element under `ref-storage: project.refs`, exercising `tools/bst_extract_run.py --strict`'s real consistency check and generating genuine "touch and rebuild" retry/rebuild data for `P1-37`.
4. `.github/workflows/ci.yml`'s new `bst-smoke` job: a minimal, fast de-risking check (added first, before investing in the full example projects) that real `bst build` actually works under GitHub Actions' `ubuntu-latest` runners.
5. `.github/workflows/ci.yml`'s new `bst-examples` job (`needs: [test, bst-smoke]`, same `push`/`pull_request: [main]` triggers as the existing jobs - no new trigger surface, per the user's explicit constraint): builds all three example projects for real, generates Chrome Trace JSON + full `bga` run directories + JSON/text reports, and uploads everything as a workflow artifact.
6. All sandbox-shell binaries (`/bin/sh` for `manual`/`compose` elements) and the throwaway `kind: git` remote are generated at build time (`examples/stage_runtimes.sh`, `examples/stage_project3_remote.sh`) rather than committed - no binary blobs or nested `.git` directories in the repo.

## Real, unplanned findings along the way
- Bubblewrap's user+mount namespace setup and file staging work fine on GitHub's `ubuntu-latest` runners, but a separate, narrower issue blocks the sandbox's own network namespace: Ubuntu 24.04+'s `apparmor_restrict_unprivileged_userns` sysctl (default 1) withholds `CAP_NET_ADMIN` inside it, breaking bwrap's loopback setup ("bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"). Fixed with the standard `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0` workaround (same root cause as `anthropics/claude-code#14719`).
- BuildStream `stack` elements require every dependency to be both build and runtime (can't mix typed deps) - a real constraint, not documented anywhere in this repo before this task.
- BuildStream project options have no free-form string type (only `bool`/`enum`/`flags`/`element-mask`/`arch`/`os`) - `examples/03`'s per-checkout absolute remote path is templated (`elements/libbar.bst.in` -> `elements/libbar.bst`, gitignored) rather than passed via `--option`.
- The `git` source plugin isn't in the base `buildstream` package (already documented in `docs/spec/ingestion-pipeline.md` #7, but not carried over into this new project's `project.conf`/CI install until a real failure caught it) - fixed via `project.conf`'s `plugins:` block + `pip install buildstream-plugins`.
- **`examples/02-deep-chain-mixed-kinds`'s real build reproduces a genuine, previously-unknown crash**: `bga analyze -d` raises an uncaught `ZeroDivisionError` in `bga/structural/analyzer.py:265`'s `compute_sensitivity` (assumes `slack >= 0`; real slack came out to exactly -1,000,000us). Filed as `P1-38` with full evidence, not fixed here (out of scope for CI wiring) - the `bst-examples` job records `bga analyze` failures (stderr + a `.FAILED` marker in the uploaded artifact) rather than aborting the rest of the job, since a real crash on real data is itself valuable corner-case data, not just a CI-wiring failure.
- `examples/01-resource-contention`'s real build also surfaces a real `Σattribution != H` gap (confirmed via `bga analyze`'s own reconciliation warning) - matches an already-known, already-filed gap (the flattened timeline only covering blame-chain-reachable tasks), now backed by real measured data instead of only a suspected gap.

## Out of Scope
- Fixing any of `P1-31`/`P1-32`/`P4-12`/`P1-37`/`P1-38` themselves - this task is the data-gathering infrastructure those future fixes will use, not the fixes.
- A broader CI trigger surface (schedule, manual dispatch) - deliberately deferred per the user's explicit "minimal required trigger scope" instruction.

## Verification Log
Verified via real GitHub Actions runs on PR #36 (multiple iterations, each fixing a real failure found by the previous run - see the PR's commit history for the individual fixes): `bst-smoke` and `bst-examples` both green, all three example projects build for real, `examples/03`'s `--strict` check demonstrates a genuine PASS (clean, committed `project.refs`) -> FAIL (dirtied, uncommitted) -> PASS (re-committed) sequence, uploaded artifact contains real chrome traces, run directories, and reports for all three projects (32KB, 45 files in the final run).
