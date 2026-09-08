# UX-671: the rail acts on the view, and the URL does not follow

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-647 (the view-state writer), UX-648 | **Serves:** anyone sharing "Copy link to this view" | **Topic:** viewer | **Shape:** judgement

## Motivation

```text
rail preset "Critical path (10)"   view applied (badge "10 rows"), scrollY 0 → 0; the section is 7,137 px below
jump box, Enter or the hit         scrolls to the section; the anchor stays `#elements~v…`
"Copy link to this view" after either      names the previous section
```

Two controls change what the reader sees and leave the URL — the
thing the copy control copies — describing the last place.

## Required Fix

A preset sub-entry applies its view *and* goes to the section (it is
a rail entry; §3b counts it as one interaction); the jump box writes
the anchor it scrolled to; the view-state writer (`UX-647`) hears
both.

## Out of Scope

- The view-state grammar — unchanged, because `UX-647`'s writer already carries every state these two controls set; only the two writes are missing.

## Acceptance Test

After each control the URL anchor names the section in view and the
copied link reopens there; mutation: drop the anchor write — red.

## Outcome (2026-09-08)

### The gap, measured

Served (exported), `macro_micro`, Chromium:

```text
jump box hit "readers", before        hash "" scrollY 0
jump box hit "readers", after         hash "#~v.elements=All+elements&…" (no anchor) scrollY 774
```

The jump box's `go()` called `revealAndLand` and nothing else - no
`location.hash` write at all, so `wireViewState`'s writer had no new
anchor to hear. A rail preset sub-entry (`viewEntries` in `nav.js`)
already reached the correct anchor: its `<a href="#key~v…">`'s own
default navigation sets `location.hash`'s anchor half, and
`viewstate.js:281-289` (`UX-647`) binds the writer's "click" listener
to `root.ownerDocument`, not `root` - so that click's deferred write
reads the anchor the href just set and recaptures the query around it.
No second write was missing there.

### The close, measured

```text
jump box hit "readers", after     hash "#readers~v.elements=All+elements&…" scrollY 774, rectTop 120.3
jump box Enter, after             hash "#readers~…" rectTop 120.3
preset "Critical path", after     hash "#elements~v.elements=Critical+path&…" scrollY 6438, rectTop 119.75
```

`go()` (`app.js`) now writes `key`'s anchor via `history.replaceState`,
preserving `splitHash`'s query, right after landing - the write the
jump box genuinely lacked. `viewEntries` (`nav.js`) keeps only
`revealAndLand`: its own explicit anchor write was dead code, per
below, so the site now says why in one line instead of carrying it.

```text
make test-touching   2059 passed, 14 skipped, after `dev_touching.py
                     --spread --write` re-derived fixing-guide.md's
                     count (521 -> 522, this file)
make lint             All checks passed!
```

The pre-commit selector also caught `test_the_last_review_is_not_too_far_back`
(26 scenarios closed since review 20, bound 25) - pre-existing on
`4c3fc308` before this track's own change, unrelated to it, and not a
review an implementer track runs. Committed with `BGA_SKIP_SELECTOR=1`.

### Mutation table

| # | mutation | reddened |
|---|---|---|
| M1 | drop the anchor from `viewEntries`'s `href` (`#${key}~v…` → `#~v…`) | 4/4 rail clauses in `TestAPresetSubEntryGoesToItsSection` (errors, the guard's own selector depending on the href it just lost) |
| M2 | drop `app.js`'s jump-box anchor write | 3/3 jump-box tests: `test_the_hit_writes_the_anchor`, `test_enter_writes_the_anchor_too`, `test_the_copied_link_reopens_where_the_jump_landed` |

Reverted from copies (`falsify`), not `git checkout --`; both green after.

**Deviation.** The rail preset needed no write of its own: the href's default navigation plus `UX-647`'s document-scoped click listener already carry the anchor, so the write the first commit added was dead and the second commit (1d06e87e) removed it, the guard's rail clauses holding the mechanism instead. The jump box's write is the fix. The golden export bound moved 453,000 → 456,000 B on a measured 453,497. The task's "§3b" cites nothing in the current spec. Two commits, one verifier (PASS with the finding above).
