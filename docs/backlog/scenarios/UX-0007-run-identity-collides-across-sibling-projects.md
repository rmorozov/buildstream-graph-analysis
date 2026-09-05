# UX-07: `run_identity.manifest_hash` collides for two different projects in the same git repo

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** none | **Topic:** capture | **Area:** tools

## Motivation

Found while using `bga compare` for real on UX-05's baseline vs. `optimized/` example projects (`examples/04-critical-path-optimization` and `examples/04-critical-path-optimization/optimized` - two genuinely different BuildStream projects, different `elements/`, different element counts, living as sibling directories inside the same git repository/commit). Both runs' extracted `run-context.json` reported the **exact same** `run_identity.manifest_hash`:

```text
run-baseline-b4:  "manifest_hash": "eed010f3be8749d7e2039035a2e627476dfb1b392a647329b5ace0c11f777c2f"
run-optimized-b4: "manifest_hash": "eed010f3be8749d7e2039035a2e627476dfb1b392a647329b5ace0c11f777c2f"
```

`bga compare`'s own report even prints an identical `Run:`/candidate identifier for what are, by inspection (`elements/` differ - 10 vs 9 elements, `base-config.bst`+`base-generate.bst` vs a merged `base.bst`), unambiguously two different builds.

Root cause: `_compute_run_identity` (`tools/bst_extract_run.py:90-121`) builds its manifest from only `targets`, `scheduler` (builders/fetchers/pushers), `project_git_commit`, and `project_refs_sha256`:

```python
manifest = {
    "targets": sorted(targets),
    "scheduler": {...},
    "project_git_commit": _git_commit(project_dir),
    "project_refs_sha256": project_refs_provenance["sha256"] if project_refs_provenance else None,
}
```

Nothing in this manifest identifies *which project* was built - only the git commit of whatever repo the project directory happens to live in, plus the target name (`"all.bst"` in both projects here, by this example's own deliberate design - a very ordinary target-naming convention, not a contrived edge case). Two different BuildStream projects checked out under the same git commit (a monorepo with multiple projects, or exactly this case - a baseline project and an `optimized/` variant living side by side) with the same target name and the same scheduler flags produce an identical `manifest_hash`, defeating I8's own stated purpose ("all analysis inputs must belong to the same run identity") - the hash cannot actually distinguish these two runs' identities.

## Required Fix (deferred - touches a widely-referenced field, not attempted here)

Add something that identifies the *project itself* to the manifest - e.g. the project directory's own path (relative to the git repo root, so it's still comparable across clones) and/or a content hash of `project.conf` + the resolved element set (`graph.json`'s own element list is already computed at this point and would work well here, since it's already keyed by real, resolved BuildStream state). Then re-verify `manifest_hash` no longer collides for this exact repro case.

Marked as needing real design work, not a one-line change, because `run_identity`/`manifest_hash` is referenced across ~20 files in the repo (analyzer, validation gates, multiple test fixtures with hardcoded golden values, `docs/backlog/tasks/P1-37-run-identity-not-captured-or-enforced.md`, `docs/spec/ingestion-pipeline.md`) - changing the manifest's shape needs those all re-checked, not just the one function.

## Out of Scope

- Re-auditing every existing caller/fixture referencing `manifest_hash` in this pass - flagged here, not fixed.
- Deciding the exact new manifest field(s) - path vs. content-hash vs. both is a real design choice for whoever picks this up, not decided here.

## Fix Implemented

Took the path-based option this doc's own Required Fix section named first. New `_project_identity(project_dir)` in `tools/bst_extract_run.py`: prefers `project_dir`'s path relative to its git repository's own root (`git rev-parse --show-toplevel`) - stable across different clones/checkouts of the same repo, unlike an absolute filesystem path - falling back to the resolved absolute path when `project_dir` isn't inside a git repository at all (matching `_git_commit`'s own existing None-for-non-repo behavior). `_compute_run_identity`'s manifest now includes `"project_identity": _project_identity(project_dir)` alongside the existing fields - the exact real repro case (two sibling directories under the same git commit, same target name, same scheduler flags) now differs on `project_identity` alone, so `manifest_hash` no longer collides.

Checked every existing caller/fixture referencing `manifest_hash`/`run_identity` per this doc's own Out-of-Scope note (not skipped, just confirmed safe rather than re-designed): `bga`'s own consumers (`bga/analyzer.py`, `bga/validation/invariants.py`, `bga/ingest/loader.py`/`models.py`) only ever cross-check hash *equality* across the three files - never depend on the manifest's internal shape or a specific literal hash value - so adding a field is a safe, non-breaking addition on that side. `tests/unit/test_run_identity.py` uses opaque placeholder hash strings (`"abc123"` etc.), not real computed values, so it's unaffected. `tests/unit/test_bst_extract_run.py`'s existing `_compute_run_identity` unit tests only assert hash *equality/inequality* between calls, never a literal hash value - no golden/hardcoded hash found anywhere in the test suite.

## Acceptance Test

1. Two different BuildStream projects (different `elements/`) under the same git commit, same target name, same scheduler flags, extracted via `tools/bst_extract_run.py`, produce **different** `run_identity.manifest_hash` values.
2. `bga compare` on those two runs prints visibly distinct `Run:`/candidate identifiers.
3. All existing tests referencing `manifest_hash` (`tests/unit/test_run_identity.py`, `tests/unit/test_bst_extract_run.py`, golden fixtures) updated and green.
4. Full suite green.

## Verification Log

Real reproduction evidence gathered 2026-08-15 via `examples/04-critical-path-optimization` (baseline) vs. `examples/04-critical-path-optimization/optimized`, both built for real with BuildStream 2.7.0, extracted with `tools/bst_extract_run.py --format wrapped`, `run-context.json`'s `run_identity.manifest_hash` compared directly (see Motivation above for the exact values). Not yet fixed - filed as backlog per this session's scope (UX-05's real optimization-walkthrough experiment).

Fixed and re-verified for real, 2026-08-16. New unit tests in `tests/unit/test_bst_extract_run.py`: `test_run_identity_changes_with_project_identity_across_sibling_projects` (the exact real repro shape - two sibling directories under one real git commit, confirms `project_git_commit` is identical for both while `manifest_hash` now differs), `test_project_identity_is_relative_to_git_repo_root` (clone-portability), `test_project_identity_falls_back_to_absolute_path_outside_a_git_repo`.

Real end-to-end re-verification against this doc's own cited projects, rebuilt fresh with real BuildStream 2.7.0 (`bst --no-colors build all.bst`) and re-extracted with `tools/bst_extract_run.py --format raw`:

```text
baseline manifest_hash:  d8a3c6a2065248f251bb12dbbbad07ae9786825f90da7d13d940b23afecd5849
optimized manifest_hash: 9d5da997073a4b9eacdba667c7e2dff6313c8ba6a1b50dd44cbb995b3e9276a8
baseline project_identity:  examples/04-critical-path-optimization
optimized project_identity: examples/04-critical-path-optimization/optimized
baseline commit:  8660acbd932b85adc33d7422d64185ffb62c2341
optimized commit: 8660acbd932b85adc33d7422d64185ffb62c2341   <- identical, confirms commit alone still can't distinguish them
COLLISION? False
```

`bga compare /tmp/run-baseline /tmp/run-optimized` now prints two visibly distinct 64-character `Baseline:`/`Candidate:` identifiers (was: an identical pair before this fix).

Full suite green: 517 passed (up from 514 - 3 new tests), same 7 pre-existing environment-only failures as `main` (this environment's `bst` binary can run plain `bst build` for real but not the sandboxed/`bst source track` paths those 7 pre-existing tests need). `make lint` clean.
