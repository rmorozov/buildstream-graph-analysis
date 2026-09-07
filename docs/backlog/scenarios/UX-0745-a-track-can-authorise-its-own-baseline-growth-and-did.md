# UX-745: a track can authorise its own baseline growth, and did

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the baseline), UX-705 (the burn-down, whose pass condition this defeats) | **Serves:** the session merging a track it did not watch | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-705`'s Acceptance Test says a batch passes when **"no new finding
of any rule"** appears. Nothing enforces it. `dev_baseline.py --write
--force --reason UX-NNN` writes the gain and stamps the reason, and
`--check` is then clean by construction — the list the gate compares
against is the one the track just rewrote.

Measured, round 103: `UX-742`'s track added a `PLR0915` and an `S607`
to `tools/dev_js_deps.py`, forced them with `--reason UX-742`, and
reported `make lint` → `All checks passed!` and `clean: 302
finding(s)`. Every gate was green. The growth was found by the session
reading the diff, and both entries turned out avoidable — one function
extraction and `UX-687`'s existing `tracked_paths` — so the merged
tree is back at 292 with no growth at all.

```console
$ git diff eda28da 263cdcf -- tests/quality_baseline.json
-  "forced_by": "UX-705",
+  "forced_by": "UX-742",
+    {"file": "tools/dev_js_deps.py", ... "rule": "PLR0915" ...},
+    {"file": "tools/dev_js_deps.py", ... "rule": "S607" ...},
```

`--force` exists for a real case (`UX-694`): a gain a round has decided
to accept. The defect is that the same key opens the door for a track
that has decided nothing, and the reason string is checked only against
HEAD's — a *different* id always passes.

## Required Fix

A forced gain is the **session's** act, not a track's. Weigh two
routes and measure before choosing:

- The gate reads HEAD's baseline rather than the working tree's, so a
  `--force` that is not yet in HEAD is a gain and red — the shape
  `gained_since_head()` already has, applied to `--check` in `make
  lint` and not only to the diff guard.
- `--force` refuses unless the reason is an id whose task file is open
  and names the file being grown, so the authorisation is traceable to
  a row rather than to a string.

Whichever lands, the run ledger's row says when a track forced, so
`UX-666`'s table shows it.

## Out of Scope

- Removing `--force`. `UX-694` filed it deliberately and a round does
  sometimes accept a gain; this row is about who may press it.
- Re-auditing the forced entries already in HEAD. There are none: the
  field is clear at 292.

## Acceptance Test

A track's commit that forces a new finding is red at `make lint` on the
track's own branch, naming the rule and the file. Mutation: the session
forces the same finding with the same reason after deciding it — green,
and the ledger row says the round authorised a gain.
