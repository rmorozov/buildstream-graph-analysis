# UX-225: the working set travels in the link

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-211 (the fragment channel), UX-216 (the element object) | **Topic:** viewer

## Motivation

`UX-211` put the *view* in the link — filters, thresholds, sort,
collapse. What is nowhere is the *decision*:

> I am working on `core.bst`. I already looked at `lib-b.bst` and it is
> not worth it. `codegen.bst` is next.

That is the state a reader rebuilds from scratch on every round of the
loop, and it is the state they cannot hand to anybody else. The tool
re-derives the same ranking every run and has no idea which parts of it
the reader has already dealt with — so round three of an optimization
reads exactly like round one.

The channel already exists and is the right one. Not `localStorage`:
that remembers for *me*, on *this browser*, and an exported report
opened from `file://` may get no storage at all. Not the store: the
viewer has no write method and must not grow one — the security posture
is an allowlist of reads, and that is worth more than this feature.
The fragment is shareable, survives `file://`, and needs no server.

## Required Fix

1. Each element carries **working**, **done** or **set aside**, set
   from `UX-216`'s section and from any element occurrence.
2. The set travels in `UX-211`'s fragment, so "here is where I am"
   is a link, and a teammate opening it sees the same three marks.
3. The decision panel and the horizon (`UX-219`) show the marks: an
   element already marked *done* is still ranked and still shown — it
   is annotated, never silently dropped. A ranking that quietly hides
   what the reader dismissed is a ranking they cannot check.
4. A one-line summary — *"2 working · 1 done · 1 set aside"* — with a
   clear control, and the marks survive a reload from the same link.

## Out of Scope

- Any server-side or cross-session persistence. No write method, no
  sessions, nothing that outlives the URL. A reader who wants it to
  survive keeps the link, which is the same thing they already do with
  a run identity.
- Re-ranking on the marks, or removing marked elements from any list.
- Marks meaning anything to `bga analyze`. This is the reader's
  annotation, not an input to the analysis.

## Acceptance Test

Mark two elements, copy the link, rebuild the page in a fresh context
with no storage, apply the fragment: the same two elements carry the
same marks and the summary reads the same. A marked-done element is
still present in the top actions and in the horizon, annotated.

Mutations, each asserted red: store the marks in `localStorage` instead
of the fragment → the no-storage round-trip fails; filter marked
elements out of the ranking → the "still ranked, only annotated" guard
fails. Works from an exported `file://` report. Page-size guard holds.

## Outcome (round 26)

The channel decision is the item, and it is asserted rather than
described. `focus.js` contains no `localStorage`, `sessionStorage` or
`indexedDB` — checked against the source with comments stripped first,
because the module's own header explains at length *why* storage is the
wrong channel here and a guard that fired on the explanation would be
rewarding silence about the decision.

A mark lands on **every occurrence** of its element, and the round-trip
is guarded in a genuinely fresh context with nothing remembered: capture
the query off one document, build a second from scratch, apply, and read
the marks back off the rendered result.

```text
mk=app.bst:working,core.bst:done   →   1 working · 1 done
```

Clause 3 is guarded as an absence too. `applyMarks` annotates and never
filters: the element count is unchanged after marking, and a marked
element is still present. **A ranking that quietly hides what the reader
dismissed is one they cannot check** — so the top actions and the
horizon show the mark and keep the row.

`views.js` imports nothing by design (UX-193's rule about the cycle
between it and `app.js`), so it spells out the three-mark vocabulary
rather than importing it. That is a duplication, so it is guarded: a
test asserts the two lists are identical, and reddens when either
drifts.

**Mutations verified red and reverted:** filter marked elements out of
the ranking (4 guards — this item's own second mutation); keep the marks
in `localStorage` instead of the fragment (3 — its first); let the mark
vocabulary in `views.js` drift from `focus.js` (2).

**Deviation from the Required Fix:** none. Clause 1 says the marks are
settable "from `UX-216`'s section and from any element occurrence"; the
buttons are rendered on the element section, and the delegated listener
means any occurrence that grows a control later is already wired.
