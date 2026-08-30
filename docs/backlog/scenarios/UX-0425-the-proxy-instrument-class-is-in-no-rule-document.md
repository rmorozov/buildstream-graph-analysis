# UX-425: the defect class this repository hits most often is in no rule document

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 67, a backlog-wide sweep run while filing `UX-423` | **Serves:** the next contributor, before they build the instrument rather than after | **Topic:** docs

## Motivation

A sweep of `docs/backlog/scenarios/` (423 files), `tests/`, `tools/`,
`bga/`, `.claude/`, `docs/contributing/`, `docs/design/` and
`docs/audits/` — 22 phrase greps, ~35 files opened,
`git log --all --grep=proxy` over 663 commits — found **about thirty
sightings across about twenty-six items** of one defect: *an instrument
reading a proxy rather than the thing*. Four sub-shapes:

| shape | items |
|---|---|
| a text scan that cannot tell code from data | `UX-340`, `UX-307`, `UX-401`, `UX-327`, `UX-403` |
| a ratio at the noise floor | `UX-420`, `UX-422`, `UX-112`, `UX-342` |
| a comparison across machines | `UX-418`, `UX-421`, `UX-235`, `UX-334` |
| the wrong artifact or the wrong population | `UX-359`, `UX-415`, `UX-287`, `UX-367`, `UX-204`, `UX-296`, `UX-264`, `UX-235`, `UX-277`, `UX-399`, `UX-369`, `UX-278`, `UX-307` |

The repository already **names** it as a class, in four registers:

1. `tests/unit/test_the_tiers_are_a_partition.py` — the canonical
   sentence, listing three sightings in one week;
2. `docs/design/directions.md` — *"a proxy that moves is worth less
   than one that is explained"*;
3. `UX-0287`'s Motivation — *"the number it prints is real; what it is
   a number of is not what the guard's name says"*;
4. `CLAUDE.md`'s recurring-mistake list — two of the four sub-shapes.

**None of those four is a rule document.**

```console
$ grep -rniE "proxy|noise floor|absolute magnitude|reading a proxy" \
      docs/contributing/ .claude/skills/
$ echo $?
0
```

Zero hits across the fixing guide, the style guide and all four skills
(`measure`, `falsify`, `verify`, `derive`). The `measure` skill comes
closest — *"say which half moved"* — and never states the rule. So the
class lives in a test docstring, a design-doc aside, one task file and
the day-one summary, and a contributor reaching for §5's hard rules or
opening the `measure` skill before writing a guard meets none of it.

That is the whole finding. Thirty sightings is not a run of bad luck;
it is the repository's most frequently repeated defect, and it is the
one thing the rules do not mention.

## Required Fix

Put it where a guard's author reads it before writing the guard, not
after CI reddens:

- A clause in the **`measure` skill**, which is the document opened at
  the moment the mistake is made. It should state the class and the
  three questions that catch it: *what quantity does this actually
  read; is it the quantity the name claims; and at the magnitudes it
  will see, can it tell them apart?*
- A rule in **`docs/contributing/fixing-guide.md` §5**, since that is
  where the hard rules live and the two existing `CLAUDE.md` bullets
  are downstream summaries of rules that are not there.
- The four sub-shapes named with **one item each** as the worked
  example, not the whole census — the table above is a finding, and a
  rule with 26 citations is a rule nobody finishes reading.

`CLAUDE.md`'s two bullets then become what they are meant to be:
pointers to a rule, rather than the only statement of it. The page is
under an 80-line guard, so this must not grow it — the bullets already
there should shrink to a reference.

## Out of Scope

- **Closing the census.** The sweep is a lower bound and says so: each
  new grep phrasing turned up items the previous ones had missed, so it
  had not converged. A complete count is not needed to write the rule
  and is not worth the round.
- **The product-level family.** The same shape appears in what `bga`
  reports to a *user* — `UX-036` (occupancy seconds under a CPU label),
  `UX-049` (`mean_width/max_width` is uniformity, not parallelism),
  `UX-069`, `UX-070`, `UX-037`, `UX-173`, `UX-013`. Confirmed to exist,
  not enumerated, and a different document's problem.
- **Re-opening any of the cited items**: `UX-340`, `UX-403`, `UX-420`
  and the rest are closed and their fixes stand. They are evidence
  for the rule, not work to redo.
- **A hook or a guard for it.** This class is a judgement about what a
  measurement means; it is not decidable from a payload. `UX-424` is
  the counter-example — the deterministic control that has the defect
  itself.

## Acceptance Test

- `grep -rniE "proxy|noise floor" docs/contributing/ .claude/skills/`
  returns the new text.
- `tests/unit/test_docs_links_and_commands.py` stays green, and
  `CLAUDE.md` stays under its 80-line bound
  (`test_the_agent_configuration_holds.py::TestClaudeMdIsTrueAndShort`).
- The `measure` skill's new clause names a sub-shape and the item that
  paid for it, so the rule can be re-checked against the record.
