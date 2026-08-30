# UX-417: the guide's export figures are stale by 3.2x

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** architecture review 7, checklist item 3 | **Serves:** anyone deciding whether to attach a report | **Topic:** docs

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

## Outcome (round 65, 2026-08-30) — 🟢 Done

### The gap, measured

The guide said:

```text
Measured on `examples/06`'s real 46 s two-plane capture: **158 KiB**,
of which the page is 90,611 B.
```

Re-measured in round 65 on a fresh cold capture of the same project —
`bga snapshot -- bst build all.bst` against an isolated
`XDG_CACHE_HOME` (38 s), then `bga view <run> --export report.html`:

```text
total       520,048 B   508 KiB
  source    283,979 B   54.6%
  contract   81,623 B   15.7%
  data      154,446 B   29.7%
```

**3.3x the total, and 3.1x the page.** Both halves of the guide's
sentence were wrong by roughly the same factor, which is why the
conclusion it drew from them still read as true.

### After

The `--export` section now carries the three-way split, both fixtures,
and the command that produces each. The synthetic run was re-measured
too, because the paragraph beside it quoted a round-21 figure:

```text
total     1,197,665 B  1170 KiB   (bga gen-synthetic /tmp/scale --seed 1)
  source    283,922 B   23.7%
  contract   81,623 B    6.8%
  data      832,120 B   69.5%
```

### The fact the split makes visible

**Source and contract are the same bytes on both runs** — 283,979 vs
283,922 and 81,623 vs 81,623. They are the page; a bigger project does
not make them bigger. What scales is the data, from 30% of a small
report to 70% of a 1,202-element one. The old sentence had no word for
the contract at all and folded it into "the page", so a schema addition
and a viewer addition were the same number to a reader.

### Which ceiling reads which half

The filing asks for this and the guide never said it. Read off the
code rather than inferred:

- **8 MiB** is `EXPORT_BUDGET_B`, compared against the size of the
  whole written file — all three parts.
- **4 MiB** is `TRACE_BUDGET_B`, compared against `len(trace)` where
  `trace` is the **gzipped timeline before base64**, one part of the
  data half. It is the only quantity either ceiling singles out.

Both are in a table column beside the ceilings now.

### The old figures are marked, not deleted

`UX-132`'s rule. Both superseded measurements are kept in a block
quote that says what they were, when they were taken and what
superseded them — a dated measurement is evidence about *when* the page
grew, which is exactly what a reader of the tripling wants. The audit
records in `docs/audits/` are left alone: an audit round's figures are
dated by construction.

### Deviation from the Required Fix

- **None.** Both figures re-measured with the recipe and the fixture
  and command named; the three-way split quoted; the two ceilings
  attributed to the halves they are read against; the round-21 figure
  annotated rather than rewritten.
- One thing the filing did not ask for and the section now states: the
  reason the split is worth having is that source and contract do not
  move with the run and data does. Without that sentence the three
  numbers are three numbers.
