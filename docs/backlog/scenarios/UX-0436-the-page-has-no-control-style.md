# UX-436: forty-four controls are the browser's, not the page's

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 69, a field report that the page's buttons look dull | **Serves:** every reader, on every screen of the report | **Topic:** viewer

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

**Round 70, 2026-08-31.** All four bullets. Every number below is read
out of a real Chromium at 1440x900 over the booted export, which is the
only instrument that can see what this item is about.

### The defect, reproduced

```console
$ # macro_micro, exported and booted
buttons        429
distinct looks 11
UA-default bg  52
   44  rgb(239, 239, 239) | 2px outset rgb(0, 0, 0) | 0px | 1px 6px | 12.75px | rgb(0, 0, 0)
    5  rgb(239, 239, 239) | 2px outset rgb(0, 0, 0) | 0px | 1px 6px | 13.3333px | rgb(0, 0, 0)
    3  rgb(239, 239, 239) | 2px outset rgb(0, 0, 0) | 0px | 3.2px 4.8px | 12.75px | rgb(0, 0, 0)
```

The item's signature line, at 44, plus two more UA variants it had not
counted — **52** controls the browser drew and nobody else did. They
came from rules like `.toc-steps button { font-size: .85em; padding:
.2rem .3rem }`, which set metrics and left surface and border to the UA.

### Closed

```text
                    macro_micro      scale (seed 1)
buttons                     429                1591
distinct looks           11 -> 3                   4
UA-default surface        52 -> 0                   0
```

The base rule alone took UA-default to **0** while leaving 11 looks —
the spread had moved into font-size and padding, most of it from
`em`-relative sizes resolving differently per parent. Stripping the
metric overrides from the nine scoped rules that restated them took it
to 3.

### Four grades, not three, and why

`macro_micro` shows three; the scale page shows four, because it is the
only one with a folded table and a long path. The fourth is **reveal** —
`fold-more` and `path-more`, dashed rather than solid because they show
more of what is already on the page rather than acting on it. They did
not match each other before (one dashed on `--panel` at `.8rem`, one
dashed on transparent at `.82rem`); they do now. §6d names all four:

| grade | look | drawn by |
|---|---|---|
| standing | `--muted-bg`, solid, 3px | copy, investigate, the rail's steps |
| quiet | transparent, solid, 3px | collapse, chapter-open, json-toggle, twin-toggle, focus-back, expand-table |
| reveal | transparent, dashed, 3px | fold-more, path-more |
| door | transparent, solid, 50% | `UX-317`'s `?` |

`button.collapse` had `border: none`, which is this item's own complaint
one scale down — a control inside a heading is still a control. Giving
it the resting appearance is what took `macro_micro` from four to three.

### The guard

`tests/unit/test_every_control_has_a_resting_appearance.py`, six
clauses, 6.7s (medium by measurement, `tests/tiers.py` updated): the
pages really have controls; nothing renders `outset`; every control is
one of the four **named** grades; the count stays at four; every grade
is actually used; and nothing animates or casts a shadow.

The third clause matters more than the fourth. A bound alone would let
one grade drift into another's look and still pass, which is how twelve
arrived — so the grades are read as a set, not counted.

### Falsification

| # | mutation | result |
|---|---|---|
| B1 | delete the base `button` rule (the whole fix) | **red** — 3 clauses, including `nothing_renders_the_ua_button` |
| B2 | `json-toggle` gets a 6px radius, so quiet drifts | **red** — the named-grades and the count clauses |
| B3 | a `transition` creeps onto `button` | **red** — `no_control_animates_or_casts_a_shadow` |
| B4 | reveal loses its dashed border, so a grade goes unused | **red** — `every_grade_is_actually_used` |

### Deviation from the Required Fix

Two, both stated.

**Three grades became four**, for the reason above: reveal is a real
distinction with two members, and deleting it to hit a number would be
the number driving the design.

**The acceptance mutation changed meaning.** The item says a classless
`<button>` must redden the guard. After this it must *not*: a classless
button now gets the standing grade, which is the whole point of a base
rule. The mutation that carries the item's intent is B1 — remove the
base rule and the classless controls fall back to the UA button, which
is exactly how the original 52 arrived. B1 is what the guard is held to.

### What was not changed

§6a's refusal of motion and ornament stands: zero transitions, zero
shadows, both now asserted rather than merely recorded. No palette
token changed. No section moved.

### The suite

```console
$ make lint
All checks passed!

$ make test
5421 passed, 28 skipped, 1 warning in 263.45s (0:04:23)
```
