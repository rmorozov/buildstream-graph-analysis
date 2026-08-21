# UX-204: buttons that know why you are going to Perfetto

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-198 (the transport this rides on), UX-194 (the questions it grows), UX-201 (the finding shapes it reads)

## Motivation

The external review's investigation thesis, adopted: the viewer's
job is not to render the timeline but to tell Perfetto **where to
look and why**. Today the button says "Open timeline in Perfetto" —
correct and context-free. The findings, the blast answers and the
per-element rows all know an element uid, a time neighborhood and a
question; none of it travels.

## Required Fix

1. **TraceContext, as a module not a layer**: a small link-builder
   `{element_uid?, reason, query?}` → the handoff invocation — title
   set to the reason (Perfetto shows it), and the matching canned
   query attached. What Perfetto's deep-link API verifiably supports
   is used; what it does not is not faked — the always-works floor is
   "open the trace + put the right query one paste away".
2. **Per-finding investigation buttons**: a finding with elements
   gains `Investigate in Perfetto` carrying its context; blast
   answers and the top rows of element tables the same.
3. **The questions grow into a library**: the five canned queries
   become a categorized page (scheduling / execution / dependencies /
   resources), each with its one-sentence what-it-answers; findings
   reference queries by id so the button and the page cannot drift.
   The exported report inlines the library (UX-199 item 4 does the
   inlining; this item fills it).

## Out of Scope

- Rendering query results in our page (Perfetto's job).
- Any timeline drawing.

## Acceptance Test

The harness: a finding's investigate button produces a handoff whose
title names the finding and whose attached query is the library
entry its id references (mutation: detaching the id linkage
reddens); a run with no timeline renders no investigate buttons
(dead-button rule); the library page lists every query the findings
reference (coverage asserted both directions); queries still parse
under `trace_processor_shell` where installed (the UX-194 marked
test, extended).
