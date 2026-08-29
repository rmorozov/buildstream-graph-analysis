# UX-417: the guide's export figures are stale by 3.2x

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** architecture review 7, checklist item 3 | **Serves:** anyone deciding whether to attach a report | **Topic:** docs

## Motivation

Checklist item 3 — *is any figure invalidated?* — against
`docs/guides/cli.md`'s `--export` section:

```text
Measured on `examples/06`'s real 46 s two-plane capture: **158 KiB**,
of which the page is 90,611 B.
```

Re-measured on a fresh 28 s two-plane capture of the same project,
round 64:

```text
example 06 cold export: total=518,578 B (506 KiB)
  source (modules+css) = 282,247 B
  contract (schemas)   =  81,681 B
  data (payload+trace) = 154,650 B
```

**3.2x the total, and 3.1x the page.** The guide's sentence then draws
a conclusion from its own numbers — "on a small project the page is
the larger half" — which is still true but for a different reason, and
the paragraph beside it quotes a round-21 synthetic figure (638 KiB,
page 6.0%) that has moved just as far.

There is a third term now that the sentence has no word for: the
**embedded contracts**. 81,681 B of the 506 KiB is the JSON Schema the
page carries so a reader can ask what a number means offline, and it
is neither "the page" nor "the data". `UX-342` split it in
`test_the_report_you_can_attach.py` and the guide never learned the
distinction; `UX-404` grew it again this round by declaring 79 more
units.

This is `UX-132`'s defect: a figure a later round moved and an earlier
document still quotes.

## Required Fix

- Re-measure both figures with the recipe in
  `.claude/skills/measure/SKILL.md` and quote the three-way split
  (source / contract / data), naming the fixture and the command, so
  the next round can re-check it.
- Say which of the three the two ceilings (8 MiB file, 4 MiB timeline)
  are read against.
- Annotate, do not delete, the round-21 synthetic figure: it is a dated
  measurement and `UX-132`'s rule is to mark it, not to rewrite
  history.

## Out of Scope

- Moving the ceilings. This is about the numbers a document quotes,
  not about what the tool refuses.

## Acceptance Test

- The `--export` section's figures match a fresh run of the recipe,
  within the noise the section states.
