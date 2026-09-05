# UX-335: reading 'start_time' of undefined

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-334 (the net that catches this class) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome (round 48, 2026-08-27) — 🟢 Done

### The field string: the filing's claim, corrected

The filing says `start_time` **"appears nowhere in this codebase and
never has (zero hits in every served asset, the built export, and
`git log -S` over all history)"**. Two of those three are right and
the blanket claim is not. Measured:

```text
bga/viewer/**                     0 hits
the built export (golden)         0 hits
git log -S"start_time" --all     10 commits
bga/ and tools/, as an identifier 4 sites
  tools/bst_run_context.py:193      start_time=args.start_time
  tools/bst_extract_run.py:787      start_time=args.start_time
  tools/bst_log_to_chrome_trace.py  _resolve_start_time_us(args.start_time…)
  tools/bst_run_wrapped.py:12       (in a comment about BuildStream's own)
```

So `start_time` is a **Python argparse dest** in three CLI tools and
appears nowhere the browser executes. The verdict the filing reached
stands: the field error came from outside bga's viewer, a browser
extension's content script on the localhost page being the likeliest,
and the check on the field machine is still an incognito or
extension-free profile. Only the phrasing was too wide, and it is
corrected here rather than repeated.

### The class, reproduced

Serving the golden run with one `null` row in `store.json`:

```text
before   refused : "Could not load this run
                    TypeError: Cannot read properties of null
                                (reading 'elements')"
         sections: 0

after    refused : null
         sections: 29        the same 29 a healthy store renders
         trend   : "3 snapshots · all finished · 1 row in this store
                    could not be read and is not drawn"
         history : "No history for this element: 1 row in this store
                    could not be read, and no other snapshot carries
                    per-element history."
```

Twenty-nine sections of correct analysis discarded because one row of
one **optional** payload was malformed.

### The finding the filing did not have

**The page-wide catch made this class invisible to `UX-334`'s console
guard.** The boot above - the one that showed the reader nothing at
all - came back with **zero console errors and zero CSP violations**,
because the page caught the throw and rendered a banner. A net built
one round earlier for exactly this class could not see it.

So `contained()` calls `console.error` as well as drawing its card.
That is not decoration: it is what makes the round-47 guard the net
the round-46 filing said it would be. Mutation M4 (drop the
`console.error`) reddens, so the property is held rather than assumed.

### Where the boundary is

- **A renderer that throws** loses its section to an inline card
  naming the *payload* it was drawn from - the section is the
  consequence, the document is the cause, and a reader told only
  "overview failed" has nowhere to go next.
- **A load failure still stops the page.** A report that will not
  parse is not a report and there is nothing to render around it. Its
  banner carries `data-page-failed`, because a section's card wears
  the same `.verdict.refused` styling - both say "this did not work",
  and only one of them means the page is empty.
- **The two null-row sites state the absence** rather than being
  caught: containment is the net, not the fix. Both boots in the
  guard assert `data-section-failed` is *absent*, so a future
  renderer that starts throwing cannot hide behind the card.

### Mutations verified red and reverted (7)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | `elementHistory` reads the row before checking it (the filed defect) | 5 |
| M2 | `renderTrend` stops filtering unreadable rows | 5 |
| M3 | `renderOverview`'s call site is no longer `contained` | 1: the containment probe, on the page refusing as a whole |
| M4 | `contained` stops telling the console | 1: the probe's console assertion — the `UX-334` link |
| M5 | the page-wide banner loses `data-page-failed` | 1 |
| M6 | the failure card stops naming its payload | 1 |
| M7 | the load failure is `contained` instead of refusing the page | 1 |

**M5 is the one that changed the work.** On its first run it reddened
**nothing**: the marker distinguishing a page failure from a section
failure existed and no clause read it, which is a distinction the next
round deletes. `TestTheLoadFailureIsStillAPageFailure` was written for
it, and writing it turned up a second fact worth recording: a
`report.json` of the *wrong shape* (`{"not": "an analyze document"}`)
is **not** a load failure at all - the page renders it as a document
with nothing in it, silently. A truncated write (`null`) is, and that
is what the clause uses.

### The race this item's own guard introduced

The containment probe has to make a renderer throw, and the first
draft wrote it into the checked-out `bga/viewer/views.js`, restoring
it in a `finally`. Under `-n auto` that is shared state: another
worker booted a page while the probe was in the file, and the full
suite failed **in this file** on a defect belonging to another test's
timing.

It is the same shape as the `probe/v3` race `UX-336` left behind and
this round fixed two files away - written again, one item later. The
probe copies the viewer directory now and points `ASSET_DIR` at the
copy for the length of one test; every other worker is a process still
reading the real one. Confirmed by two consecutive full runs at `-n
auto`, 4,200 passed each.

The lesson worth keeping is not "copy the directory". It is that **a
guard which writes into the tree it guards is a race by
construction**, and `-n auto` turned the latent ones live all at once.
Two found this round; the third will not announce itself either.

### Deviation from the Required Fix

- The Required Fix says the class "is held by `UX-334`'s console
  guard". It is now, but only because this item added the
  `console.error` - before it, the console guard was structurally
  incapable of seeing this class. Recorded because the filing states
  it as a property already available rather than one to build.
- The degenerate fixture offers three shapes (`null_row`,
  `string_row`, `row_without_snapshots_key`) where the filing names
  one. The extra two cost nothing - they are the same `typeof` check -
  and `string_row` is a real double-encoding shape one character away
  from the filed one.
