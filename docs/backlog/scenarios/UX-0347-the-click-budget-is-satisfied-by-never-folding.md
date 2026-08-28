# UX-347: the click budget is satisfied by never folding

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-319 (the chain folds, and the clicks are counted), UX-286 (the report has chapters) | **Serves:** anyone looking for one number in a twenty-screen document | **Topic:** viewer

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
- The first chapter, which is the decision and stays open.

## Acceptance Test

The document height and the per-chapter offsets are measured on both
fixtures and asserted against a stated bound, in the same guard that
holds §3b's click budget — so a change that trades one for the other
reddens on the one it spent. The worst-case walk to each of the eight
destinations above is published in the guard's failure message, both
in clicks and in screens.
