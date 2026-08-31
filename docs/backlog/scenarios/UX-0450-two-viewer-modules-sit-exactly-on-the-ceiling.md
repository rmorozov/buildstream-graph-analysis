# UX-450: two viewer modules sit exactly on the line-count ceiling

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 70, `UX-429` adding four lines to `structured.js` | **Serves:** the next round that adds anything to the viewer's two largest modules | **Topic:** guards

## Motivation

`UX-337` split the viewer along its seams and set a 1,500-line ceiling
per module, guarded by
`test_the_viewer_splits_along_its_seams.py::test_every_viewer_module_is_under_the_ceiling`.
Two modules now sit **exactly** on it:

```console
$ wc -l bga/viewer/*.js | sort -rn | head -4
 11706 total
  1500 bga/viewer/structured.js
  1500 bga/viewer/app.js
  1267 bga/viewer/element.js
```

Both got there the same way, a round apart. `UX-431` added one line to
`app.js` at 1,499 and paid for it by merging two declarations onto one
line and shortening a comment. `UX-429` needed four lines in
`structured.js` — a `classify` option and a dispatch branch — and paid
for them by folding two option lines into one and **deleting the
branch's explanatory comment**, which then had to be re-homed in
`controls.js`.

Neither payment made the code better. The second one made it slightly
worse: a dispatch branch in a §1 table now carries no note where every
other branch around it does, and its reason lives in a different file.

**The ceiling is working.** It is meant to force a split rather than
let a module absorb, and this is it forcing one — twice, on two
modules, with the cost currently being paid in comments instead. What
has not happened is the split, because each round in turn has had a
task to finish and a module split is a design task of its own.

## Required Fix

Decide, and do one of:

- **Split both modules along a seam**, the way `UX-337` split the
  original two — and name the seam, because "the file is long" is not
  one. `structured.js` holds §1's dispatch *and* the whole table
  machinery (tools, filters, presets, focus); `app.js` holds the boot
  and the section walk. Either could be two files.
- **Or move the ceiling**, with a reason that is not "we hit it" — the
  count `UX-337` chose was a judgement about what one reader can hold,
  and if 1,500 was the wrong number the item should say what the right
  one is and why.

Whichever, the comment `UX-429` deleted goes back.

## Out of Scope

- **Any behaviour change**: this is a move, and a move that renders one
  pixel differently is not a move. The export must come out
  byte-identical, which is what the acceptance test below reads.
- **The other five modules**: none is within 200 lines of the ceiling,
  so none of them is under the pressure this item is about.

## Acceptance Test

```bash
wc -l bga/viewer/*.js | sort -rn | head -5
make test
```

No module within 100 lines of the ceiling, the suite green, and the
export byte-identical to before the split — the property that says a
move was a move.

## Outcome

_Not started._
