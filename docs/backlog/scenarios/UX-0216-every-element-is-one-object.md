# UX-216: every element is one object, and its links resolve

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-215 (the join it renders), UX-208 (the affordance it repairs), UX-199 (anchors)

## Motivation

**Clause 1 is a live defect, and it is mine.** `UX-208` gave every row
of an element-column table a generic Inspect anchored at
`#${cssId(uid)}` (`app.js:306`, `app.js:111`). Nothing in the page ever
sets that id. Rendered `examples/06` and resolved every anchor:

```text
inspect links         19
distinct targets      11   #element-core-bst, #element-lib-b-bst, …
ids present in page   21   every one a section key: summary, headline,
                           floors, signals, critical_path_detail, …
unresolvable          11 of 11
```

`wireJumpBox` scrolls by `[data-element="…"]` and works; the anchor
`UX-208` shipped uses a different scheme and matches nothing. The
guards written for it asserted the affordance *exists* — never that it
*arrives*.

**Clause 2 is what the anchor should land on.** An element uid appears
in findings, the critical path, three signals tables, the blast tree,
the top actions and the trace context. A reader who wants "everything
about `core.bst`" reads six sections and joins them by hand. With
`UX-215` publishing the join, the page can render that row once, as an
object, and point every occurrence at it.

## Required Fix

1. One `<section data-section="element-<uid>" data-element="<uid>">`
   per element the report actually discusses, with `id` = the anchor
   `cssId` already generates — so every Inspect resolves, by
   construction rather than by a second mechanism.
2. It renders `UX-215`'s published row and nothing derived: path share,
   duration, what a fix is worth, blast radius, achieved parallelism
   and its Plane 2 evidence, the findings that name it, and the
   investigate button where `run.has_timeline`.
3. Every rendered occurrence of an element uid — path box, table cell,
   finding element list, top action, blast row — links to it.
4. Path boxes keep `UX-208`'s popover and gain the link (the popover
   answers "what is this", the link answers "show me everything").

## Out of Scope

- **A drawer or overlay.** Declined deliberately: overlay machinery is
  the one part of this page that would not survive an export opened
  from a downloads folder, a print, `filter: grayscale`, or a pasted
  anchor. A section is linkable, printable, exportable and collapsible
  by machinery that already exists — and it makes `UX-208`'s anchor
  resolve as a side effect.
- Rendering a section per element on a 4,000-element report. Only
  elements the report *discusses* (path, findings, top actions, blast,
  latent heavies) get one; the cap and its elision follow `UX-187`.
- Focus mode (`UX-222`), which builds on this.

## Acceptance Test

On `examples/06` and on the golden fixture: **every** `href` beginning
`#element-` resolves to an `id` present in the same document — asserted
by resolving all of them, which is the check that was missing. Zero
unresolvable, on both fixtures, served and exported.

Mutations, each asserted red: change `cssId`'s replacement so the id
and the href disagree → the resolution guard fails (this is the exact
defect, so it must fail); drop the element section for an element that
a finding names → the "every occurrence links to something" guard
fails. On a report with no Plane 2, the section renders its Plane 1
half and no empty Plane 2 rows. Page-size guard holds.

---

## Outcome (round 25)

**Status:** 🟢 Done.

**Clause 1, the defect.** Measured on `examples/06` before and after,
by resolving every anchor rather than counting affordances:

```text
before   19 element links, 11 distinct targets, 11 of 11 unresolvable
after    55 element links, 11 distinct targets,  0 unresolvable
```

The acceptance is resolution, not presence — which is the whole lesson
of the defect, since `UX-208`'s guards asserted presence and shipped
nineteen links to nowhere. And the two spellings are now **one
expression**: `app.js`'s `cssId` delegates to `views.js`'s
`elementAnchor` rather than repeating the regex, because a link and its
target drifting apart *is* this item. The mutation that proves it is
not "rename the anchor" — it is *re-duplicating the expression with a
different character class*, which is exactly how the original defect
would recur, and it reddens four guards.

**Clause 2, the object.** One `<section>` per element the report
discusses, carrying `UX-215`'s join row where Plane 2 saw it — path
share, worth fixing, blast radius, cores busy, jobs asked for, peak RSS
— the findings that name it, what `entering` says joins the path if it
is fixed, and an investigate button where there is a timeline. Every
occurrence links to it: table Inspects, path boxes, finding element
lists, decision-panel actions, blast-tree rows.

**The cross-reference is read off the rendered document**, not from a
list in the viewer: whatever else drew a `data-element`, the section
links back to the section that drew it. So a view added later joins the
cross-reference with no edit here — the property `UX-193` bought for
the sections themselves.

**The drawer stayed declined**, and the absence is asserted rather than
promised: no `dialog`, no `showModal`, no `position: fixed` in either
the module or the stylesheet. (The guard deliberately does *not* ban
`z-index` — the sticky table header has had one since `UX-205` and it
is not an overlay. A guard that fires on pre-existing correct code
teaches people to disable guards.)

**Two invariants the repository's own guards defended.**
`UX-199`'s "a section's id *is* its key" caught `data-section="element-
base.bst"` against `id="element-base-bst"`; the key is the sanitised
spelling now, and the section carries a `data-toc-label` so the
contents reads `core.bst` rather than "Element core bst". And
`UX-187`'s elision rule: the sections are capped at 24 with a note that
names its own count.

**The page-size guard did not hold, for the third round running — so
what it measures changed rather than the number.** A byte ceiling was
crossed by ordinary feature work in rounds 23, 24 and 25 and raised
twice; a number that moves every time a feature lands is measuring the
calendar. It is now three guards: composition (the page *is* the
checked-in modules plus the stylesheet — the one that can tell 6 KB of
feature from 6 KB of vendored library), **Direction 7's ratio measured
at the scale the rule names** (1,000 elements: 691,401 B of data
against a 97,488 B page, **7.1x**, asserted at 4x so growth does not
trip it and a framework does), and a loose 120,000 B backstop whose
crossing would mean something structural. The small fixtures invert the
ratio and always did — that is a property of small reports, not of the
viewer, and is why the absolute ceiling was the wrong instrument.

Eight mutations, each verified red: both forms of the anchor defect;
the sections not rendered; the id dropped; the cross-reference dropped;
a fact recomputed rather than published; the cap removed; findings not
reaching the section.

**Deviation from the Required Fix:** none.
