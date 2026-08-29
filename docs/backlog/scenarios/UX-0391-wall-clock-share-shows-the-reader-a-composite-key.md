# UX-391: `wall_clock_share_us` shows the reader a composite key

**Priority:** Medium | **Status:** 🟢 Done Done | **Depends on:** UX-374 (the page renames the reader's elements and programs), UX-216 (every element is one object) | **Serves:** anyone searching the page for an element they built | **Topic:** viewer

## Motivation

`UX-374` fixed the sections that renamed the reader's elements. One
section over, the same defect survives. From the round 63 export:

```text
codegen.bst|BUILD|BUILD|0    2.3 s
```

That is the task uid — element, kind, phase, attempt — pipe-delimited
and printed verbatim as a row label in `wall_clock_share_us`. A reader
who types `codegen.bst` into the jump box does not match it, and a
reader who reads it has to know the tool's own key format to see that
three of the four fields are `BUILD`, `BUILD`, `0`.

The composite is right as a key: a build task and a fetch task of the
same element are different rows, and collapsing them would lose that.
What is wrong is showing the key where a name belongs.

## Required Fix

The row is labelled the way `UX-374` labelled the others: the element
name as the label, the task's kind and attempt as their own columns or
as a qualifier, and the composite uid kept as the row's identity for
linking and filtering — not as its text.

The link matters as much as the text: the element name in this table
should reach the same element the rest of the page reaches, which is
`UX-216`'s property and is unavailable while the label is a string
nothing else in the payload spells that way.

## Falsification

A guard over the rendered page that asserts no visible label contains
the uid delimiter — the same clause `UX-374` added, extended to this
section. Today it fails on every row of `wall_clock_share_us`.

The other direction: two tasks of one element must still be two rows.
A guard that renders a fixture with a retry and asserts both attempts
survive the relabelling, so "show the name" does not become "merge the
rows".

## Out of Scope

- The rest of the uid's fields reaching the reader as data. Whether
  attempt number deserves its own column is a design call inside the
  fix, not a second item.

## Outcome (round 65, 2026-08-29) — 🟢 Done

### Before and after, on the two committed fixtures

```text
                         label shown            data-key
before  macro_micro      codegen.bst|BUILD|BUILD|0   codegen.bst|BUILD|BUILD|0
after   macro_micro      codegen.bst  BUILD         codegen.bst|BUILD|BUILD|0
        golden           extra.bst  FETCH           extra.bst|FETCH|FETCH|0

labels still containing the uid delimiter:   before 22   after 0
rows:                                        unchanged
```

The composite survives as the row's identity, which is the half the
filing insists on: a retry and a fetch of one element are different rows
and collapsing them would lose that.

### Declared, not sniffed

`bga:keyed_by: "task_uid"` on the map. The page cannot tell
`a.bst|BUILD|BUILD|0` from a binary called that without being told, and
a viewer that guessed would be the name-sniffing `UX-201` removed. The
hint has its row in styleguide §1's vocabulary table, which is what
`test_the_contract_names_its_vocabulary.py` demanded on its first run.

**The qualifier says only what is not obvious.** `BUILD|BUILD|0` is one
BUILD task on its first attempt, so it reads `BUILD`; a retry reads
`BUILD, attempt 2` and a distinct phase reads `ASSEMBLE, BUILD`.
Printing all three fields would have put the composite back on screen in
words.

### `UX-374`'s guard had to be amended, and that is the interesting part

`test_the_page_keeps_the_names_it_was_given.py` asserts every data key
is shown **verbatim** - and this shows a component of one, so it went
red on four keys per fixture. The amendment is deliberately narrow: a
key the schema declares as a *composite* satisfies the rule by showing
one of its fields verbatim, split on the delimiter. `base` for
`base.bst|...` is still a rename, and so is any humanised form.

That is the rule `UX-374` always meant - **the page must not author a
name** - stated for the one class of published key that is not itself a
name. Recorded here rather than in a comment, because weakening a guard
to admit one's own change is exactly the move that needs to be visible.

### Two guards this change had to answer to

```text
test_the_contract_names_its_vocabulary   a hint documented nowhere
test_the_viewer_splits_along_its_seams   structured.js at 1,517 of 1,500
```

The second is `UX-337`'s ceiling, and structured.js was sitting exactly
on it. `describedTerm` moved to `format.js` - it builds a *label*, its
sentence and its `?` door, and every other label mechanism (`title`,
`heading`, `sectionHead`) already lives there. `el` and `title` are both
local to `format.js`, so the move adds no import edge and the viewer
stays acyclic. structured.js: 1,517 → 1,446.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| A1 | the map stops declaring `bga:keyed_by` | the contract clause and the rendered-page clause (2 failed, 4 passed) |
| A2 | the label is the whole uid again — the defect | the no-composite clause (1 failed, 5 passed) |
| A3 | `data-key` is not set, so the identity is lost | the identity clause (1 failed, 5 passed) |
| A4 | a retry's attempt number is dropped from the qualifier | the retry clause (1 failed, 5 passed) |

A3 is the one that matters beside A2: showing the element name is easy,
and doing it by *replacing* the identity would break every link and
filter built on the row.

### Deviation from the Required Fix

**None.** The label is the element, the kind and attempt are a
qualifier, and the composite is kept as identity. The Falsification's
other direction - two tasks of one element stay two rows - holds by
construction: nothing merges rows, and the golden fixture's `FETCH` and
`BUILD` tasks are both present with distinct `data-key`s.

### Verification

```text
pytest tests/unit/test_a_task_uid_is_not_a_label.py            6 passed
pytest tests/unit/test_the_page_keeps_the_names_it_was_given.py
                                                  18 passed, 1 skipped
pytest tests/unit/test_the_viewer_splits_along_its_seams.py   28 passed
make lint                                                      clean
```
