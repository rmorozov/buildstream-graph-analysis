---
name: walk
description: Run the outsider walk of bga - a stranger follows the guides through snapshot, view and the Perfetto handoff on a capture with every plane, scores what the tool said against an answer key, and returns a fixed-shape report. Use when a round audits the tool's current state, and use before filing a usability finding from memory rather than from a walk.
---

# walk

The rule is the [fixing guide](../../../docs/contributing/fixing-guide.md)
§6a audit stream — every claim a pasted
measurement — and the lesson rounds 45, 63, 64 and 77 paid for:
**feature guards verify what was built; only a walk verifies what was
promised.** A walk is two halves, on two models, and the exploration
is a seeded scenario rather than a memory (`UX-685`): the same seed
reruns the same walk, and every finding it files grows the journey's
answer key so the next walk with that seed starts from what is held.

## 0. Seed the scenario

```bash
python3 tools/dev_scenario.py --seed N
```

Draws an area (the backlog's area index, `UX-688`), a reader role
and the `decompose` skill's six input classes, and prints the script
the driving half below follows: the capture recipe, the commands, the
page controls to drive, the report shape to fill in.

## Driving — the reporters' model, ledger target under 100k tokens

Capture, export, census, drive one control per class, diff against
the answer key. Round 77's control walk cost 336k tokens, mostly
re-deriving the page's census by hand; the steps below are what stay
under 100k.

1. **Stranger rules.** The walker reads the guides and what the tool
   prints, not the source and not the suite. It records every
   deviation as *command · output* — the verdict on it is the judging
   half's, not driven here.
2. **One capture, every plane**, per the seed's recipe: the `measure`
   skill's two-plane pattern (cache-busted, `--trace-opens
   --trace-spine=on`) run twice — cold, then incremental — because
   the second run is where the empty-population class lives
   (`UX-388`).
3. **An answer key before the tool speaks.** Example 06 ships
   `optimized/`; diff it first, then score each plane's advice as
   match / partial / miss with the sentence quoted (round 64).
4. **Read the census, drive the difference.** `python3
   tools/dev_page_census.py <export.html>` boots the export once and
   prints the census — classes with counts, sections, rail entries,
   tables with folded cells, drawings and their twins, planes present
   — so a walk reads it rather than re-deriving it by hand. Drive one
   instance per class it names — never every button.
5. **Return the report** in the shape below, raw: quoted output and
   diffs, no conclusion yet. `seed` is the scenario drawn at step 0.

## Judging — the session's own model, ledger target under 50k tokens

Reads the **report** the driving half returned, never the page. For
each recorded deviation: is this the guide's promise (quote the
clause it confirms or contradicts), and what rule follows — a
styleguide/spec line, an existing closed row (`git grep -l "<section
id>" docs/backlog/scenarios/`), or a new one filed now. Every new
finding adds a row to the journey's answer key in the same round
(`tests/unit/test_the_journey_has_an_answer_key.py` gains a planted
case or an assertion) and the report's `rows added` line names it, so
a rerun of the same seed can say the row held.

## The report, ≤ 80 lines

```text
seed         the scenario drawn at step 0
capture      <stamp> · elements · processes · planes present
answer key   3 lines
per plane    plane | what it said (quoted) | match? | actionable? | gap
page         headline right? · the macro findable? · N controls in M classes, K differ from label
perfetto     N canned queries answered · what it added that no surface had
findings     numbered, each: surface · evidence (command + snippet) · code site · nearest closed row
rows added   the answer-key rows this run added, or "0, N held" on a rerun
friction     what cost the walker the most (the line the ledger keeps — see the design-review skill's §Ledger)
```

Anything longer is a transcript, and the transcript stays with the
walker. A report missing `seed` or `rows added` is not this skill's
shape (`test_a_scenario_is_named_by_its_seed.py`).

## What it is not

Not a design review (the `design-review` skill judges look and feel
on screenshots), not a growth audit (the `measure` skill's scale run
and a store of N copies), not a falsification pass (`falsify`).
