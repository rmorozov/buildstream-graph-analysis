# UX-436: forty-four controls are the browser's, not the page's

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 69, a field report that the page's buttons look dull | **Serves:** every reader, on every screen of the report | **Topic:** viewer

## Motivation

Counted over the booted export of a real capture, at 1440x900:

```text
buttons          468
distinct looks    12
UA-default bg     44
with transition    0
with box-shadow    0
```

`bga/viewer/style.css` is 1,106 lines and **has no base `button` rule.**
Controls are styled where a section happened to need one — `.investigate
button`, `button.collapse`, `button.chapter-open`, `.element-controls
button` — and everywhere else the browser's default is what the reader
gets:

```text
   44  rgb(239, 239, 239) | 2px outset rgb(0, 0, 0) | 0px | 1px 6px
```

`2px outset` on a beveled grey is the 1995 UA button, sitting inside a
page that otherwise runs on a declared token palette. That is the
"dull" in the field report, and it is not a matter of taste: it is
forty-four controls that no rule in this repository has ever described.

The twelve distinct looks are the same defect counted the other way.
Three of them differ only in padding and font-size — `2.4px 8px` at
12.8px against `1.6px 7.2px` at 12.48px — which is drift, not
intention.

**What this is not.** §6a refuses *delight* — motion, easing, ornament
— deliberately and on a stated ground, and this item does not reopen
that. The zero transitions and zero shadows above are recorded as
measurements of the current state, not as a gap to fill. **A control
that looks like the page it is in requires no animation.** What is
missing is one rule, in the token vocabulary the rest of the page
already uses.

Nor is it §4's problem. The emphasis budget bounds *tone* per block and
says nothing about whether a control has a resting appearance at all; a
button can be entirely un-emphasised and still not be the browser's.

## Required Fix

- **One base control rule**, in the existing tokens: surface from
  `--muted-bg` or `--panel`, border from `--line`, text from `--fg`,
  radius consistent with the 25 already in the file. Every scoped rule
  becomes a modifier of it rather than a separate look.
- **Name the grades that actually exist** and hold them to a small set —
  §6a's "one primary action per view" implies at least a primary and a
  quiet grade, and the `?` door is a third by geometry (209 of the 468,
  circular, 11.2px). Three, not twelve.
- **A guard that counts what a reader sees**: distinct computed control
  appearances in the booted page, bounded. It must redden on a new
  button added with no class — which is how all forty-four arrived.
- Focus states stay visible and the whole thing survives the export and
  a `file://` open, per §1's standing constraint.

## Out of Scope

- **Motion, easing and hover ornament**: refused by §6a on the export
  constraint, and this item explicitly leaves that refusal standing.
- **The palette itself** — `UX-304`'s two grades of token are settled
  and this spends them rather than changing them.
- **Re-laying-out any section**: this changes what a control looks like,
  never where it sits (`UX-317`, `UX-285`).
- **The `?` door's count**: §6a already bounds it at one per block and
  that work is its own.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
bga view @last --export /tmp/report.html
```

Boot it and count distinct computed appearances over every `button`:
the number is at or under the stated bound, and none reports the UA
default surface. A mutation adding a classless `<button>` to any
section must redden the guard.

## Outcome

_Not started._
