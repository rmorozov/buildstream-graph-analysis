# UX-548: five mechanisms round 80 shipped, and no guide names one

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** anyone who reads a guide to find out what `bga view` does | **Topic:** docs

## Motivation

Architecture review 12. `UX-241` filed the cadence guard because the
viewer axis ran `UX-193`..`UX-226` — 34 closed rows — with no document
noticing. Round 80 shipped eight viewer and export items and the same
thing happened at one round's scale:

```text
mechanism                        shipped in    named in a guide?
bga view --reanalyse             UX-533        NO  (git grep -in reanalyse -- docs
                                                    README.md CHANGELOG.md: only
                                                    the task file and its closed row)
the export's compact data half   UX-529        NO  (cli.md:1302 "the run's JSON
                                                    inlined"; architecture.md:864
                                                    "inlines every served document")
STORE_WINDOW = 12, store-all.json UX-528       NO  (cli.md:1038 and
                                                    what-the-viewer-answers.md:135
                                                    describe an unbounded picker)
PICKER_SHOWN = 8, the search box   UX-527      only docs/design/styleguide.md:607
the timeline degrades, not refuses UX-530      cli.md:1374 yes;
                                                what-the-viewer-answers.md:159 still
                                                says "Above 8,000 tracks it is refused"
```

`--reanalyse` is the worst of the five: the served page *prints a
sentence naming the flag* (`analysis_source`, `tools/bga_view.py:295`),
so a reader is told to run a command that appears in no document —
`UX-326`'s class, a sentence the tool speaks being a contract.

`docs/guides/what-the-viewer-answers.md` was not touched by round 80 at
all (`git diff --name-only origin/main..HEAD -- docs/guides/`), and it
is the document the page's own readers are pointed at.

## Required Fix

Each of the five reaches the guide that owns it: `cli.md` for the
flag, the compact form and the window; `what-the-viewer-answers.md` for
the degradation and the picker; `architecture.md` where its sentence
about `--export` inlining is now wrong. `architecture.md:700` also
still calls the server's table "a fixed document table" and does not
name `store-all.json`.

## Out of Scope

- Re-measuring the export weights — `UX-529`'s Outcome has them.
- A guard that every new flag reaches a document; that is `UX-326`'s
  axis and a separate argument.

## Acceptance Test

`git grep -in "reanalyse" -- docs README.md` names a guide; the
refusal sentence in `what-the-viewer-answers.md` matches
`tools/bga_view.py::_degradation_steps`; `store-all` appears in a
document a reader opens.
