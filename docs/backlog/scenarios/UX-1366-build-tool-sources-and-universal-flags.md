# UX-1366: shared-source findings separate build tools, and a flag on every element is not printed

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R3 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** tests/unit/test_a_build_tool_source_reach_is_expected.py, tests/unit/test_a_flag_on_every_element_is_said_once.py, tests/unit/test_requested_jobs_is_the_observed_request.py

## Motivation

On fdsdk, analyze advises narrowing `autoconf-2.73.tar.xz` because a change "rebuilds 108 of 126 elements": a build-tool bump should rebuild its consumers. And `overlap_exceeds_granted_width` fires on every traced element with `requested_jobs: 1`, though the build ran `--max-jobs 4`.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

A shared source whose direct elements every dependent takes through build dependencies only is described so (review correction 2: never read as a build tool; the finding keeps its severity and its narrowing step); a native finding present on every element is summarised once. `requested_jobs` stays the observed recipe request (`UX-894`); the resolved width reaches every Plane 2 row the graph can answer for, and `pinned_to_one_job` judges that width, never the argv - with no width, the row says the width is unknown.

## Out of Scope

Classifying tools by name lists. Labelling a tool role from Plane 2 `execve` evidence (dependents' sandboxes running binaries the element staged): the hook folds `/proc/self/exe` into the read set (`UX-1360`), so a published report cannot tell an exec from an open, and `resource_blast` is built before any Plane 2 join - more than a bounded change; a row of its own.

## Acceptance Test

On the fdsdk capture (`bga analyze run --plane2 native-report.json`, a copy of `/home/claude/fdsdk-cap`) the autoconf blast stays `medium` with its narrowing step and a build-only note, the run-wide flag is said once, `requested_jobs` keeps the argv's 1 beside `resolved_jobs` 4, and only the `notparallel` element is pinned. A `--max-jobs 4` case with a real `make -j1 install` and a `notparallel` element asserts both readings; a shared source over build-only static libraries (`macro_micro`'s `lib-a`..`lib-f`) keeps its severity and step. Mutation: revert any; its guard reds.

## Decision

(a) `sources.build_only_elements(graph.dependencies)` is every element whose dependents all take it as `build`; a `resource_blast` row is `build_tool` when all its direct elements are in it. `monorepo_headline`, `keying_clause` and the `shared-source-blast` finding then say "as expected": INFO, `why_none` in place of "Narrow which elements...". No name lists; a `runtime` edge to any dependent makes it a source again. Superseded by (d).

(b) Why `requested_jobs` read 1: it is `-jN` from `make`/`ninja` argv, highest wins, and BuildStream passes the width as `MAKEFLAGS`, so only autotools' own `make -j1 ... install` carries a `-j`. That is the observed request and stays published (review, below); `resolved_jobs` is the width. `overlap_exceeds_granted_width` is `peak_work_concurrency > graph width` and still fires (peaks 7-12 against 1 and 4); `plane2.run_wide_findings` finds ids every traced element (work processes, scored against a width) carries, and `_plane2_findings` says them once (`native-finding-on-every-element`, INFO). The same ids are dropped from each `element_join` row's `native_findings` (`report/json.py`); the finding's `evidence.finding_ids` names them. A `shared-source-blast` row gains `build_tool`, a new column on the page's Shared sources table.

(c) Review correction (owner): the first close rewrote a lone `-j1` to the granted width, reversing `UX-894`. Reverted. The capture's raw `native-report.json` has `resolved_jobs: null` on all 24 rows by design - the tracer writes it before `graph.json` exists and the capture workflow passes no `--run-dir`; `analyze` and `correlate` apply the widths at read time and filled 19. The 5 they missed are not uids: `buildstream-build` (the unresolved bucket), `unknown`, and `libsepol`, `libselinux`, `flit_core` - sandboxes the invocation correlation left ambiguous, tagged by fdsdk's `build-root` override with their `--dir`'s last segment. `libsepol` and `libselinux` kept the tracer's argv pin, and `bootstrap/libsepol.bst` is the graph's one `notparallel` element while `libselinux` is granted 4. `plane2.width_lookup` now answers a non-uid row by the one uid whose basename is `<row>.bst` (none when two share it, never for the buckets); a row still unanswered drops the argv pin for `granted_width_unknown` (`format.js` label, `disclosure` vocabulary). A graph that grants no width at all (pre-`UX-377`, e.g. `tests/fixtures/golden`) leaves the capture's findings as they were: there the argv is the only reading, and `test_publish_the_join.py` holds it.

(d) Review correction 2 (owner): build-only dependents do not identify a build tool - a static library, generated headers or a source bundle has them too, and a monorepo split into static-library elements satisfies it for every direct element, so (a) hid the very blast `shared-source-blast` exists for. BuildStream records no tool role. The row key is now `build_only_reach` (`sources.mark_build_only_reach`, unpublished on main, so no schema bump); the finding is `medium` with "Narrow which elements..." whatever it reads, the evidence carries `build_only_reach`, and `monorepo_headline` and `keying_clause` add one neutral sentence, `BUILD_ONLY_NOTE`. No "as expected", no "build tool".

## Outcome (2026-10-30, reworked 2026-10-31)

Gap measured on a copy of `/home/claude/fdsdk-cap` (freedesktop-sdk cold, `--max-jobs 4`), before: `50120b532`; after: this commit. `measure.py` applies `apply_resolved_widths(report, resolved_widths("run/graph.json"))` to `native-report.json` and counts `per_element_parallelism`:

```text
raw native-report.json: rows 24, resolved_jobs filled 0, pinned_to_one_job 16
before: resolved_jobs filled 19, pinned_to_one_job 2 ['libsepol', 'libselinux']
  bootstrap/gcc.bst: requested_jobs 4 resolved_jobs 4      <- the -j1 rewrite
  libselinux: requested_jobs 1 resolved_jobs None peak 8 findings ['pinned_to_one_job']
after:  resolved_jobs filled 21, pinned_to_one_job 1 ['libsepol']
  bootstrap/gcc.bst: requested_jobs 1 resolved_jobs 4 peak 8 findings ['overlap_exceeds_granted_width']
  libsepol: requested_jobs 1 resolved_jobs 1 peak 7 findings ['pinned_to_one_job', 'overlap_exceeds_granted_width']
  libselinux: requested_jobs 1 resolved_jobs 4 peak 8 findings ['overlap_exceeds_granted_width']
```

`bga analyze run --plane2 native-report.json`, before -> after:

```text
-> libsepol, libselinux asked its native build for -j1 ...   ->   -> libsepol asked its native build for -j1 ...
6 elements asked for 4 jobs ... median 0.91 cores busy       ->   1 elements asked for 4 jobs ... median 0.62 cores busy
17 of 17 traced elements carry `overlap_exceeds_granted_width` -> 19 of 19 traced elements carry ...
element_join: resolved_jobs on 19 rows, requested_jobs of granted rows [4, None] -> 21 rows, [1, 4, None]
```

`jobs-waiting` returns to its pre-UX-1366 reading because it counts `requested_jobs > 1`. Shared sources read `... as expected of a build tool` (info) until review correction 2, below.

Gates this touched, not guards of its own: the page's DOM-node budget (`test_the_page_has_a_volume_budget.py`, xl_both 8,086 against 8,085) goes one over because `build_tool` is a table column; reported, not adopted. The new test files need a tier in `tests/tiers.py` (the orchestrator's file).

| mutation | red |
|---|---|
| `build_only_elements` returns `set()` | 3 failed, 1 passed |
| `_shared_source_findings`: `tool = False` | 2 failed, 2 passed |
| `run_wide_findings` returns `{}` always | 3 failed, 2 passed |
| `report/json.py` stops dropping run-wide ids from the rows | 1 failed, 5 passed |
| `apply_resolved_widths` rewrites a lone `-j1` to the width again | 3 failed, 7 passed (`test_a_real_j1_install_step_stays_one_at_a_granted_four`, `test_the_granted_width_is_resolved_jobs_and_never_rewrites_the_request`) |
| `resolved_widths` ignores `notparallel` | 2 failed, 2 passed (`test_a_notparallel_element_resolves_to_one_and_is_pinned`) |
| `width_lookup` answers no basename | 1 failed, 3 passed (`test_a_build_root_tag_finds_its_elements_width`) |
| a row with no width keeps the argv pin | 1 failed, 3 passed (`test_a_tag_no_one_uid_answers_says_the_width_is_unknown`) |
| a basename two uids share answers | 1 failed, 3 passed (same) |
| the `unknown` bucket answers by basename | 1 failed, 3 passed (same) |
| the width-unknown branch runs only when the graph grants no width | 2 failed, 20 passed (`test_the_published_rows_are_the_joins_own_rows` and the unknown test) |

**Review correction 2** (owner: build-only dependents are no tool role). `macro_micro`'s six static libraries `lib-a`..`lib-f` sharing one ref-keyed repository, `_shared_source_findings` on `217550fb1` -> this commit:

```text
{'build_tool': True} info | 8 of 11 elements rebuild on any commit to one shared source, as expected of a build tool | {'why_none': ...}
{'build_only_reach': True} medium | 8 of 11 elements rebuild on any commit to one shared source | {'text': 'Narrow which elements ...'}
```

The same copy of `/home/claude/fdsdk-cap`, `bga analyze run --plane2 native-report.json --format json`, before -> after:

```text
info   | 108 of 126 elements rebuild on any commit to one shared source, as expected of a build tool
medium | 108 of 126 elements rebuild on any commit to one shared source
  step: Narrow which elements take this source, or key it per element, so a change stops rebuilding the rest.
  detail ends: Every dependent of its direct elements takes them through build dependencies only.
  evidence: build_only_reach True (direct_count 2)
```

| mutation (`test_a_build_tool_source_reach_is_expected.py`, 6 tests) | red |
|---|---|
| build-only reach downgrades to INFO | 2 failed, 4 passed |
| build-only reach drops the narrowing step for `_none` | 3 failed, 3 passed |
| the title says "as expected of a build tool" again | 2 failed, 4 passed (monorepo, page) |
| the headline says "as expected of a build tool" again | 2 failed, 4 passed (monorepo, page) |
| the headline drops the note | 2 failed, 4 passed |
| `build_only_elements` returns `set()` | 2 failed, 4 passed |
| a runtime edge no longer clears it (`"build" in types`) | 1 failed, 5 passed (`test_a_runtime_dependent_clears_the_note`) |

That last one first stayed green: the fixture turned every edge of a runtime predecessor into `runtime`, so `"build" in types` agreed; one runtime edge beside build ones now discriminates. The guard file keeps its name (`tests/tiers.py` lists it).
