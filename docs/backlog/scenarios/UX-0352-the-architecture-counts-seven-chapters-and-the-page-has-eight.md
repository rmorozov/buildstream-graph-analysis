# UX-352: the architecture counts seven chapters and the page has eight

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-286 (the report reads in chapters) | **Serves:** anyone reading the architecture to learn what the viewer does | **Topic:** docs

## Motivation

Found by review 5, checklist item 1 - *open the module the chapter
names and check the mechanism*.

`docs/design/architecture.md` says, of the viewer:

> `bga/viewer/chapters.js` groups them into **seven** chapters, each
> named for a question the reader has

The module has eight, and has had eight since the commit that
introduced it:

```text
$ node -e 'import("./bga/viewer/chapters.js").then(
      m => console.log(m.CHAPTERS.length, m.CHAPTERS.map(c => c.id).join(",")))'
8 decide,change,compare,time,machine,elements,believe,run

$ git show 3c4a96b:bga/viewer/chapters.js | grep -c '^    id: "'
8
```

`3c4a96b` is `UX-286`, the round the sentence was written in. So the
number was never true, and three reviews have read past it - which is
the shape of error a count in prose has: nothing reads it but a human,
and a human checking the eight-row table below the sentence sees eight
rows and no contradiction.

The neighbouring figures in the same bullet are *not* this defect:
"forty-eight sections averaging 0.24 screens" and "18.51 screens to
18.10" are attributed to `UX-286`, round 39, and a dated measurement
that a later round moved is a record rather than a claim. The chapter
count is written in the present tense about what the module does now.

## Required Fix

The sentence names what the module holds. Derived rather than counted
by hand where that is cheap: the viewer already publishes `CHAPTERS`,
`tests/unit/test_the_report_has_chapters.py` already asserts the page
draws six to eight of them, and a guard that reads the number out of
the prose and compares it to `CHAPTERS.length` is the same shape as
`test_the_architecture_names_the_commands.py`, which `UX-322` added
for the CLI table after the same drift happened three times.

## Out of Scope

- Re-measuring the screen figures in that bullet. They are dated to
  their round and `UX-347` re-measured the document under folding;
  restating round 39's numbers as round 53's would erase the history
  the attribution carries.
- The chapter table itself. Declined because it is correct:
  eight rows, one per member of `CHAPTERS`, in the module's
  order - the sentence above it is the only thing that
  disagrees with the module.

## Acceptance Test

`architecture.md`'s chapter count equals `CHAPTERS.length`, asserted
by a guard that reads both - so the next chapter added or removed
reddens rather than waiting for a fourth review to read the sentence.
