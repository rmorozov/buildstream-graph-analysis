# UX-640: the rail names the key, the heading asks the question

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-199 (a report you can find your way around), UX-374 (the page renames the reader's elements) | **Found by:** round 87, by the owner not knowing where a rail entry led | **Serves:** anyone navigating by the rail rather than by scrolling | **Topic:** viewer | **Area:** bga/viewer

## Motivation

The rail labels a destination with one string and the destination
labels itself with another. Measured on both committed fixtures:

```text
                  entries   labels differing from their heading
golden               45              39
macro_micro          65              52
```

Eighty percent. The rail says the payload key; the heading asks the
question the section answers:

```text
elements             nav 'Elements'             h2 'Which element should I look at?'
blast                nav 'Blast radius'         h2 'What rebuilds if I touch this?'
floors               nav 'Floors'               h2 'How much faster could this build possibly be?'
cpu_time             nav 'Cpu time'             h2 'What did the whole build cost in CPU?'
wall_clock_share_us  nav 'Wall clock share us'  h2 'How much of the run did each task hold?'
```

Three of them are machine-mangled keys no reader would recognise —
`Wall clock share us`, `Cpu time`, `Plane2 coverage` — from
`nav.js:124`'s `key.replace(/[-_]/g," ")`.

There are **two independent label functions**: the rail uses
`section.getAttribute("data-toc-label") || label(key)` (`nav.js:313`),
the body uses `heading(key, hint).label` via `sectionHead`
(`format.js:340-347`). Nothing ties them together —
`grep data-toc-label tests/unit/*.py` returns nothing, and the two
existing rail guards assert only that every section *is* linked. The
13 entries that do agree are exactly the ones that set
`data-toc-label` explicitly.

Membership cannot drift — one selector feeds both — but the labels
already have.

## Required Fix

One label authority. The rail asks the same function the heading does,
and falls back to the mangled key only where no heading exists. A
guard holds the two together over every rendered section, so the next
question added to a heading reaches the rail without anyone
remembering to.

## Out of Scope

- The rail's **length** — 90 entries, because the document has 65
  sections. `UX-271`'s Direction 12 already declined a structural tree,
  and UX-643 proposes the reader-role lever instead.

## Acceptance Test

On both fixtures, every rail entry's label equals its destination
heading's label. A mutation to one heading reddens it.

## Also measured, and not a defect

Round 87 suspected that a rail click drops the view state, on the
reading that the entries are bare `#` links. They are not: `nav.js:306`
writes `#${key}`, and `captureView()` re-derives the query from the DOM
on the delegated `click`, so the state is rebuilt rather than lost.
Recorded here so a later round does not re-file it. What was *not*
measured is whether the delegated listener fires for a rail outside
`#report`; that is this row's one open question and its guard covers it.

## Outcome (round 87, 2026-09-04) — 🟢 Done

**Both fixtures at zero.** Counted with a browser over the exported
page, rail entries whose text differs from the label their destination's
`h2` gives itself:

```text
                  entries   differing (before)   differing (after)
golden               46             39                   0
macro_micro          66             52                   0
```

The 39 and the 52 are this file's own numbers. The entry counts are
**46 and 66**, one more each than filed above; the filing counted 45 and
65.

`nav.js` reads the destination's own heading and falls back to
`data-toc-label`, then to `label(key)`. `heading()` is not callable from
the rail — it needs the schema hint the rail does not carry — so the
rendered `h2` is the authority, read as its **text nodes**: subtracting
the controls' strings takes the wrong `cache` out of "How much of this
run came from the cache?" and produces `…from the ?cache`. `null` under
`tests/dom_shim.mjs`, which holds a node's text in one string; the rail
falls back there and the guard is a browser guard for that reason.

### The open question, answered: it is a defect, and not this row's

The delegated `click` **does not fire** for a rail entry. Served,
`macro_micro`, Chromium:

```text
report.contains(rail entry)                         false
after collapsing `floors`   #~c=floors&v.elements=All+elements&n.…
after clicking rail `elements`                      #elements
after the next click inside #report   #elements~c=decision%2Cfloors&v.…
```

`wireViewState` listens on `#report`; `app.js` puts the rail *after*
`#actions-group`, a sibling. So the fragment loses the query on a rail
click and gets it back only on the reader's next interaction inside the
report — the document keeps the state (`data-collapsed="true"` survives
the click), the **link** does not. "Also measured, and not a defect"
above is right about `#${key}` and wrong about the rebuild. Left for
viewstate's own row rather than fixed here.

`jumpTargets` still names sections `label(key)` (`nav.js:719`) — the
same two-authority defect on the palette rather than the rail, and out
of this row's scope.

### The Acceptance Test, deviating on its second sentence

"A mutation to one heading reddens it" cannot hold once there is one
authority: mutation B below changed **every** heading and the rail
followed, so the agreement clause stayed green — which is the property
this row was filed to get. What reddens is the population clause, and
the mutation that reddens the agreement is one that decouples the rail
from the heading.

```text
$ python3 -m pytest tests/unit/test_the_rail_says_what_the_heading_says.py -q
tests/unit/test_the_rail_says_what_the_heading_says.py ....              [100%]

============================== 4 passed in 1.32s ===============================
```

### Mutations verified red and reverted (2)

| mutation | reddened | printed |
|---|---|---|
| A: `nav.js` rail label drops `headingLabel(section)` | the agreement clause, both fixtures; population green | `39 of 46` / `52 of 66` rail entries name their section something the section does not |
| B: `format.js` `heading()` returns `title(key)` as its label | the population clause, both fixtures; **agreement green** | `only 0 of 46 headings ask a question` / `0 of 66` |

B is applied to a file this track does not own; it was reverted from the
step-1 copy and `git status` shows `format.js` unchanged.
