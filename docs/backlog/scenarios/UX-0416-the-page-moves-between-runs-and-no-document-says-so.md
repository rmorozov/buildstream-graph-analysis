# UX-416: the page moves between runs, and no document says so

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** architecture review 7, checklist item 4 | **Serves:** anyone with more than one snapshot in a store | **Topic:** docs

## Motivation

`UX-394` gave the served page a run selector: `bga view` builds any
snapshot in the store on demand, `?run=<stamp>` names one, and the rail
draws a picker when the store holds two or more. It is the answer to a
question the guides have posed since `UX-234` ("the store speaks for
more than one build") and answered only in the terminal.

Checklist item 4 of the review — *what shipped since the last review
that no document names?* — found it named nowhere:

```text
$ grep -rln '?run=\|run picker\|run selector' docs/ README.md CHANGELOG.md
docs/backlog/scenarios/UX-0394-nothing-in-the-page-moves-between-runs.md
docs/backlog/scenarios/closed.md
```

Its own task file and the closed index. `docs/guides/cli.md`'s
`bga view` section describes the server's document table and names the
two endpoints that take a parameter (`blast.json?target=`,
`whatif.json?elements=`); there are three now. `docs/design/architecture.md`'s
viewer chapter says the same thing in the same words. And
`docs/guides/what-the-viewer-answers.md`, which is the document a
reader consults to learn what the page can do, does not mention that it
can move between runs at all.

## Required Fix

- `docs/guides/cli.md`'s `bga view` section: `?run=<stamp>` beside the
  other two parameterised endpoints, and one sentence on the picker —
  when it appears (two or more runs) and what it does *not* do (an
  export has no store, so it renders no picker).
- `docs/design/architecture.md`'s viewer chapter: the same, where it
  lists the document table.
- `docs/guides/what-the-viewer-answers.md`: the capability, in the
  reader's terms.

## Out of Scope

- The chapter heading "The viewer axis (rounds 21-26)", which is now
  thirty-eight rounds behind its own title. Real, and a different
  edit.

## Acceptance Test

- The grep above returns the three documents above, not two backlog
  files.
