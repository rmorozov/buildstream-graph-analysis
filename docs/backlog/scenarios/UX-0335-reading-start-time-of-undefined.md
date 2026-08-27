# UX-335: reading 'start_time' of undefined

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-334 (the net that catches this class) | **Serves:** R1 | **Topic:** viewer

## Motivation

The user's field report: `Cannot read properties of undefined
(reading 'start_time')` in the viewer console on a real capture.

Investigated to an honest split verdict. The literal string:
**`start_time` appears nowhere in this codebase and never has**
(zero hits in every served asset, the built export, and
`git log -S` over all history; zero exceptions booting every page
live) — the field error was thrown by something outside bga's
viewer, most likely a browser extension's content script running
on the localhost page. Worth one check on the field machine
(incognito or an extension-free profile) before hunting further.

**But the failure class is real and reproduced**: one `null` row
in `store.json` collapses the *entire* report to "Could not load
this run — TypeError: Cannot read properties of null (reading
'elements')" — `views.js:2376` indexes the row before checking
it, `:270` would throw next, and `boot()`'s single page-wide
try/catch (`app.js:2527`) makes any one section's throw everyone's
funeral. The shim guards can never see it: under the shim,
`getElementById` returns null and boot never runs.

## Required Fix

Error containment moves to the section boundary: a renderer that
throws loses *its section* to an inline error card naming the
payload path, never the page (boot's page-wide catch remains only
for load failures); the two null-row sites state the absence per
the grammar; a degenerate-store fixture joins the suite so both
the shim path (fed directly) and the browser walk see it; and the
class is held by `UX-334`'s console guard. The field string's
external origin is recorded here so the next reader does not
re-hunt it.

## Out of Scope

- Blanket defensive `?.` sprinkling — the fix names the shape and
  states the absence; it does not hide every future one.

## Acceptance Test

The triggering payload shape renders its absence sentence (no
throw, asserted in the shim on the new fixture); the console
guard on the browser walk is green; mutation: restore the
unchecked read → the shim clause and the console clause both red.
