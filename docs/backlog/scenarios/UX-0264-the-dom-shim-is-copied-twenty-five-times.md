# UX-264: the DOM shim is copied twenty-five times

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-263 | **Serves:** all, through every viewer guard | **Topic:** guards

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
