# P4-08: `graph.json` producer from a real BuildStream project (`bst show`)

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** none

## Spec Reference
Part 32.2 (`graph/v9`) defines what `bga` consumes; the spec is silent on how it gets produced from a real BuildStream invocation (deliberately - Part 32 documents the contract, not a producer for it).

## Background
This task was originally filed as ⚪ Blocked - producing `graph.json`/`run-context.json` from a real BuildStream project needed product/architecture decisions (own `bst`-introspection tooling vs. raw YAML parsing vs. log-scraping) this tracker's usual pattern doesn't resolve alone. The user resolved the key decisions directly: build a separate tool (matching the `tools/` convention already used by `P4-05`'s log converter) that calls real BuildStream (`bst show`) rather than parsing `.bst` YAML directly, since real projects reference other projects via junctions and `bst show` already resolves that correctly. See `docs/ingestion-pipeline.md` for the full design record - this file covers only what this specific task built and verified.

Everything below was verified against a **real, installed `bst` binary** (BuildStream 2.7.0 + `buildstream-plugins` + bubblewrap), not assumed from documentation - several assumptions from documentation-only research turned out to be wrong or incomplete once tested for real (see `docs/ingestion-pipeline.md`'s "Empirically confirmed facts" section), most importantly that `--format` *does* have `%{build-deps}`/`%{runtime-deps}` symbols in current BuildStream (missing from an older manpage snapshot that briefly suggested a much more complex per-element-closure-plus-transitive-reduction approach was needed).

## What was built
- `tools/bst_show_to_graph.py`: runs `bst show --deps all --format ...` against a real project and emits `graph/v9` JSON. Uses ASCII record/field separator control characters in the format string (not newline-based parsing) because `%{build-deps}`/`%{runtime-deps}` can themselves contain embedded newlines for a multi-dependency element - confirmed by testing, and a real bug that a naive line-based parser would have shipped with. Collapses a dependency present in both `%{build-deps}` and `%{runtime-deps}` (BuildStream's default "all" type) to a single `dependency_type: "build"` edge. `cache_key` maps to `null`, never a fabricated value, when a source is inconsistent/unresolvable. **Update (2026-08-14):** also captures `%{kind}` (Since: BuildStream 2.6, confirmed against the real 2.7.0 install) as `element_kind` on every `Element` - the user pointed out this symbol exists and could feed future analysis heuristics; wired through `bga/ingest/models.py`/`loader.py` as inert metadata for now, no analysis consumer reads it yet - see `P4-12`.
- `tests/fixtures/bst_show_project/`: a small, deliberately-valid, `kind: local`-only (no network needed) BuildStream project checked into the repo - exercises a multi-build-dependency element, a runtime-only dependency, and a junction (all three of the things that mattered most while designing the parser) in one small fixture.
- `tests/unit/test_bst_show_to_graph.py`: pure-parser unit tests (always run, hermetic) plus real end-to-end tests against the fixture project via an actual `bst` invocation, `@pytest.mark.skipif`-guarded on `bst` being on `PATH` so the main suite doesn't require BuildStream+bubblewrap installed.
- `pyproject.toml`: new `bst` optional extra (`buildstream>=2.0`) separate from `dev`, since it's a heavy, non-pip-only dependency (needs the `bwrap` system binary too) most contributors don't need.
- `docs/ingestion-pipeline.md`: the full design record - read this before touching `P4-09`/`P4-10`.

## Out of Scope (now split into follow-on tasks, per this task's own original scoping note)
- `run-context.json` production (resource capacities, wall clock, max_jobs) - filed as `P4-09`.
- Wiring this together with `P4-05`'s trace-side converter into one convenience command, and deriving the target list from a real invocation rather than a hardcoded convention - filed as `P4-10`.
- Making `dependency_type` actually affect analysis (ready-time gating, structural signals) - `bga`'s consumers still treat every edge identically regardless of type, confirmed by grep; documented in `docs/ingestion-pipeline.md` as real follow-on work, not yet filed as its own task (do that once `P4-09`/`P4-10` land and there's real typed input to test against).

## Acceptance Test
`PYTHONPATH=. python3 -m pytest tests/unit/test_bst_show_to_graph.py -v` - parser tests always pass; the two real end-to-end tests pass when `bst` is installed (`pip install -e ".[bst]"` + `apt install bubblewrap`), skip cleanly otherwise.

## Verification Log
```
$ pip install buildstream buildstream-plugins   # in an isolated venv
$ apt-get install -y bubblewrap
$ bst --version
2.7.0

# Real end-to-end run against tests/fixtures/bst_show_project/:
$ PYTHONPATH=. python3 tools/bst_show_to_graph.py tests/fixtures/bst_show_project app.bst /tmp/graph.json
Wrote graph.json with 4 elements, 3 dependencies to /tmp/graph.json
# base.bst -> app.bst: build; base2.bst -> app.bst: build (multi-dep,
# embedded-newline case); subproj-junction.bst:libfoo.bst -> app.bst:
# runtime (junction + type extraction case) - all correct.

# Confirmed the output loads into bga's own loader with no errors:
$ PYTHONPATH=. python3 -c "from bga.ingest.loader import load_graph; ..."
elements: ['base.bst', 'base2.bst', 'subproj-junction.bst:libfoo.bst', 'app.bst']
deps: [('base.bst', 'app.bst', 'build'), ('base2.bst', 'app.bst', 'build'),
       ('subproj-junction.bst:libfoo.bst', 'app.bst', 'runtime')]

# Confirmed junction-qualified naming matches between `bst show` and a
# real `bst build`'s own log lines (the single highest risk item):
$ bst build app.bst 2>&1 | grep libfoo
[00:00:00][00a7aa29][   build:subproj-junction.bst:libfoo.bst] SUCCESS ...
# identical to bst show's %{name} output for the same element.

$ PYTHONPATH=. python3 -m pytest tests/unit/test_bst_show_to_graph.py -v
12 passed   # with bst on PATH
# 10 passed, 2 skipped   # without bst on PATH (clean skip, confirmed both ways)

$ PYTHONPATH=. python3 -m pytest tests/ -q
253 passed (with bst on PATH) / 251 passed, 2 skipped (without)   # was 241

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```

**2026-08-14 update (`element_kind`):**
```
$ bst -C tests/fixtures/bst_show_project show --format $'%{name}\x1f%{kind}' subproj-junction.bst
subproj-junction.bst<US>junction
# confirmed real %{kind} values: "import" (base.bst/base2.bst/libfoo.bst/app.bst),
# "junction" (subproj-junction.bst)

$ PYTHONPATH=. python3 -m pytest tests/unit/test_bst_show_to_graph.py -v
15 passed   # with bst on PATH (was 12) - 3 new tests for element_kind capture

$ PYTHONPATH=. python3 -m pytest tests/ -q
314 passed (with bst on PATH) / 310 passed, 4 skipped (without)   # was 311/307+4
```
