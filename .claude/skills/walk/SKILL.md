---
name: walk
description: Run the outsider walk of bga - a stranger follows the guides through snapshot, view and the Perfetto handoff on a capture with every plane, scores what the tool said against an answer key, and returns a fixed-shape report. Use when a round audits the tool's current state, and use before filing a usability finding from memory rather than from a walk.
---

# walk

The rule is the [fixing guide](../../../docs/contributing/fixing-guide.md)
§6a audit stream — every claim a pasted
measurement — and the lesson rounds 45, 63, 64 and 77 paid for:
**feature guards verify what was built; only a walk verifies what was
promised.** A walk is one subagent, one capture, one report of fixed
shape, so the orchestrating session pays for the conclusion and not
the driving. Round 77's control walk cost 336k tokens; the shape
below is what brings the next one under 100k.

## The protocol

1. **Stranger rules.** The walker reads the guides and what the tool
   prints, not the source and not the suite. It records every
   deviation as *command · output · what a stranger concludes*.
2. **One capture, every plane.** The `measure` skill's two-plane
   recipe (`examples/06-macro-micro-optimization` copied out,
   cache-busted, `--trace-opens --trace-spine=on`); run the cycle
   twice — cold, then incremental — because the second run is where
   the empty-population class lives (`UX-388`).
3. **An answer key before the tool speaks.** Example 06 ships
   `optimized/`; diff it first, then score each plane's advice as
   match / partial / miss with the sentence quoted (round 64).
4. **Read the census, drive the difference.** `python3
   tools/dev_page_census.py <export.html>` boots the export once and
   prints the census — classes with counts, sections, rail entries,
   tables with folded cells, drawings and their twins, planes present
   — so a walk reads it rather than re-deriving it by hand. Drive one
   instance per class it names — never every button. Report only
   the classes whose effect differs from their label.
5. **Novelty before filing.** `git grep -l "<section id>"
   docs/backlog/scenarios/` and cite the closed row that touched the
   surface.

## The report, ≤ 80 lines

```text
capture      <stamp> · elements · processes · planes present
answer key   3 lines
per plane    plane | what it said (quoted) | match? | actionable? | gap
page         headline right? · the macro findable? · N controls in M classes, K differ from label
perfetto     N canned queries answered · what it added that no surface had
findings     numbered, each: surface · evidence (command + snippet) · code site · nearest closed row
friction     what cost the walker the most (the line the ledger keeps — see the design-review skill's §Ledger)
```

Anything longer is a transcript, and the transcript stays with the
walker.

## What it is not

Not a design review (the `design-review` skill judges look and feel
on screenshots), not a growth audit (the `measure` skill's scale run
and a store of N copies), not a falsification pass (`falsify`).
