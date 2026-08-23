# UX-228: focus is an investigation, not a dimmer

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-222 (the focus state), UX-216 (the element object), UX-227 (the explanation it reuses) | **Serves:** R1, R2 | **Topic:** viewer

## Motivation

`UX-222` built focus as visual state: one element held, the rest
dimmed, the document unharmed. The fourth review's observation,
adopted: that mental model is "dim everything else", and the reader
who focuses an element actually wants "show me the evidence about
*this*". Today they focus `openssl.bst` and still scroll — the
element section is one place, its blast another, its history a
third, the finding that names it a fourth.

## Required Fix

Focusing an element additionally presents its organised evidence —
why it matters (the `UX-227` block), what evidence exists (which
planes/payloads carry it: join row, Plane 2 lanes, history,
findings that name it), its relationships (upstream blocker on the
chain, downstream consumers — both already published), and its
actions — assembled entirely from published objects. Unfocusing
restores the document exactly. The export and print render the
plain document (focus is served-mode state, like the palette).

## Out of Scope

- Any relationship computed in the page (a relation not published
  goes through the pipeline first).
- Panes, drawers, overlays (round 24's declined-drawer argument
  stands: what cannot survive an export or a print does not enter
  the page).

## Acceptance Test

Focus on the golden run's top element shows the four groups with
every value traceable to a published field (same walk as UX-227);
unfocus leaves the DOM identical to never-focused (asserted by
serialisation compare); the focus state still round-trips through
the URL (`UX-225`'s guard unbroken); export contains no focus
machinery output.

## Outcome (round 28)

Focusing an element now prepends an **investigation section** under the
focus bar: four groups, assembled from published objects.

```text
Everything about base.bst
  Why it matters       — the measured rows UX-227's fold uses, each with
                         the path it was read from
  What evidence exists — critical path: yes · horizon: yes · off-path
                         heavies: not in this document · Plane 2
                         (sandbox): not in this document · findings
                         naming it: 1 · store history: 3 snapshot(s)
  What it is connected to — waits on / blocks (its chain neighbours, by
                         published order) and how many elements rebuild
  What to do           — its section, and the published next step or the
                         command that answers the question
```

**Unfocus restores the document exactly**, and that is asserted by
serialisation compare rather than by eye: the tree is captured before
focusing, after focusing (to prove the compare is not vacuous) and after
unfocusing, and the first and third must be identical strings. The
property holds by construction — everything focus adds carries
`data-role`, and the refresh removes exactly that set — and the guard
that the panel *is* in that set is separate, because the construction is
what a later edit breaks.

### Presence is not a value read, and does not pretend to be

The first draft gave the evidence group `data-field`/`data-raw` like
every other row, with the element uid as the "value" under a path that
resolves to an object. That is a traceability claim the row cannot
honour. Presence rows carry `data-source` (where it looked) and
`data-present` (what was there) instead, and the guard resolves each
source path to check that "yes" and "not in this document" are the
truth rather than a label. `Plane 2 (sandbox): not in this document` on
the golden run is the case that matters: "Plane 2 saw nothing" and
"Plane 2 was not run" are different facts, and a list of only what
exists collapses them.

### The path grammar grew one form, in both resolvers

`signals.blast_radius` is keyed by element uid, and a uid contains dots,
so no dotted path can address one. A `[...]` segment that is neither a
number nor a `key=value` selector is now a **literal key** on an object
and an index on a list — `signals.blast_radius[base.bst].downstream_count`
resolves, and so does `signals.critical_path[1]`. Added to
`bga/provenance.py` and `views.js` together, because the guard compares
the two resolvers on every path the page emits.

**Mutations verified red and reverted (5):** the panel dropped from the
removal set (the unfocus compare reddens); a presence row asserting
"yes" unconditionally; the chain neighbours read one index the wrong
way; an unknown element handed the first element's facts; the panel's
`data-role` renamed.

**Deviation from the Required Fix:** none. No pane, no drawer, no
overlay — round 24's argument stands, and this is a section prepended to
the document and removed again. The export contains no focus output and
still ships the renderer, because the served page needs it and an export
is one file.

Full suite: `3045 passed, 3 skipped`.
