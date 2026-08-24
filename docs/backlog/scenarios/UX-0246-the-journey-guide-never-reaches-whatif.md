# UX-246: the journey guide never reaches what-if

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-230 (the command it should reach) | **Serves:** R1 — the local optimizer the guide is written for | **Topic:** docs

## Motivation

Found by review 1 (`UX-241`).

[`docs/guides/real-project.md`](../../guides/real-project.md) is the
end-to-end journey — capture → read → go inside → join → **act** →
gate — and it is the document `README.md` points at six times. The act
step is where a reader decides what to fix. `bga whatif`, which prices
exactly that decision, is named nowhere in it:

```text
subcommands absent from docs/guides/real-project.md:
  whatif, cache-trend, diagnostics, floors, graph, utilisation
```

Five of those six are correct absences: the guide is a journey and
`floors`/`graph`/`utilisation`/`diagnostics` are `analyze`'s own
sections, with `cli.md` as their reference. `whatif` is not — it is a
step in the journey the guide walks, and the guide walks past it.

## Required Fix

1. The act step gains `bga whatif <element>…`: what it answers, and
   the one thing that makes the number safe to quote — *fixed* means
   the element becomes instant over this run's measured durations, an
   upper bound and not a forecast (`UX-244` is the same convention's
   other home).
2. Real output, as every other step in that guide has.

## Out of Scope

- The other five absences, which are correct — a journey is not a
  reference, and `cli.md` names all of them (checked).
- A guard that every subcommand appears in every guide. That would be
  wrong: it would force `ci-comment.md` to name `sweep`.

## Acceptance Test

The act step names `bga whatif` with output from a real run, and the
convention is stated in the guide's own register rather than quoted
from the docstring.

## Outcome — 🟢 Fixed & Verified

Step 7 — *"change something, then prove it"* — now opens with **"Before
you change anything: price the change"**, and the example it prices is
better than the one this item imagined.

The guide's own committed run (`examples/06-macro-micro-optimization`,
the snapshot at `20260821T170127Z`) carries a case that inverts the
naive reading:

```text
$ bga whatif …/run --element core.bst
  Makespan 43.200s -> 31.150s (saves 12.050s)
$ bga whatif …/run --element codegen.bst
  Makespan 43.200s -> 43.200s (saves 0.000s)
$ bga whatif …/run --element core.bst --element codegen.bst
  Makespan 43.200s -> 24.150s (saves 19.050s)
  Their individual savings add up to 12.050s, which is not what they are
  worth together (19.050s) - what one fix is worth depends on the others.
```

`codegen.bst` is worth **nothing** on its own and **seven seconds** the
moment `core.bst` is fixed, because it sits on the chain that becomes
binding once `core.bst` goes. An element a reader would strike off the
list today is on it tomorrow — and that is exactly what a per-element
table cannot say, which is the argument for the step existing at all.

**This corrected the chapter written for `UX-244` an hour earlier.**
That chapter said summing per-element savings is "wrong in the direction
that overstates". It is wrong in **both** directions: it overstates on
parallel branches (`UX-74`'s `cmake-stage1` + `git-minimal`, 2117.5s
summed against 1569.8s joint) and understates here (12.050s summed
against 19.050s joint). `architecture.md` now says both, with this run
as the second measurement.

Clause 1 also gained the convention in the guide's own register — "an
**upper bound**, not a forecast … a real fix that makes the element
merely faster lands under it; a fix that changes the graph is not
modelled at all" — and the refusal, pasted, with its exit 0 stated.
The appendix accounts for the new figures, as it does for every other
number in the guide.

**The guard** — `tests/unit/test_the_journey_reaches_what_if.py`,
8 tests. Deliberately narrow, per this item's Out of Scope: it checks
one step of one guide for one command, and does **not** assert that
every subcommand appears in every guide, which would force
`ci-comment.md` to name `sweep`.

Its useful half is that the pasted figures are **recomputed**, not
trusted: `_render()` runs `bga.whatif.project` against the committed run
and every projection figure the document pastes must be one the tool
produces today. A pasted number is a claim about the tool, and the run
is in the tree, so the claim is checkable rather than historical
(`UX-132`).

**Three of the first six mutations did not discriminate, and the guard
was rewritten rather than the mutations counted:**

```text
first draft                     M2 delete the pasted block   -> green
                                M4 pasted saving goes stale  -> green
                                M5 summed figure goes stale  -> green
```

Two independent reasons, both worth recording:

1. The checks asked whether the *figure* appeared in the step. The prose
   around the block repeats both figures in bold ("worth **12.050s**",
   "worth **19.050s**"), so deleting or editing the pasted output left
   the sentence *discussing* the number to satisfy the check. This is
   the self-matching failure in its subtlest form yet — not a guard
   finding its own argument, but a guard finding the caption instead of
   the picture.
2. The one check that did read pasted lines compared them line by line,
   and the guide reflows pasted output to 72 columns while the renderer
   emits one long line. That is `UX-244`'s lesson recurring one guide
   over, within the same session.

The rewrite matches the renderer's **forms** on flattened text —
`Makespan X -> Y (saves Z)` and `add up to A … worth together (B)` —
which no sentence can produce and no reflow can break. Re-falsified:

```text
M1  remove the act-step block   -> names_whatif + shows_output + says_what_it_is_not
M2  delete the pasted output    -> test_the_step_shows_output_and_not_only_a_command
M3  drop the convention         -> test_the_step_says_what_the_number_is_not
M4  saving 19.050s -> 19.500s   -> every_pasted_figure[act step] + [appendix]
M5  summed 12.050s -> 12.500s   -> every_pasted_figure[act step]
M6  appendix stops accounting   -> test_the_appendix_says_where_the_figures_came_from
M7  appendix 31.150s -> 31.000s -> every_pasted_figure[appendix]
```

M7 was added because M4-M5 only proved the act-step parameter; a
parametrized guard is falsified when each parameter has been.

`test_the_run_still_discriminates_summed_from_joint` is the floor under
all of it: if the committed run ever stops separating summed from joint,
the step's whole argument goes with it and the example has to move to a
run where it holds — reddening then is correct, not noise.
