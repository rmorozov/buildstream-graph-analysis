# UX-211: a link that shows what I was looking at

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-199 (the anchors), UX-205 (the filters), UX-208 (the top-N presets) | **Topic:** viewer

## Motivation

`nav.js`'s own comment sells the section ids as something that
"can be pasted into an issue" — and that promise stops at the
anchor. The state a reader builds while investigating — a filter
narrowing 1,202 rows to nine, a `> 5s` threshold, a sort, the
collapsed sections, the unfolded middle of the chain — lives in
DOM state and `localStorage`, so the pasted `#floors` link opens
the unfiltered wall for whoever clicks it. The round-23 review's
"remember collapsed/expanded state more aggressively" is
`localStorage` thinking: it remembers for *me*, on *this browser*.
The house ethos — evidence you can paste — wants the view state in
the link.

The export makes this sharper: an exported report is *for*
attaching to an issue, and `file://` documents get no storage at
all in some browsers (`safeStorage` already defends against the
throw) — the URL fragment is the one channel that works
everywhere, needs no server, and travels with the file.

## Required Fix

Serialize the view state into the location hash — collapsed
sections, per-table filter text, thresholds and sort, top-N
preset, the chain fold — and restore it on load. The hash wins
where it speaks; `localStorage` remains the default where it is
silent. Copy affordance: a "copy link to this view" control beside
the TOC, so the reader does not hand-edit fragments.

## Out of Scope

- Server-side state, sessions, or anything that outlives the URL.
- Cross-run state (a hash from one run opening another run's
  report applies what it can and drops the rest, silently).

## Acceptance Test

Set a table filter and collapse two sections → the hash reflects
both; reloading with that hash restores the same shown-row badge
and the same collapsed set (asserted; mutation: drop the restore
path → red). A hash-free load behaves exactly as today. The copy
control yields a URL that reproduces the view in a fresh session
(no `localStorage`). Works in an export from `file://`. Page-size
guard holds.

---

## Outcome (round 23)

**Status:** 🟢 Done.

`bga/viewer/viewstate.js` captures the view off the document and puts
it back by driving the controls — setting the value and firing the
event each control already listens for, so there is no second code path
that can disagree with the first. Serialized: the collapsed set (`c`),
per-table filter (`f.`), per-column thresholds (`t.`), sort (`s.`),
Top-N preset (`n.`) and the disclosures a reader opened (`o.`).

**The anchor is not sacrificed to the state.** `#floors` still means
exactly what it meant — the browser's own scroll-to-id still fires for
it, and every link already pasted into an issue still works. State
follows a `~`, a character no section key contains, and a stateless link
comes back byte-identical to today's. Asserted both ways.

**"The hash wins where it speaks, storage remains the default where it
is silent"** turned out to be the clause with a trap in it. A naive
restore reads an absent `c` as "nothing is collapsed" and *expands* what
the reader's own storage had shut — the opposite of the rule. So `c` is
authoritative only when the fragment carries it, and `captureView`
emits `c` (empty if need be) as soon as the view says anything at all,
so a reader who expands everything and then filters still hands over a
link that pins the collapse set. Both halves are guarded on a page whose
section is already shut: silent fragment leaves it shut, `c=` opens it.

Cross-run keys are dropped in silence, as the Out of Scope asks — a
fragment naming a table this report does not have applies what it can
and returns the list of what it applied, which is what the guard reads.

The copy control sits beside the contents, and `viewLink` is asserted
to produce a `file://` URL carrying the filter — the export is the case
this item exists for, and it is the one where `localStorage` may not
exist at all.

**Deviation from the Required Fix:** none.

**Page-size guard:** see the note in
`test_the_payload_dwarfs_the_page`. This module is 5,055 B of the page
after comment-stripping, and it is part of why the ceiling moved.
