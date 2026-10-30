# UX-1365: analyze finds the Plane 2 report beside a published capture

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** tests/unit/test_analyze_finds_the_report_beside_a_capture.py

## Motivation

`bga analyze <capture>/run` prints "Plane 2 was not captured for this run" while `native-report.json` sits in the capture's root; a cold reader has to know `bga correlate run native-report.json` exists. The published capture's own `analyze.txt` says the same.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

When a native report exists beside or above the run directory, analyze names it and prints the correlate command instead of "not captured".

## Out of Scope

Merging the two reports.

## Acceptance Test

The fdsdk capture's layout prints the correlate command. Mutation: remove the lookup; the guard reds.

## Decision

`run_store.nearby_native_report` looks for `native-report.json` in the run dir, beside it and one level up. `plane2.absence` returns `NATIVE_REPORT_NOT_ATTACHED` (names the file and the `bga correlate <run> <report>` command) when the store's `plane2.json` is absent but one is found. Terminal, JSON `plane2_absence` and the page read that one sentence; the page's status line (`statusLine`, `bga/viewer/views.js`) shows that sentence instead of "Plane 2 not captured" (the sentence opens "Plane 2 not attached"; the page-size budget leaves 19 B, so the page matches on that opening). Attaching it stays `bga correlate`'s job.

## Outcome (2026-10-30)

Gap measured, `bga analyze /home/claude/fdsdk-cap/run | grep -A1 '^Plane 2:'`, before:

```text
Plane 2:
  Plane 2 was not captured for this run, so there is no per-process detail. `bga snapshot -- bst build TARGET` captures both planes.
```

Close, same command, after:

```text
Plane 2:
  Plane 2 not attached to this run: a report exists at /home/claude/fdsdk-cap/native-report.json; `bga correlate /home/claude/fdsdk-cap/run /home/claude/fdsdk-cap/native-report.json` joins them.
```

Page, `bga view /home/claude/fdsdk-cap/run --reanalyse --export a.html`, headless chromium dump-dom: before "Plane 2 not captured"; after the same sentence as the terminal ("Plane 2 not attached to this run: a report exists at ...; `bga correlate ...` joins them").

| mutation | red |
|---|---|
| `nearby_native_report` joins "nope.json" | 4 failed, 1 passed |
| `statusLine` drops the `joins` branch | 1 failed, 4 passed |
