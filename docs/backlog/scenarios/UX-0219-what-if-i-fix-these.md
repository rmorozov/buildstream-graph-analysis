# UX-219: what if I fix these — the plan, drawn

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-207 (the top actions), UX-208 (the table it replaces)

## Motivation

`signals.optimization_horizon` already carries the whole answer, per
step. Measured on `examples/06`:

```json
{"element_uid": "core.bst", "saving_us": 12050000,
 "makespan_after_us": 31150000, "cumulative_saving_us": 12050000,
 "entering": ["codegen.bst"]}
```

It renders as a five-column table. The question it answers — *if I fix
the top three, what does this build become?* — is the single most
product-shaped question the tool answers, and a table is the weakest
way to answer it.

`entering` is the part that matters and the part a table hides: the
elements that **join the critical path** once that step is taken. It is
the honest reason the savings stop adding, and it is why this is a plan
rather than a sum.

```text
now                              46.1s
████████████████████████████████████
fix core.bst                     31.2s   → codegen.bst enters
██████████████████████████
+ fix lib-b.bst                  27.2s
██████████████████████
```

Every width is a published `makespan_after_us` over a published total —
one CSS division, `UX-202`'s rule, no arithmetic in the page.

## Required Fix

1. The horizon renders as a cumulative bar sequence beside the decision
   panel: one row per step, width from `makespan_after_us`, the saving
   and the element named.
2. Each row names what `entering` says joins the path at that step, and
   links those elements to `UX-216`'s sections.
3. The final row states the total: *"3 fixes → 41% faster"*, computed
   from published values only.
4. The table stays, folded beneath it — nothing leaves the page or the
   export.

## Out of Scope

- Any new projection, and any step the payload does not publish. If the
  horizon has three entries, the plan has three rows.
- Making it interactive (selecting a subset re-projects) — that is a
  second analysis, and the payload publishes one ordering.

## Acceptance Test

On `examples/06`: every bar's width resolves to a published
`makespan_after_us` (asserted from `data-` attributes against the
payload, not from computed style), and the `entering` elements named in
the drawing are exactly the payload's. The stated total equals
`cumulative_saving_us` of the last step over `total_duration_us`.

Mutations, each asserted red: compute a width from a sum of `saving_us`
instead of reading `makespan_after_us` → the widths disagree with the
payload on `examples/06`, where they differ; drop `entering` from the
rows → the guard that the drawing names what joins the path fails.
Page-size guard holds.

## Outcome (round 26)

One row per published step, plus the run as it stands so the bars have
something to shorten. Every width is one published `makespan_after_us`
over one published `total_duration_us` — a single division, carried on
`data-makespan-after-us` so a guard reads the drawing against the
payload rather than through computed style.

**The committed golden fixture discriminates the width mutation on its
own**, which is worth stating because it is why this guard is not
decorative. At every step the published makespan differs from the naive
`total - cumulative_saving_us`:

```text
base.bst    8000  vs 10000
lib.bst     4000  vs  6000
extra.bst   3000  vs  5000
app.bst        0  vs  2000
```

A drawing that summed savings would disagree with the payload on every
bar. That fixture also carries a real `entering` step (`lib.bst` →
`extra.bst`), so the guard that the drawing names what joins the path is
checked against something rather than passing over four empty lists —
which is asserted explicitly, so emptying the fixture fails rather than
quietly making the guard vacuous.

### A mutation that could not discriminate, and what replaced it

> *the total re-adds `saving_us` instead of reading `cumulative_saving_us`*

Applied, everything stayed green — and it always would. In every report
this analyzer produces, `cumulative_saving_us` **is** the running sum of
`saving_us`; they agree by construction, so no real fixture can separate
them. The mutation was rejected rather than counted.

The property it was meant to check is real, so it is checked where the
two *can* differ: a synthetic payload whose last `cumulative_saving_us`
(15) disagrees with the sum of its savings (20). The page must report
15, and the mutation reddens there. A guard that can only pass is not a
guard, but neither is one deleted because its first mutation missed.

### The size discipline, and how much of it this round spent

UX-218 replaced the absolute page ceiling with composition + Direction
7's ratio + a loose 120,000 B backstop, after the ceiling was crossed
three rounds running. Measured after this round's two drawings:

```text
exported page with its data removed   107,533 B
backstop                              120,000 B
margin                                 12,467 B
```

Holding, and stated rather than assumed: the culprit strip and the
horizon together spent a real fraction of the headroom that change
created. The ratio guard and the composition guard both still pass.

**Mutations verified red and reverted:** width from a sum of savings
rather than the published makespan (2 guards); `entering` dropped from
the rows (2); a bar drawn with no total to divide by (1); the total
re-derived rather than read (1, on the separable payload).

**Deviation from the Required Fix:** none. Clause 4's table stays — the
drawing is appended in `views.js` and `app.js` never names
`optimization_horizon`, which is asserted, so the generic schema
dispatch still renders the table beneath with no special case.
