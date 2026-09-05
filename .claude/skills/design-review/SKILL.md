---
name: design-review
description: Judge the browser report's look, navigation and readability against the styleguide and the reader roles, on screenshots of a page with every plane rendered, and return proposals as styleguide rules with their guard. Use when a round reviews the page's design rather than its data, and use before proposing a layout change from a description of the page rather than a picture of it.
---

# design-review

The law is [`docs/design/styleguide.md`](../../../docs/design/styleguide.md)
— its §1 mapping, §2 drawings, §3 tables and folds, §4 color and
emphasis, §5 dark-first, §6 growth without imports — and the readers
are [`docs/design/roles.md`](../../../docs/design/roles.md). A review
adds rules to the guide and files their implementation; it does not
restyle the page in passing.

## Who runs it

One subagent that can read images, so the pictures never enter the
orchestrating session. It returns text; the screenshots stay in the
scratchpad. The orchestrator passes the model choice on the launch
(see `CLAUDE.md`'s agents line).

## The protocol

1. **A page with every plane.** The `measure` skill's two-plane
   capture, exported and served; the served page has the run picker
   and the store section the export does not.
2. **Seven pictures, fixed.** 1440×900 viewport: landing, header and
   rail, the decision, next steps, one element card, one table with
   folded cells; and the full page. The reviewer describes what a
   first-time reader sees in each *before* measuring.
3. **Measure what the eye does.** Rail entries and depth; entries
   visible without scrolling the rail; whether the rail tracks
   scroll; chars per line and computed font sizes for body, h2,
   cells, badges; computed contrast; nodes per viewport; where the
   first accent sits.
4. **Judge against the guide, then against the craft.** Every
   proposal names the § it extends or contradicts. The craft
   questions, borrowed from platform design guidance and kept as
   questions rather than as brand: does the sidebar read as a
   grouped source list with disclosure and one selection? Is there
   one accent, and does it mean one thing? Does the type scale have
   at most four sizes? Does depth (shadow, layer) mark only what
   floats? Is every control's label its effect?
5. **Controls, one per class.** As the `walk` skill's step 4; report
   only what differs from its label.

## The report, ≤ 140 lines

Per ask: *measured* (numbers, quoted text) → *judged* (the § and the
craft question) → *proposed* (a rule sentence for the guide, the DOM
or CSS shape in a few lines, the guard that would hold it). Then the
broken-controls table and a numbered findings list with the nearest
closed row each.

## Ledger

Every subagent run ends with one line the orchestrator copies into
[`docs/audits/agent-runs.md`](../../../docs/audits/agent-runs.md):
round · agent · model · tokens · wall · what cost the most · what
went wrong. That table is where the process learns what a run
costs; `tools/dev_process_bands.py` reads the Outcomes, this reads
the runs.
