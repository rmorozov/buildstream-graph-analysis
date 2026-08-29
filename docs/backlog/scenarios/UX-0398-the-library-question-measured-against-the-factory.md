# UX-398: the library question, measured against the factory

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-397 (the filed question), UX-392 (the filters it would buy), UX-367 (the volume budget that arbitrates) | **Serves:** R8, and anyone deciding what this page may depend on | **Topic:** viewer

## Motivation

`UX-397` files the Tabulator question with one argument for adoption:
"a library answers sorting, filtering, and virtual scrolling at 1,200
rows **in one dependency rather than in twenty-one modules**."

Round 64 measured that premise, and it is wrong:

```text
$ grep -l 'renderTable\|buildTable' bga/viewer/*.js
bga/viewer/app.js          (the caller)
bga/viewer/primitives.js   (the factory's parts)
bga/viewer/structured.js   (the factory)
```

Every one of the 31 tables flows through one factory —
`buildTable`/`renderTable` in `structured.js` — which already
implements declared column specs, declared-not-sampled sorting
(`UX-284`/`UX-289`), the 22 preset menus (`presetColumns`), Top-N,
fold-the-middle, the density strip and the copy control. The 21
viewer modules *consume* the factory; none hand-rolls a table. So the
marginal cost of `UX-392` (a filter on all 31 tables) is one change
to one factory, and every future table gets it free — which is
exactly the economics a library promises, already owned.

The against-side stands as `UX-397` filed it (a ~400 KB library on a
477 KB self-contained export; four-CDN CSP so it ships inside the
file) and gains three arguments the filing did not price:

1. **The styleguide is law over this DOM.** `shapes.js classify()`,
   the §2a/§3a/§3b guards and the conformance walks all assert the
   page's own markup. A library's DOM either fails those guards or
   gets wrapped until the visual contract is re-implemented on top of
   it — the "reimplementing the world" cost, inverted.
2. **The console guard would light up.** `UX-334` holds every served
   page to zero CSP violations; table libraries write inline style
   attributes as a matter of course.
3. **There is no toolchain to carry it.** The repo has no
   npm/bundler/lockfile; one runtime dependency imports the whole
   supply-chain and upgrade question the page was built to avoid
   (`UX-296` — the view that parses nothing).

## Required Fix

Record the decision in `UX-397` and replace the standing question
with a standing **rule**, in `docs/design/styleguide.md` (one short
section beside §6's export rules):

- A JS dependency is admitted only when a required behavior
  (a) cannot be met by the factory plus a platform primitive within
  the volume budget — shown by a measured before/after of the
  export's page half, the `UX-382` split — and (b) the library's
  wiring-plus-conformance cost measurably undercuts the in-house
  cost. The trackevent precedent (`tools/native_trace/trackevent.py`
  instead of a protobuf dependency) is the named prior.
- The factory measurement above is pasted beside the rule, so the
  next person to ask starts from the number, not the impression.

## Out of Scope

- Adopting or rejecting any specific library forever — the rule
  prices future candidates; it does not blacklist them.
- The rail pin and the other half of `UX-397` — that half stands on
  its own.
- Implementing `UX-392`'s filters — this task only establishes where
  they land (the factory); the filing itself stays the work order.

## Acceptance Test

- The styleguide carries the rule and the pasted measurement; the
  docs guards pass.
- `UX-397`'s file records the decision under its "Falsification"
  clause ("the decision is recorded here either way"), with the
  export's measured page and data halves beside it.
