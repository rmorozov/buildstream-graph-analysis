# UX-219: what if I fix these — the plan, drawn

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-207 (the top actions), UX-208 (the table it replaces)

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
