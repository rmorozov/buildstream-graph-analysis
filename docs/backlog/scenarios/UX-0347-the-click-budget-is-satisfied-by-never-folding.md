# UX-347: the click budget is satisfied by never folding

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-319 (the chain folds, and the clicks are counted), UX-286 (the report has chapters) | **Serves:** anyone looking for one number in a twenty-screen document | **Topic:** viewer | **Area:** bga/viewer

## Motivation

The visual contract's §3b sets a **click budget**: any section's
content is reachable in at most two interactions, and a guard measures
the worst path. The page satisfies it. Measured on a real boot,
clicks-from-first-paint to each thing a reader comes for:

```text
                              clicks   screens down (macro_micro)
the verdict sentence               0            0.3
what to fix first                  0            0.4
a Perfetto query                   1            5.9
the element table                  0            6.8
the critical path list             0            9.2
the memory envelope                0           10.8
confidence                         0           18.3
the run identity                   0           19.6
```

Almost everything is zero clicks. It is zero clicks because **almost
nothing is folded**: 51 `details` on the page, 3 of them open — but the
48 closed ones hold detail *inside* sections, and the sections
themselves are all expanded, all the time. The document is 18,148 px.

So the budget was met by paying in the other currency. A click is
directed: the reader names what they want and arrives. A screen of
scroll is a search: the reader does not know how far, and passes
nineteen things they did not ask for. §3b measures the first and
nothing measures the second, so the design optimised exactly what was
measured.

**The rail does not repay it.** There is a jump box and a section list,
so a reader who knows the section's name is one interaction away. A
reader who knows what they *want* — "how much memory would more
builders need" — is not: they scroll.

## Required Fix

A **distance budget** beside the click budget, measured by the same
kind of guard: on both committed fixtures, the document is at most N
screens at 1440x900, and no chapter's first section begins more than M
screens from the top of its chapter.

The lever is folding by chapter: a chapter other than the first opens
to its heading and its one-line answer, and expands on demand. That
turns most of the nineteen screens into one interaction each — which
the click budget already permits and which `UX-286`'s chapters were
built to make navigable.

The numbers N and M are chosen from what the page is *after*
`UX-346`'s note removal, not before, because that changes the height
substantially and picking a bound against the current page would pin
the wrong thing.

## Out of Scope

- Padding sections to a screen. Direction 13 already refused it, with
  a measurement: 31.3 screens of whitespace on the synthetic run.
- The first chapter, which is the decision and stays open. A reader
  who has to open the verdict has been handed nothing at all.

## Acceptance Test

The document height and the per-chapter offsets are measured on both
fixtures and asserted against a stated bound, in the same guard that
holds §3b's click budget — so a change that trades one for the other
reddens on the one it spent. The worst-case walk to each of the eight
destinations above is published in the guard's failure message, both
in clicks and in screens.

## Outcome (round 52, 2026-08-28) — 🟢 Done

### The gap, measured

Both currencies, on the two committed exports at 1440x900, at the
commit this item was worked from (`fc45f94`, after `UX-346`):

```text
                          golden              macro_micro
                       clicks  screens      clicks  screens
the verdict sentence        1      0.3           1      0.3
what to fix first           1      0.4           1      0.4
a Perfetto query            2      4.0           2      6.5
the element table           1      4.9           1      7.4
the critical path list      1      6.0           1      9.5
the memory envelope         1      6.7           1     11.1
confidence                  1     10.2           1     20.0
the run identity            1     11.2           1     22.1

document                          11.6                 22.7
last chapter's question           10.9                 21.8
```

One click to everything, because **nothing folds**: seven chapters, all
expanded, all the time. §3b measured the clicks and was satisfied; the
twenty screens of scroll past nineteen things nobody asked for were
free, because nothing measured them.

### After

```text
                          golden              macro_micro
                       clicks  screens      clicks  screens
the verdict sentence        1      0.3           1      0.3
what to fix first           1      0.4           1      0.4
a Perfetto query            2      4.0           2      6.5
the element table           1      4.4           1      6.9
the critical path list      1      5.4           1      9.0
the memory envelope         1      3.6           1      6.1
confidence                  1      3.8           1      6.3
the run identity            1      4.2           1      6.7

document                           4.1                  6.6
last chapter's question            3.8                  6.3
```

**No walk grew a click.** The screens are what moved: the document by
65% and 71%, the identity block from 22.1 screens to 6.7.

### The bounds, and where they came from

| bound | value | measured |
|---|---|---|
| the document a reader lands on | **10 screens** | 4.1 and 6.6 |
| the furthest chapter's question | **8 screens** | 3.8 and 6.3 |
| a chapter's heading to its first section | **half a screen** | 0.1 everywhere |

The first is one and a half times the worst measured: it admits a run
with more findings in the open first chapter — the only chapter whose
height still scales with the run — and reddens on a page that stops
folding at all (measured: 11.8 and 22.9 screens). All three live in
the file that holds §3b's click budget, and the failure message
publishes the eight destinations in clicks *and* screens, so a change
that spends one currency to buy the other reddens on the side it was
paid from.

### A folded chapter is its question, its answer and its count

```text
What if I change this?            [Show 3 sections]
  A change to toolchain.bst rebuilds 10 elements (50.2 s of work) - the widest here.

Where did the time go?            [Show 7 sections]
  46.1 s wall-clock, of which 43.2 s is execution on chain.

Was the machine used well?        [Show 5 sections]
  4 builder slots, 29.1% of their time used.

Which elements, and how do they connect?   [Show 12 sections]
  11 elements; the slowest is core.bst at 19.1 s.

How much of this can I believe?   [Show 4 sections]
  96.8% of this report resolves to this run's own record.

Which run is this?                [Show 3 sections]
  Captured 2026-08-21 17:01:28 UTC on Intel(R) Xeon(R) Processor @ 2.80GHz,
  written as analyze/v3.
```

Every sentence is **read from what the document already publishes** —
`signals.blast_radius`, the attribution split, `floors.occupancy_share`,
`structural.summary`, `confidence.primary`, `run_instance` — and
returns `null` where the fields are absent, so the `compare` chapter on
a first run folds with its question and its count and no sentence. A
summary that derived its own numbers would be a second pipeline,
disagreeing quietly; and one that threw would take its chapter's
heading with it, so `safely` wraps them the way `UX-335` wraps a
section.

### Why no walk grew a click

Every way into a section opens the chapter holding it — the rail's
links and its chapter links, the command palette, an `#anchor` pasted
into a fresh load, and `hashchange` — through one delegated listener
rather than a handler per link, because the rail is rebuilt whenever a
section arrives late. A fold a link cannot open is a section the click
budget cannot reach, which is the defect this item would have
*introduced* rather than fixed, so a clause shuts every chapter, clicks
every rail entry, and asserts the chapter opened and its target was
drawn: 28 and 40 entries, none stuck.

Paper opens everything: a folded chapter would print as a heading over
nothing, and paper does not navigate.

### Four guards moved with it, each for a reason

- `test_the_page_has_geometry.py`'s three chapter clauses and the
  identity-position clause now **open the chapters before measuring**.
  Folded, the identity group sits at 0 px and so does everything else,
  which is not an order at all — and two of those clauses would have
  passed over an empty document (a chapter with no drawn sections pads
  nothing; a zero-height section makes any spread look enormous).
- `test_no_chapter_pads_its_sections` moves from a quarter-screen of
  head to a third: the answer and the control wrap to two or three
  lines at 390px (measured 0.28 for `elements`, 0.26 for `time`, 0.16
  at 1440). The head is what a folded chapter *is*; a head past a third
  of a screen would be the padding the clause refuses.
- `test_each_chapter_is_a_named_landmark` reads the heading **without**
  the control, the way it already ignores a section's collapse caret.
- The export page budget rises 231,000 → 240,000 B, with the round's
  page/data split recorded in the note that guards it: page
  228,528 → 236,271 (`UX-346` +2,950, `UX-347` +4,793), data on the
  golden run 101,906 → 89,148, because `UX-345` removed a key from the
  schemas that travel with the document.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `d4bf28a`.

| # | mutation | reddened |
|---|---|---|
| E1 | every chapter opens (nothing folds) — the defect itself | 4 clauses: *"golden: the document is 11.8 screens at 1440x900, against a budget of 10.0"*, and *"a chapter's question is more than 8.0 screens down: [('elements', 8.5), ('believe', 10.3), ('run', 11.1)]"* |
| E2 | `revealChapter` returns without opening anything | `test_the_rail_opens_the_fold_it_points_into` |
| E3 | the `time` chapter answers `null` | `test_every_folded_chapter_says_what_is_behind_it` |
| E4 | the control labelled before its members arrive (the "Show 0 sections" this item shipped once, mid-work) | same clause, on the count |
| E5 | the first chapter folds too | `test_only_the_first_chapter_is_open` |
| E6 | `.chapter[data-open="false"] > section` display rule removed | the document and chapter-question bounds, 22.9 screens on `macro_micro` |

### What this leaves

The residual distance is chapter one: 3.1 screens on golden, 5.6 on
`macro_micro`, and it stays open by design. Inside an *opened* chapter
the old distances remain — the critical path list is 9.0 screens down
once `time` is open — which is the honest shape of "one chapter at a
time" and the reason the bound is on the document a reader lands on
rather than on every state the page can reach.
