# UX-07: `run_identity.manifest_hash` collides for two different projects in the same git repo

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** none

## Motivation

Found while using `bga compare` for real on UX-05's baseline vs. `optimized/` example projects (`examples/04-critical-path-optimization` and `examples/04-critical-path-optimization/optimized` - two genuinely different BuildStream projects, different `elements/`, different element counts, living as sibling directories inside the same git repository/commit). Both runs' extracted `run-context.json` reported the **exact same** `run_identity.manifest_hash`:

```
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

Marked as needing real design work, not a one-line change, because `run_identity`/`manifest_hash` is referenced across ~20 files in the repo (analyzer, validation gates, multiple test fixtures with hardcoded golden values, `docs/tasks/P1-37-run-identity-not-captured-or-enforced.md`, `docs/ingestion-pipeline.md`) - changing the manifest's shape needs those all re-checked, not just the one function.

## Out of Scope

- Re-auditing every existing caller/fixture referencing `manifest_hash` in this pass - flagged here, not fixed.
- Deciding the exact new manifest field(s) - path vs. content-hash vs. both is a real design choice for whoever picks this up, not decided here.

## Acceptance Test

1. Two different BuildStream projects (different `elements/`) under the same git commit, same target name, same scheduler flags, extracted via `tools/bst_extract_run.py`, produce **different** `run_identity.manifest_hash` values.
2. `bga compare` on those two runs prints visibly distinct `Run:`/candidate identifiers.
3. All existing tests referencing `manifest_hash` (`tests/unit/test_run_identity.py`, `tests/unit/test_bst_extract_run.py`, golden fixtures) updated and green.
4. Full suite green.

## Verification Log

Real reproduction evidence gathered 2026-08-15 via `examples/04-critical-path-optimization` (baseline) vs. `examples/04-critical-path-optimization/optimized`, both built for real with BuildStream 2.7.0, extracted with `tools/bst_extract_run.py --format wrapped`, `run-context.json`'s `run_identity.manifest_hash` compared directly (see Motivation above for the exact values). Not yet fixed - filed as backlog per this session's scope (UX-05's real optimization-walkthrough experiment).
