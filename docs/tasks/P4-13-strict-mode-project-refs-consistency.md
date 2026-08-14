# P4-13: `--strict` extraction mode enforcing project-state consistency via `project.refs`

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** `P4-10` (done - `tools/bst_extract_run.py`, whose existing best-effort git-dirty check this hardens)

## Spec Reference
Not spec-mandated - ingestion-tooling correctness/usability, building on the real pipeline `P4-05`/`P4-08`/`P4-09`/`P4-10` established. Relates to `docs/ingestion-pipeline.md`'s "A note on time-of-extraction consistency" section and cold-floor duration matching (Part 15.2), which silently corrupts if `graph.json`'s cache keys don't match what was actually built.

## Background
`tools/bst_extract_run.py` (`P4-10`) already has a best-effort consistency check: it warns (does not fail) if the BuildStream project's git working tree is dirty when graph extraction runs, since a dirty tree is the strongest *generic* signal available that the project state might not match what the analyzed build actually ran against. That check has two real weaknesses, both raised while discussing it:
1. It's whole-tree dirty-or-clean - a genuinely unrelated dirty file (docs, an unrelated element) trips the same warning as a change that actually affects build output, and it's *only* a warning, never a hard failure, even when the user explicitly wants a strict guarantee.
2. It can't detect the case that actually matters most for reproducibility: source refs changing *without* a new commit (e.g. `bst source track` was re-run, updating resolved refs, before anything was committed) - or, symmetrically, extraction running against a *different, later commit* than the one the analyzed build actually used, even with a clean tree at extraction time.

The user proposed a more precise mechanism: BuildStream's own `project.refs` file. Confirmed real and empirically verified against a real BuildStream 2.7.0 install (not assumed):
- A project can set `ref-storage: project.refs` in `project.conf` (the alternative to the default `ref-storage: inline`, where each element's own `.bst` file carries its source refs). Confirmed via BuildStream's own source (`buildstream/_projectrefs.py`'s `ProjectRefStorage` class: `INLINE = "inline"` vs `PROJECT_REFS = "project.refs"`).
- When enabled, BuildStream centralizes *every* trackable element's resolved source ref (e.g. a git commit SHA) into one YAML file, `project.refs`, at the project root. Confirmed with a real, from-scratch project + a real local git-repo source (`kind: git`, `buildstream-plugins`) + `bst source track`:
  ```yaml
  projects:
    refs-test-project2:
      thing.bst:
      - ref: 9a38a016690ed541621842661aaf890cf556b521
  ```
  (the `ref` value is the exact real git commit SHA of the source repo tracked - not a placeholder).
- This makes `project.refs` (when a project uses it) a single, content-addressable fingerprint of "the exact resolved state of every source in this project" - a strictly more precise signal than "is the git tree dirty" for exactly the question this check needs answered: did the *inputs BuildStream actually resolved and built against* change.
- **Real limitation, confirmed**: `ref-storage: project.refs` is opt-in, not the default (default is `inline`) - and even opted in, only sources with a genuine trackable ref populate it (confirmed: a `kind: local` source in the same test project produced no `project.refs` entry and didn't even create the file, since local sources have no ref concept at all - they're always already resolved). A project using inline ref-storage, or built entirely from non-trackable sources, has no single file this mechanism can hash/compare at all.

## Required Fix
1. Add a `--strict` flag to `tools/bst_extract_run.py`. Required behavior when set:
   - If the project's `project.conf` does not set `ref-storage: project.refs`, **fail loudly** with an actionable message (name the missing config, don't silently degrade to the existing best-effort git-dirty check) - strict mode's whole point is a real guarantee, not "we tried."
   - If `ref-storage: project.refs` is set but `project.refs` itself has uncommitted changes (`git diff --exit-code -- project.refs` against the project's own git history, if it's a git repo) or the project directory isn't a git repo at all, fail loudly - this is a more precise, actionable check than the existing whole-tree dirty check (item 1 in Background), since `project.refs` is specifically the file whose content matters for reproducibility.
   - Without `--strict`, keep today's behavior unchanged (whole-tree dirty warning, non-fatal) - this is additive, not a breaking change to the default flow.
2. Regardless of `--strict`, when `project.refs` exists, embed its content (or a stable hash of it) into the produced run directory as a permanent provenance record - e.g. a new field under `run-context.json` or a sidecar file - so a *later*, independent re-check (not just the one done at extraction time) can detect drift if graph.json is ever re-extracted separately from the original build. Confirm this doesn't collide with any existing run-context/v9 field (Part 32.1) - this is a `bga`-tooling-specific addition, same additive-extension precedent as `element_kind` (`P4-08`) and `dependency_type` (`P4-08`/`P4-11`).
3. Document the real limitation prominently (both in code comments and `docs/ingestion-pipeline.md`): `--strict` is only usable for projects with `ref-storage: project.refs` and at least one trackable-ref source - a project using inline refs or entirely local/non-trackable sources cannot use this mechanism, and `--strict` must say so explicitly rather than silently passing or silently falling back to a weaker check.

## Out of Scope
- Don't try to make `--strict` work for `ref-storage: inline` projects by some other mechanism (e.g. hashing every individual `.bst` file) - that's a materially different, larger design (every element file becomes a comparison target, not one central file) and should be its own task if actually wanted, not folded into this one.
- Don't change the default (non-`--strict`) extraction flow's behavior at all.

## Acceptance Test
1. A real project with `ref-storage: project.refs`, a real trackable (`kind: git`) source, and a clean git tree: `tools/bst_extract_run.py --strict` succeeds.
2. The same project with `project.refs` dirtied (re-run `bst source track` without committing): `tools/bst_extract_run.py --strict` fails loudly, naming `project.refs` specifically, not just "the tree is dirty."
3. A project using the default `ref-storage: inline` (e.g. `tests/fixtures/bst_show_project/`, confirmed to use inline refs): `tools/bst_extract_run.py --strict` fails loudly and explains why (no `project.refs` mechanism available), rather than silently succeeding or silently falling back to the weaker check.
4. Without `--strict`, behavior is unchanged - existing `P4-10` tests continue passing.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
