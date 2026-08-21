# UX-187: a report you can read at four thousand elements

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-33 (the always-print rule this revisits), UX-168 (the synthetic scale fixture this renders)

## Motivation

Field feedback: *"let's check that our reports in different formats
are readable enough on long output."* The known unbounded spots, from
past rounds' notes: the critical path prints **in full** (UX-33's
rule, written when paths were ten elements; at thousands it is the
bulk of the report), the Serialized-chains line concatenates every
chain, and several per-element sections have no top-N. The bounded
parts (diagnostics summary at 6, unknown flags at 6, blast table
rows) show the house pattern already exists — it was just never
applied to the oldest sections.

This is an audit-shaped task: render, measure, cap.

## Required Fix

1. **Render every report format** (analyze text, analyze
   `--diagnostics`, compare, correlate, cache-logs, blast) against
   the 1,202-element synthetic run and a real fdsdk capture; record
   per-section line counts in the task's log.
2. **Cap what scrolls**: every list-shaped section gets the top-N +
   "and M more (--full-<section> to print all)" treatment — N chosen
   per section from what a screen holds, the cap stated inline so
   truncation is never silent (the UX-160 lesson). The critical path
   specifically: head and tail with the elision count, full path
   behind the flag and always full in JSON.
3. **JSON stays complete** — caps are a text-rendering concern; the
   machine format never truncates.
4. A guard renders the synthetic run and asserts no section exceeds
   its cap and every elision names its count and its flag.

## Out of Scope

- Pagination/pager integration (`| less` works once stdout is clean;
  owning a pager is scope creep).
- The bounded sections (already right).

## Acceptance Test

On the 1,202-element synthetic run: the full text report fits under a
stated total budget (a few hundred lines, exact number recorded with
provenance), every elided section names its count and flag, each
`--full-*` flag restores its section, and JSON is byte-identical
before and after the caps (mutation: capping JSON reddens it).
