# UX-547: the fixture differ compares parsed JSON, so key order drifts unseen

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** `UX-535` (whose refresh carried the drift), `UX-302` (the golden snapshot's rule) | **Found by:** `UX-535`, refreshing the fixture for a contract bump | **Serves:** the round that reads a fixture diff to check its own change | **Topic:** guards | **Area:** tools

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

## Outcome (round 81, 2026-09-02) — 🟢 Done

**Premise:** held — `sort_keys=True` threw key order away; both committed fixtures were already in emitted order.

### The gap

`differences()` compared each top-level key with
`json.dumps(..., sort_keys=True)`, so two documents saying the same
thing in a different order compared equal. `UX-535` is the instance:
its semantic diff was exactly the intended change while the textual
diff carried a `value`/`resolved` reordering nobody had asked for.

The loader question the item asks: `json.loads` keeps insertion order
on CPython 3.7+, so **each file's own order survives the parse** — it
was only the `sort_keys=True` comparison that threw it away. Nothing
had to be re-read from the bytes.

### The close

`order_drift()` walks both parsed sides and reports `(where, emitted,
committed)` for every object carrying the same key *set* in a different
order, as its own line naming itself:

```text
the committed order is not the emitted order
```

It runs only over keys whose values already agree — a key that differs
explains its own reordering, and reporting both would say one change
twice. A node whose key sets differ is a value difference and is left
to the existing comparison.

### The decision the item asked for

**No rewrite was needed.** Both committed fixtures are already in
emitted order — the baseline below reports no drift — so there was
nothing to normalise. `--write` is the standing fix if one ever drifts,
and that is now written in the module docstring rather than implied.

### Mutations verified red and reverted (2)

Applied to `tests/fixtures/with_timeline/analyze.json`, read through
`differences()` directly (which is how the guard calls it):

| # | mutation | reported |
|---|---|---|
| — | baseline, untouched | `(no differences)` |
| M1 | `headline`'s keys reversed, every value identical | `$.headline \| the committed order is not the emitted order` — **and no value difference** |
| M2 | `total_duration_us` + 1, order untouched | `total_duration_us \| differs` — **and no drift line** |

M2 is the one that makes M1 mean something: a differ that called every
change "order drift" would pass M1 and fail here.

### One thing fixed in passing

The module's own usage block opened with
`python3 tools/dev_refresh_analysis.py --check`, and there is no
`--check` flag — the guard imports `differences()`. Pre-existing, not
introduced here, and `UX-326`'s class (a tool's printed sentence is a
contract). Corrected to the command that does run.

### Deviation from the Required Fix

None. Both branches of the decision were available and the measured
one — fixtures already in emitted order — needed neither.
