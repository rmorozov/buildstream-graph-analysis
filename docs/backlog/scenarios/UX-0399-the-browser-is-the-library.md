# UX-399: the browser is the library

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-392 (the filters), UX-393 (the navigation), UX-396 (the drawings gap) | **Serves:** R2, and every reader of a seven-screen report | **Topic:** viewer

## Motivation

Round 64 answered "how does the page grow without importing
libraries" partly by inventory: the platform now ships, natively and
CSP-clean, most of what a table/UI library is adopted for — and the
page uses none of it:

```text
$ grep -rn "content-visibility\|IntersectionObserver\|popover\b\|<dialog" bga/viewer/
bga/viewer/views.js:941:  box.setAttribute("data-popover", detail);   # hand-rolled, not the platform's
```

The specific replacements, mapped to open work:

| primitive | replaces | serves |
|---|---|---|
| `content-visibility: auto` (+ `contain-intrinsic-size`) | virtual scrolling — offscreen sections and rows stop costing layout | the 9,316 px page; `UX-397`'s "virtual scrolling at 1,200 rows" argument, without the 400 KB |
| `IntersectionObserver` | scrollspy — the rail learns where the reader is; next/prev become real | `UX-393` |
| `popover` attribute / `<dialog>` | overlay plumbing for the `?` apparatus and table focus | §2b apparatus, `UX-318`'s focus state |
| `:target` + `scroll-margin-top` | deep links that land under sticky chrome instead of behind it | every rail jump and finding anchor |
| CSS `@container` queries | resize listeners for density adaptation | §2a size grades at narrow widths |

## Required Fix

- Adopt `content-visibility: auto` on chapter sections (with declared
  intrinsic sizes so scrollbar geometry and `Jump to…` targets stay
  honest), and measure the before/after of a full-report render on
  the round-63 export — the claim is layout cost, so the number is a
  layout number.
- Give the rail a scrollspy via `IntersectionObserver` — the current
  section highlighted, next/previous controls that move one section —
  as `UX-393`'s implementation route (that filing stays the work
  order; this one fixes the route to a zero-dependency one).
- Record the inventory table in `docs/design/styleguide.md` beside
  the `UX-398` rule, so "can the platform do it" is the first
  question a future widget asks — with the styleguide, not this task
  file, as the living copy.

## Out of Scope

- The `?` apparatus and table-focus migrations to native
  `popover`/`<dialog>` — priced here, but they are rewrites of
  working §2b/§3a mechanisms and each deserves its own task if the
  price is right.
- Any polyfill — a primitive the shipped Chromium baseline lacks is
  simply not on the menu; the inventory lists what is.

## Acceptance Test

- The full-report render measurement exists in this file with the
  export it was taken on, and shows the offscreen cost dropping.
- A driven browser scrolled mid-report shows the rail highlighting
  the section in view, and next/prev moving exactly one section.
- The docs guards pass with the styleguide's inventory section.
