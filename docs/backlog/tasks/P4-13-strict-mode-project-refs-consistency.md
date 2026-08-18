# P4-13: `--strict` extraction mode enforcing project-state consistency via `project.refs`

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** `P4-10` (done - `tools/bst_extract_run.py`, whose existing best-effort git-dirty check this hardens)

## Spec Reference
Not spec-mandated - ingestion-tooling correctness/usability, building on the real pipeline `P4-05`/`P4-08`/`P4-09`/`P4-10` established. Relates to `docs/spec/ingestion-pipeline.md`'s "A note on time-of-extraction consistency" section and cold-floor duration matching (Part 15.2), which silently corrupts if `graph.json`'s cache keys don't match what was actually built.

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
3. Document the real limitation prominently (both in code comments and `docs/spec/ingestion-pipeline.md`): `--strict` is only usable for projects with `ref-storage: project.refs` and at least one trackable-ref source - a project using inline refs or entirely local/non-trackable sources cannot use this mechanism, and `--strict` must say so explicitly rather than silently passing or silently falling back to a weaker check.

## Out of Scope
- Don't try to make `--strict` work for `ref-storage: inline` projects by some other mechanism (e.g. hashing every individual `.bst` file) - that's a materially different, larger design (every element file becomes a comparison target, not one central file) and should be its own task if actually wanted, not folded into this one.
- Don't change the default (non-`--strict`) extraction flow's behavior at all.

## Acceptance Test
1. A real project with `ref-storage: project.refs`, a real trackable (`kind: git`) source, and a clean git tree: `tools/bst_extract_run.py --strict` succeeds.
2. The same project with `project.refs` dirtied (re-run `bst source track` without committing): `tools/bst_extract_run.py --strict` fails loudly, naming `project.refs` specifically, not just "the tree is dirty."
3. A project using the default `ref-storage: inline` (e.g. `tests/fixtures/bst_show_project/`, confirmed to use inline refs): `tools/bst_extract_run.py --strict` fails loudly and explains why (no `project.refs` mechanism available), rather than silently succeeding or silently falling back to the weaker check.
4. Without `--strict`, behavior is unchanged - existing `P4-10` tests continue passing.

## What was built
`tools/bst_extract_run.py` gained:
- `_read_ref_storage(project_dir)`: reads `project.conf`'s `ref-storage` key directly via a minimal, direct YAML read (`inline` when absent, BuildStream's own default) - deliberately not queried through `bst` itself, since there's no `bst show`-style per-project-config query the way there is for element fields. Documented, real limitation: this reads the literal top-level key, not a variable-substituted/conditional one - not observed in practice, but named plainly rather than silently assumed.
- `_check_project_refs_strict(project_dir)`: the real `--strict` gate - fails loudly (never silently degrades) unless `ref-storage: project.refs` is set, `project.refs` actually exists (a project with the right `ref-storage` but zero trackable-ref sources never gets one created - confirmed real, same finding as this task's original research), the project is a git repository, and `project.refs` itself has no uncommitted changes relative to git HEAD (`git diff --exit-code -- project.refs` - a precise, single-file check, not the whole-tree one).
- `--strict` CLI flag, wired through `extract_run(strict=...)`. Without it, behavior is completely unchanged (confirmed - see Verification Log).
- Provenance embedding (Required Fix item 2), unconditional on `--strict`: whenever `project.refs` exists, its SHA-256 is embedded into `run-context.json`'s new `project_refs_provenance` field (`{"path": "project.refs", "sha256": "..."}`) - additive, confirmed no collision with run-context/v9's spec-mandated schema (Part 32.1), same precedent as `element_kind`/`dependency_type`.
- Added `pyyaml>=6.0` to `pyproject.toml`'s `bst` extra (the only place `--strict`'s YAML read is needed).
- Documented the real limitation prominently in both code (each function's own docstring) and `docs/spec/ingestion-pipeline.md`'s "A note on time-of-extraction consistency" section.

Real bug found and fixed while verifying against an actual non-git directory: `git diff --exit-code`'s exit code for "not a repository at all" is **129** (a usage error), not the **128** `git status --porcelain` returns for the same case (which `_git_consistency_note` already relies on) - conflating them would have misreported "not a git repo" as "has uncommitted changes." Fixed by checking repo-ness with `git status --porcelain` first (matching the already-verified existing check), then running the `project.refs`-specific diff only once confirmed to be inside a real repo.

## Verification Log
All 4 acceptance-test scenarios verified against a real, freshly-installed BuildStream 2.7.0 + `buildstream-plugins` (needed for a real `kind: git` trackable source):

**1. Clean `ref-storage: project.refs` project - succeeds:**
```
$ python3 -m tools.bst_extract_run project build.log rundir1 --bst-bin bst --strict
Wrote run directory to rundir1 - targets=['thing.bst'], 1 elements, 0 dependencies, 2 spans
$ echo $?
0
$ python3 -c "import json; print(json.load(open('rundir1/run-context.json'))['project_refs_provenance'])"
{'path': 'project.refs', 'sha256': 'c26f87c67c46e2eec92d1f4cc81ce229f4516b90725ac8f906372e9fce25418f'}
```

**2. `project.refs` dirtied (re-tracked against a new upstream commit, not committed) - fails loudly, naming `project.refs`:**
```
$ git status --short
 M project.refs
$ python3 -m tools.bst_extract_run project build.log rundir2 --bst-bin bst --strict
Error: --strict: /tmp/.../project/project.refs has uncommitted changes relative to git HEAD - the
resolved source state this file records may not match what the analyzed build actually ran
against. Commit project.refs (after confirming it reflects the build being analyzed) before
extracting with --strict.
$ echo $?
1
```

**3. `tests/fixtures/bst_show_project/` (confirmed `ref-storage: inline`, the default) - fails loudly, explaining why:**
```
$ python3 -m tools.bst_extract_run tests/fixtures/bst_show_project build.log rundir --bst-bin bst --strict
Error: --strict requires ref-storage: project.refs in tests/fixtures/bst_show_project/project.conf
(found: 'inline') - a project using the default inline ref-storage has no single file this
mechanism can hash/compare, so --strict cannot provide a real guarantee for it.
$ echo $?
1
```

**4. Without `--strict` - behavior unchanged (same dirty project, default flow still just warns):**
```
$ python3 -m tools.bst_extract_run project build.log rundir2b --bst-bin bst
Wrote run directory to rundir2b - targets=['thing.bst'], 1 elements, 0 dependencies, 2 spans
Warning: project directory '.../project' has uncommitted changes - ...
$ echo $?
0
```

Added `tests/unit/test_bst_extract_run_strict.py` (12 tests): 9 hermetic unit tests against `_read_ref_storage`/`_check_project_refs_strict` (including the not-a-git-repo exit-code regression and an explicit check that an *unrelated* dirty file doesn't trip `--strict`), 2 real `bst`-gated tests against the inline-storage fixture (fails loudly; default flow has no `project_refs_provenance` key), and 1 real `bst` + `buildstream-plugins`-gated test running the full real lifecycle (clean succeeds with a real provenance hash, then dirtying `project.refs` fails loudly) - all 12 passed for real with both `bst` and `buildstream-plugins` available.

Full suite: 399 passed with `bst` + `buildstream-plugins` available (388 passed + 11 skipped without `bst` on `PATH`) - was 387/379+8 at the start of this task. `make lint` clean, `make check-clean` OK.
