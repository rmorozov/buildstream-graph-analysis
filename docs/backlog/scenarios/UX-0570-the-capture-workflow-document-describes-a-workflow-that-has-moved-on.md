# UX-570: the capture workflow document describes a workflow that has moved on

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-381 (the capture directory contract), UX-516 (the CI owner's page) | **Serves:** the CI owner reading how the weekly capture works | **Topic:** docs

## Motivation

`docs/design/capture-workflow.md` against
`.github/workflows/real-project-capture.yml`:

```text
doc L93    "Warm. bst build <target>"          yml L351: bst … artifact pull --deps all "$TARGET"
                                               (yml L332-341: bst build "finished in 7 seconds", replaced)
doc L152   "weekly … and workflow_dispatch, and on nothing else"
                                               yml L163-173: two crons, 0 3 * * 0 and 0 4 1 * * (monthly → cold)
                                               doc L189 itself: "the monthly cron settled it"
doc L298   contents table: 13 files             yml writes 21 under capture/ — 8 absent:
                                               bst-element-logs.tar.gz, capture-outcome.txt, doctor.txt,
                                               bwrap-argv.jsonl, invocations.jsonl, native-trace.head.log,
                                               native-trace.log.omitted, build-traced.log, native-report-traced-only.json
yml ~L741  "Cache health trend across the retained refs" (bga baseline -n 8 + cache-trend)
                                               doc: 0 hits for cache-trend / health
```

The two guards on this document check four phrases and one sentence;
neither reads the workflow's file list or its `schedule:` block —
while `test_capture_ref_patterns.py:17` already parses the yml.

## Required Fix

The doc's steps, trigger sentence and contents table corrected, and a
guard that derives the contents table from
`grep -o "capture/[A-Za-z0-9._-]*"` over the yml and the trigger
sentence from its `schedule:` list — the ref-pattern guard's parser,
reused.

## Out of Scope

- The nine-cut list (doc L127-133) — not re-extracted from the yml
  this round; checked or filed when the guard above lands.

## Acceptance Test

Mutation: add a file to the yml's upload list — the table guard
reds; drop a cron — the trigger guard reds.
