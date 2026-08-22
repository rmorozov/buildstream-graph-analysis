# UX-217: findings carry the evidence they were drawn from

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-202 (the finding renderer), UX-207 (the decision the findings support)

## Motivation

Every finding already carries a structured `evidence` dict. Measured on
`examples/06`:

```text
cache-hit-ratio     hit_ratio, built_elements, cached_elements, run_mode
confidence          primary, band, violation_count
wait-category       category, category_us, share, hint
time-concentration  path_us, share_of_path, chain_bound, rows
```

`renderFindings` (`app.js:159`) reads `id`, `severity`, `title`,
`detail` and `elements`. It does not read `evidence`. So the page shows
the *conclusion* and drops the numbers the conclusion was drawn from —
in a tool whose entire proposition is that its conclusions are measured
rather than guessed.

A finding today is a statement. It should be a statement, the evidence,
and the action:

```text
⚠ Build is chain-bound
   critical path      3610s
   share of path        94%
   scheduling wait      <1%
   ↓ therefore
   Increasing builders is unlikely to help.
   [Show critical path]  [Inspect timeline]
```

`UX-204` built exactly this shape for the Perfetto handoff — "where to
look, and why". This generalises it one step, to the finding itself.

## Required Fix

1. `renderFindings` renders `evidence` as a small definition list under
   the detail, formatted by the same schema machinery as everything
   else — a key with a declared `bga:quantity` renders in its unit, and
   one without renders raw. No per-finding code.
2. The finding's schema node declares the evidence shape (`properties`
   with quantities), so a new finding's evidence formats correctly with
   no viewer change — `UX-201`'s rule, applied one level deeper.
3. The evidence keys that name elements link to `UX-216`'s element
   section; the ones that name a section link to it.
4. Evidence is folded by default where it exceeds four rows, open
   otherwise, `data-fold`ed so `UX-211` carries it in the link.

## Out of Scope

- Changing what any finding concludes, or what it puts in `evidence`.
- A new evidence field for findings that carry none — a finding without
  evidence renders exactly as today.
- The "copy this finding" affordance (`UX-224`).

## Acceptance Test

On `examples/06`, all four findings render their evidence keys, and a
`duration_us`-declared evidence value renders in seconds rather than as
a bare integer (asserted against the published value, not the rendered
text). A finding whose payload carries no `evidence` renders unchanged
from today, byte for byte.

Mutations, each asserted red: drop `evidence` from the renderer → the
evidence guard fails; render evidence by name-sniffing instead of the
declared quantity → the units guard fails on `time-concentration`'s
`path_us`. Page-size guard holds.
