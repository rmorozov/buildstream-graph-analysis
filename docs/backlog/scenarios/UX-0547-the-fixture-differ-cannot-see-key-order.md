# UX-547: the fixture differ compares parsed JSON, so key order drifts unseen

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-535` (whose refresh carried the drift), `UX-302` (the golden snapshot's rule) | **Found by:** `UX-535`, refreshing the fixture for a contract bump | **Serves:** the round that reads a fixture diff to check its own change | **Topic:** guards

## Motivation

`tools/dev_refresh_analysis.differences()` loads both sides with
`json.load` and compares the parsed objects. Key order is not part of
that comparison, so the committed fixture's order can drift from what
the emitter writes and nothing says so — until a `--write` reorders a
block and the diff carries a change nobody made.

`UX-535` hit it: its semantic diff was exactly the intended change
(three keys gone, the version stamps, `document_shape.leaves`
699 → 697), and the *textual* diff also carried a `value`/`resolved`
reordering that had been latent.

Harmless this time. The reason it is filed is that the fixture diff is
the instrument a round uses to confirm its change is the only one, and
an instrument that cannot see one axis of the file will one day hide
something on that axis.

## Required Fix

`differences()` reports order drift as its own line — not as a
difference in value, which it is not, but as "the committed order is
not the emitted order", so a round reading the diff knows which half
of the change is its own. Then either the fixture is rewritten in
emitted order once, or the tool says why it never will be.

## Out of Scope

- Making key order a contract — it is not one, and `UX-302` decides
  what the payload's shape means.

## Acceptance Test

A fixture whose keys are reordered and whose values are identical:
`differences()` names the drift and returns no value difference, with
a mutation that reorders one block.
