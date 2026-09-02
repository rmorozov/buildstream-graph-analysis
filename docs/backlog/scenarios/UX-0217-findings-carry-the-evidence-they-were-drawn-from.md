# UX-217: findings carry the evidence they were drawn from

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-202 (the finding renderer), UX-207 (the decision the findings support) | **Topic:** viewer

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

---

## Outcome (round 25)

**Status:** 🟢 Done.

`renderFindings` renders `evidence` under each finding's detail,
through the same schema machinery as everything else. Measured on the
golden fixture: `primary: 0.875` reads **87.5%**, `category_us: 2000`
reads **2 ms**, `band: "high"` reads **high**.

**The units are the substance, and each was checked against a rendered
value rather than inferred from its key.** The evidence vocabulary is
59 keys wide; `_us` is the only suffix in it safe to read
mechanically. `primary` is a share and not a count; `cores_busy` is
1.60 and a ratio, not a share; `envelope_mb` is 613.7 megabytes. So
`EVIDENCE_QUANTITIES` declares 39 of them in `analyze/v1`, and the
guard that every declared key is one a finding actually emits keeps the
contract from rotting in the other direction.

Nothing is special-cased per finding: a new finding's evidence formats
correctly if its keys are declared, and renders raw if they are not —
which is the honest degrade, and better than inventing a unit.

**Structured evidence is left alone.** `rows`, `steps` and
`constraints` are tables in their own right that a finding builds its
sentence from, and the report already draws them elsewhere. Flattening
them into a definition list would be a worse rendering, not a more
complete one.

**The fold hides pixels, not the DOM.** Above four measurements the
block folds (`UX-209`'s rule, `data-fold`ged so `UX-211` carries it in
the link) and the guard asserts all ten values are still present — a
fold that costs the reader Ctrl-F is not a fold.

Seven mutations, each verified red: the evidence dropped again (six
guards); the units name-sniffed instead of read from the schema;
`primary` losing its declared share; `category_us` declared as seconds;
the arrays flattened in; the fold hiding values from the DOM; a
declared key no finding emits.

**One defect the work surfaced:** `renderEvidence` was already the name
of `UX-202`'s evidence *header*. The new one is
`renderFindingEvidence` — two different objects called evidence, and
the import collision is what made that visible before it shipped.

**Deviation from the Required Fix:** clause 3 asks for evidence keys
naming elements or sections to become links. None of the 39 declared
keys is an element uid or a section name — the element-shaped evidence
(`rows`, `steps`, `latent_heavies`) is exactly the structured kind this
item leaves to the sections that draw it, and `UX-216` already links
every element occurrence there. Nothing was dropped; there was nothing
of that shape to link.
