# UX-1366: shared-source findings separate build tools, and a flag on every element is not printed

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R3 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** tests/unit/test_a_build_tool_source_reach_is_expected.py, tests/unit/test_a_flag_on_every_element_is_said_once.py

## Motivation

On fdsdk, analyze advises narrowing `autoconf-2.73.tar.xz` because a change "rebuilds 108 of 126 elements": a build-tool bump should rebuild its consumers. And `overlap_exceeds_granted_width` fires on every traced element with `requested_jobs: 1`, though the build ran `--max-jobs 4`.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Sources whose elements are build tools to the rest of the graph are reported as expected reach, not as a defect; a native finding present on every element is summarised once, and `requested_jobs` reads the run's max-jobs.

## Out of Scope

Classifying tools by name lists.

## Acceptance Test

On the fdsdk capture neither line prints as a defect. Mutation: revert either; its guard reds.

## Decision

(a) `sources.build_only_elements(graph.dependencies)` is every element whose dependents all take it as `build`; a `resource_blast` row is `build_tool` when all its direct elements are in it. `monorepo_headline`, `keying_clause` and the `shared-source-blast` finding then say "as expected": INFO, `why_none` in place of "Narrow which elements...". No name lists; a `runtime` edge to any dependent makes it a source again.

(b) Why `requested_jobs` read 1: it is `-jN` from `make`/`ninja` argv, highest wins, and BuildStream passes the width as `MAKEFLAGS`, so only autotools' own `make -j1 ... install` carries a `-j`. The trace has `make PREFIX=...` (no `-j`) beside `make -j1 PREFIX=... install`. `plane2.apply_resolved_widths` (where UX-894 already reconciles the argv with `graph.json`) now reads a lone `-j1` on an element granted more as the granted width; `notparallel` elements (width 1) and a `-jN>1` stay as the recipe wrote them. `overlap_exceeds_granted_width` is not derived from `requested_jobs`: it is `peak_work_concurrency > graph width` and still fires (peaks 8-12 against 4); `plane2.run_wide_findings` finds ids every traced element (work processes, scored against a width) carries, and `_plane2_findings` says them once (`native-finding-on-every-element`, INFO). The same ids are dropped from each `element_join` row's `native_findings` (`report/json.py`), so the page's element cards list only what is their own; the finding's `evidence.finding_ids` names them. A `shared-source-blast` row gains `build_tool`, a new column on the page's Shared sources table.

## Outcome (2026-10-30)

Gap measured on the capture at `/home/claude/fdsdk-cap`, before:

```text
$ grep -c overlap_exceeds corr.json          25   (17 elements)
requested_jobs of elements with a granted width: [1, 4, None]
analyze.txt: Shared source: one repository decides most of this build: any commit to ftp_gnu_org/autoconf/autoconf-2.73.tar.xz rebuilds 108 of 126 elements (86%, 5.1 h ...), because its 2 direct elements key on its ref ...
step: Narrow which elements take this source, or key it per element, so a change stops rebuilding the rest.   (MEDIUM)
```

Close, `bga analyze run --plane2 native-report.json` and `bga correlate`:

```text
requested_jobs of elements with a granted width: [4, None]
  17 of 17 traced elements carry `overlap_exceeds_granted_width`
  108 of 126 elements rebuild on any commit to one shared source, as expected of a build tool
    A change to ftp_gnu_org/autoconf/autoconf-2.73.tar.xz rebuilds 108 of 126 elements (86%, 5.1 h of measured build work), as expected: its 2 direct elements are build tools, and their dependents use them through build dependencies only.
```

Side effect, measured: `jobs-waiting` reads "1 elements asked for 4 jobs" before and "6 elements asked for 4 jobs and ran at a median 0.91 cores busy" after, because 14 elements no longer read as `-j1`. Page, `bga view <copy with plane2.json> --reanalyse --export`, dump-dom: both finding titles present, "Narrow which elements" absent.

Gates this touched, not guards of its own: the page's DOM-node budget (`test_the_page_has_a_volume_budget.py`, xl_both 8,086 against 8,085) goes one over because `build_tool` is a table column; reported, not adopted. The three new browser tests need a tier in `tests/tiers.py` (the orchestrator's file).

| mutation | red |
|---|---|
| `build_only_elements` returns `set()` | 3 failed, 1 passed |
| `_shared_source_findings`: `tool = False` | 2 failed, 2 passed |
| `apply_resolved_widths` skips the `-j1` read | 1 failed, 4 passed |
| `run_wide_findings` returns `{}` always | 3 failed, 2 passed |
| `report/json.py` stops dropping run-wide ids from the rows | 1 failed, 5 passed |
