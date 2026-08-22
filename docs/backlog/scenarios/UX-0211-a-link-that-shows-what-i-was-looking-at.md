# UX-211: a link that shows what I was looking at

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-199 (the anchors), UX-205 (the filters), UX-208 (the top-N presets)

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
