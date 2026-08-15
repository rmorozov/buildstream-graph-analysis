# P1-37: Run identity (I8) has no schema field and isn't enforced by `bga`'s own analyzer

**Priority:** P1 | **Status:** 🟢 Done | **Depends on:** `P4-13` (done - `tools/bst_extract_run.py --strict`/`project_refs_provenance` is real, useful prior art this task extends, not duplicates)

## Spec Reference
I8 - Run Identity: "All analysis inputs must belong to the same run identity" (`docs/specification.md:1795-1797`). Confirmed via grep: the spec states this invariant but defines no concrete field or mechanism for it anywhere in run-context/v9 (Part 32.1), graph/v9 (Part 32.2), or trace/v9 (Part 32.3)'s own schemas - `docs/specification.md` has zero matches for `run_id` at all. The only `run_id` in the codebase is `AnalysisResult.run_id` (`bga/ingest/models.py:269`), populated in `bga/analyzer.py` via `getattr(self.run_context, 'run_id', '') or getattr(self.run_context, 'uuid', '')` - but `RunContext`'s own dataclass has no `run_id`/`uuid` field defined, so this `getattr` always falls through to `''` in practice today.

## Background
Raised by an external review; independently verified against the current code before filing. Two related gaps, filed together since the second can't be meaningfully built without the first:

**1. No real identity is captured anywhere, only post-hoc proxies.** `bga.analyzer.BuildEfficiencyAnalyzer.load()` (`bga/analyzer.py:108`) calls `load_all(run_dir)` (`bga/ingest/loader.py:304`), which reads `run-context.json`/`graph.json`/`trace.json` independently with no cross-check that they describe the same real build. `P4-13`'s `--strict` (real, shipped, useful) hardens a *related but distinct* question - "is the project state clean at extraction time" - not this one. Concretely, `P4-13`'s own task file documents this exact limitation, and the external review's counterexample is real: a build happens from commit A (`project.refs = X`), `project.refs` later changes to `Y` under a new commit B, and extraction runs against a clean commit B - `--strict` passes, but the extracted `graph.json`'s cache keys may not correspond to what the analyzed log's build actually ran against. `--strict` proves "`project.refs` is currently clean relative to git HEAD", not "this exact `project.refs` content existed when the build in this log ran" - a real TOCTOU gap between build time and extraction time that no currently-captured data can close.

**2. Even the identity signals that do exist today aren't cross-checked by `bga` itself.** A user can hand-construct or copy files between run directories (e.g. mixing a `trace.json` from one run with a `graph.json` from another) and `bga analyze` will proceed without any objection, since `load_all`/`load()` never compares any identity-bearing field across the three inputs.

## Required Fix
1. Design a real run-identity mechanism captured **at build/extraction time**, distinct from `P4-13`'s post-hoc cleanliness check: at minimum, a stable hash covering the inputs that determine `graph.json`'s and `trace.json`'s content (e.g. `project.refs` content hash when available, project git commit, BuildStream version, target list, scheduler configuration) - a "run manifest" recorded once at extraction time and embedded consistently across `run-context.json`/`graph.json`/`trace.json` (or a single shared manifest file all three reference), so the identity relationship is checkable, not merely assumed.
2. This is a non-spec, additive extension (the spec defines the invariant, not the mechanism) - same precedent as `element_kind` (`P4-08`), `dependency_type` (`P4-08`/`P4-11`), and `project_refs_provenance` (`P4-13`). Confirm no collision with any existing run-context/v9/graph/v9/trace/v9 field before adding new ones.
3. `bga`'s own `load()`/`load_all()` must validate identity when present: matching identity → proceed normally; identity fields absent (e.g. hand-built or older run directories) → proceed with a clearly reduced-provenance note, not a hard failure (backward compatible); identity fields present but **conflicting** → a violation entry (extending the existing `violations`/confidence machinery, Part 33) at minimum, and consider whether this should be a hard failure under some future `--strict`-equivalent flag for `bga analyze` itself (a separate, `bga`-side strictness knob from `bst_extract_run.py --strict`, which only controls extraction-time behavior).
4. Document plainly, in both code and `docs/ingestion-pipeline.md`, the real limitation this still doesn't solve: without instrumenting the actual `bst build` invocation itself to record its own identity at the moment it runs (not just what a later `bst show`-based extraction observes), a determined mismatch between build time and extraction time can still theoretically evade even this - the goal is closing the practical gap the external review's counterexample demonstrates, not an unfalsifiable guarantee.

## Out of Scope
- Don't fold this into `P4-13` or change `--strict`'s existing, already-shipped, already-useful behavior - this task is complementary (build-time identity capture + analyzer-side enforcement), not a replacement.
- Don't attempt to make `bst_extract_run.py` support "build + extraction as one atomic workflow" (the external review's "even better" suggestion) as part of this task - that's a materially larger scope change to how this tool is invoked (it currently only reads an already-produced log) and should be its own task if pursued, not folded in here.

## Acceptance Test
1. A real run directory produced by `tools/bst_extract_run.py` (updated to embed the new identity fields) round-trips through `bga analyze` with no warnings.
2. A run directory with `trace.json` swapped from a different, unrelated real extraction - `bga analyze` reports a clear identity-conflict violation rather than silently analyzing the mismatched inputs.
3. An older-style or hand-built run directory with no identity fields at all - `bga analyze` still works (backward compatible), with an explicit reduced-provenance note rather than a false-confidence identity claim.
4. Full suite green; no change to any existing invariant-bearing numeric result for inputs that already have consistent (or absent) identity.

## Verification Log
Added a real run-identity mechanism: `tools/bst_extract_run.py::_compute_run_identity` builds a manifest (`targets` sorted, `scheduler` config, `project_git_commit`, `project_refs_sha256`) and hashes it (`manifest_hash`, sha256 of sorted-key JSON), embedding `run_identity` in `run-context.json` and `run_identity_hash` in both `graph.json` and `trace.json`. New optional fields: `RunContext.run_identity`, `Graph.run_identity_hash`, `Trace.run_identity_hash` (`bga/ingest/models.py`), read by `bga/ingest/loader.py`.

`bga/validation/invariants.py::compute_confidence` validates identity across all three inputs: all-present-and-matching → no penalty; all-absent or partially-present → backward-compatible, `provenance_score` capped at 0.75 (reduced-provenance note, not a failure); present-but-conflicting → `provenance_score = 0.0`, a `run_identity_mismatch` violation, and a new `run_identity_consistent` hard gate failure. `AnalysisResult.run_id` now reads the real `run_identity.manifest_hash` instead of a dead `getattr` fallback that always produced `''`.

Documented the real remaining limitation (build-time vs. extraction-time TOCTOU gap - this proves extraction-time consistency across the three files, not that the analyzed build actually ran against the current project state) in `docs/ingestion-pipeline.md`.

`tests/unit/test_run_identity.py` (5 new tests): matching identity → no penalty; missing entirely → backward compatible; partially present → reduced provenance, not a conflict; conflicting → violation + hard gate failure; analysis still proceeds despite the conflict (not a hard crash). Golden/synthetic fixtures updated with consistent `run_identity` so they continue to demonstrate full confidence.

```
$ python3 -m pytest tests/unit/test_run_identity.py tests/unit/test_bst_extract_run.py tests/unit/test_confidence_gates.py tests/test_golden.py tests/test_synthetic_multi_subproject.py -v
33 passed
$ python3 -m pytest -q   # full suite
418 passed, 11 skipped
$ make lint
All checks passed!
```
