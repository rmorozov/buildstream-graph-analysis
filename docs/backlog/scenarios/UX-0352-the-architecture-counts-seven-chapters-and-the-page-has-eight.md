# UX-352: the architecture counts seven chapters and the page has eight

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-286 (the report reads in chapters) | **Serves:** anyone reading the architecture to learn what the viewer does | **Topic:** docs

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
- ~~The chapter table itself.~~ **Corrected while doing the work:
  there is no chapter table.** This entry was written during review 5
  and asserted rows nobody had counted; the bullet is prose from end
  to end. It is also the explanation the filing was missing for why
  three reviews read past the number - there were no rows to count
  against the word.

## Acceptance Test

`architecture.md`'s chapter count equals `CHAPTERS.length`, asserted
by a guard that reads both - so the next chapter added or removed
reddens rather than waiting for a fourth review to read the sentence.

## Outcome (round 54, 2026-08-28) — 🟢 Done

### The gap

```text
architecture.md:718   groups them into seven chapters
chapters.js           8  decide,change,compare,time,machine,elements,believe,run
3c4a96b               8  (the commit that introduced the module and wrote
                         the sentence)
```

The sentence now says eight.

### The guard reads the number, and asks the module

`_claimed` finds `into <word> chapters` and resolves the number word -
the prose spells small numbers as words, which is the house style and
not something a guard should make a document give up. `_module` asks
`chapters.js` through node rather than counting `id:` lines: the file
also exports an `UNCHAPTERED` fallback with an id of its own, so a
regex over the source counts **nine** and would call a correct
document wrong.

### The Out of Scope entry was wrong, and correcting it explains the item

This filing's second Out of Scope entry said the bullet's chapter
*table* was correct and therefore excluded. **There is no chapter
table.** The bullet is prose from end to end; the entry was written
during review 5 and asserted rows nobody had counted. It is struck
through above with the correction.

It is also the explanation the filing was missing. The obvious question
about this item is how a wrong count survives three reviews of a
document read line by line - and the answer is that there was nothing
beside it to disagree with. A wrong number over a right table is a
contradiction a reader trips on; a wrong number alone is just a
number.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `6ce1b0a`.

| # | mutation | reddened |
|---|---|---|
| R1 | the prose says seven again — the defect itself | *"architecture.md says 'into seven chapters'; `chapters.js` exports 8"* |
| R2 | a ninth chapter added to the module, prose untouched — the direction a later round would actually break it in | the same clause, naming the nine ids |
| R3 | the sentence reworded past the pattern (`a handful of chapters`) | two clauses, including the instrument one: *"architecture.md no longer says how many chapters the viewer groups the document into"* |

R2 is the one that matters for the argument: the filing is about a
number that was never true, but the failure a guard has to catch from
here on is the *ordinary* one — someone adds a chapter and does not
think about a sentence four hundred lines away in another file.

### Deviation from the Required Fix

- The Required Fix suggested the guard could be derived "where that is
  cheap", citing `test_the_architecture_names_the_commands.py`. That
  guard compares two *lists*; this compares a spelled-out number to a
  length, because the document makes its claim as a sentence and not
  as a table. Same argument, different instrument.
- `docs/design/directions.md:1885` records `UX-286` as having settled
  on "seven chapters" too, and is left alone: it is a dated record of
  what round 39 argued, and the population this guard walks is the
  live documents, on the same reasoning `UX-353` used. It does mean
  the miscount is still readable at its origin, which is what a dated
  record is for.
