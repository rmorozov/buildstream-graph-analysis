# UX-264: the DOM shim is copied twenty-five times

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-263 | **Serves:** all, through every viewer guard | **Topic:** guards

## Motivation

Every viewer guard boots the shipped modules against a hand-rolled DOM
shim written inline in its own file. There are **25 of them**:

```text
$ grep -rln "setAttribute" tests/unit/*.py | xargs grep -ln createElement | wc -l
25
```

They are near-identical — `function make(tag)` returning an object
literal with `attrs`, `children`, `className`, `setAttribute`,
`append` — and they drift, because nothing makes them agree. Three
fidelity defects in three rounds, each found in the page and then fixed
in the instrument:

| round | defect | what shipped because of it |
|---|---|---|
| 27 | `prepend` implemented as `append` | every order guard read a reversed document (`UX-235`) |
| 32 | `append` copied an already-parented node instead of moving it | a 4,000-row table read as 8,000 (`UX-262`) |
| 33 | `style: {}` swallowed every write | four dead drawings, invisible to 25 guards (`UX-263`) |

`UX-263` had to be applied in seven files to fix one bug. The next one
will be the same, and the 18 shims that did not need touching are now
*more* different from the seven that did — the fix made the drift
worse, which is the signature of a duplicated fact.

This is the defect this repository names as its most-repeated
(`UX-252`: "two hand-maintained copies of one fact drifting apart"), at
twenty-five copies, in the one place nobody looks because it is test
scaffolding rather than shipped code.

## Required Fix

1. One shim module — `tests/dom_shim.py`, or a `.mjs` the harnesses
   import — with the fidelity decisions in one place: node identity,
   `append` moving rather than copying, `prepend`, `style` reflection
   and its serialisation, `querySelector`.
2. Every harness imports it. A guard counts inline `createElement`
   shims and fails above one, the way `test_the_page_opens_the_way_it_
   says.py` censuses the open set.
3. The shim's own fidelity is asserted against a real browser for the
   properties the guards depend on, rather than against itself — the
   `test_the_serialisation_matches_what_chrome_does` shape from
   `UX-263`, generalised.

## Out of Scope

- Replacing the shim with a real DOM (`jsdom`, or Chromium in CI).
  That is `UX-257`, it is a different argument about dependencies and
  CI cost, and it is not blocked by this: one shim is a better starting
  point for that migration than twenty-five.
- Rewriting what the guards assert. This moves the instrument, not the
  measurements.

## Acceptance Test

Introduce one fidelity defect in the shared shim — `append` copying
instead of moving is the known-discriminating one — and confirm it
reddens guards in more than one file. Today that mutation has to be
applied 25 times to have the same reach, which is the measurement this
item is filed on.

## Outcome

**Fixed.** `tests/dom_shim.mjs` is the one node factory; twenty-five
harnesses import it through `process.env.BGA_DOM_SHIM`, published once
in `tests/conftest.py` as an absolute file URL — several harnesses run
node from a `tmp_path`, and the first migration failed exactly there,
resolving `./tests/dom_shim.mjs` against whatever directory the test
had chosen.

**The acceptance test, run.** One fidelity defect in the shared file —
`append` copying instead of moving, the known-discriminating one —
reddens guards in **three files**:

```text
tests/unit/test_one_click_from_investigation.py
tests/unit/test_tables_you_can_interrogate.py
tests/unit/test_the_dom_shim_is_one_instrument.py
```

Before this, that mutation had to be applied twenty-five times to have
the same reach.

**Consolidating found four disagreements with a browser**, each of
which had been quietly true in some subset of the copies:

- **`textContent` was a plain string.** A real DOM concatenates every
  descendant's text; the one harness that implemented it that way
  joined with a space. Chrome 141, measured: a `<div>` holding `"a"`
  and `<b>x</b>` reads `"ax"` — no separator. Two probes were reading a
  container's text where they meant the leaves, and one was parsing a
  heading's label out of a string that included its own subtitle.
- **`href` did not reflect.** `setAttribute("href", …)` sets the
  property in a browser; the shims left `.href` at `""`, so a probe
  reading `n.href ?? n.attrs.href` silently took the first branch.
- **Parent links were declared and never set.** One probe snapshots the
  tree with `JSON.stringify`; with real parent links the tree is cyclic
  — as it always was in a browser — so that snapshot had been of a
  forest, not a document.
- **A detached `<header>`.** `app.js` mounts the contents with
  `heading.after(contents)` and falls back to `insertBefore` when
  `after` is absent. The old shims had no `after`, so **the fallback
  was the only path any guard had ever exercised**. Giving the shim a
  real `after` made the fallback stop firing and the harness's
  unattached header stop working — the guard was measuring a branch the
  page does not take.

The shim also refuses selectors it cannot parse (`tr > td`,
`li:first-child`, `a + b`) rather than matching nothing: a selector
that quietly matches nothing reads as "the page does not render that",
and the guard passes.

**Not done:** the shim still has no layout engine, and says so at the
bottom of the file. That is `UX-257`, which landed in the same round
with a real browser instead.
