# UX-576: the question count is stated three ways

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-469 (the seventeenth question), UX-549 (derived figures) | **Serves:** the reader deciding whether to open Perfetto | **Topic:** docs

## Motivation

```text
bga/viewer/questions.js                       17 question ids
docs/guides/what-the-viewer-answers.md:53     "seventeen" (9 + 8)
docs/guides/what-the-viewer-answers.md:93     "turned the count above from thirteen into sixteen"
docs/guides/cli.md:1504                        "Six of the thirteen canned questions… seven are sharper"
.claude/skills/measure/SKILL.md:117            "fourteen questions"
tools/dev_perfetto_queries.py:13               "fourteen"
```

The boundary guard reads only "serves N questions"; the other four
sentences are unread. `resource-queues` landed on 2026-09-01 and the
prose around the count was written before it.

## Required Fix

One derived count: every sentence that counts the questions is
either derived (`UX-549`'s shape from `questions.js`) or names the
question ids it counts, and a guard reads every "N … questions"
phrase across `docs/` and `.claude/` against the file.

## Out of Scope

- The questions themselves — `UX-368` and `UX-469` own their content; this is the count.

## Acceptance Test

Mutation: add an eighteenth question — every counted sentence reds
or derives.
