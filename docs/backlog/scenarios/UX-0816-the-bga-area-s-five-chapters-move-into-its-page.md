# UX-816: the bga area's five chapters move into its page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-689 (the rule), UX-815 (landed before this, the anchor rule) | **Found by:** round 114, `UX-815`'s Out of Scope | **Serves:** the reader pricing a change to the analysis; the session finishing `UX-689` | **Topic:** docs | **Area:** bga | **Shape:** mechanical

## Motivation

After `UX-815`, the mechanism prose left in `docs/design/architecture.md`
is the `bga` area's: joining the planes, the two round-history chapters
(the 2026-08-16 audit round and the real-capture rounds, structural
changes to what the analysis asserts), the core invariants and the
real extensions table. `docs/design/areas/bga.md` does not exist yet;
the generated `docs/backlog/areas/bga.md` will carry its `Mechanism:`
line once it does.

```console
$ grep -n "^## " docs/design/architecture.md | sed -n '6p;8,10p;12p'
170:## Joining the planes (`UX-51`, `UX-100`)
404:## What the 2026-08-16 audit round changed structurally
476:## What the real-capture rounds (7–10) changed structurally
496:## Core invariants still load-bearing (Plane 1)
529:## Real extensions beyond the original spec
```

(line numbers at `24098978`, before `UX-815` moves the chapter between them.)

## Required Fix

The five chapters move into a new hand-written `docs/design/areas/bga.md`
— an H1 naming the area, the "Moved from" pointer paragraph, then the
five as `##` sections in the document's order, prose verbatim, links
re-based. `architecture.md` keeps each heading with a one-paragraph
pointer, plus any line a guard reads from inside a chapter (blank each
chapter and re-run the files, as `UX-810` did — the real-extensions
table and the invariants list are the likely reads). `docs/README.md`'s
design index names the page; `dev_close_task.py --check --write` gives
the generated `docs/backlog/areas/bga.md` its `Mechanism:` line. One
Verification Log entry crediting `UX-816` rides the same commit.

## Out of Scope

- The chapters that stay: the shape of the tool, the CLI surface, the
  package structure, the published and read contracts, the navigation
  chapter and the log — skeletons the guards read, or the document's
  own frame.
- The chapters' claims — moved verbatim, not re-measured.

## Acceptance Test

`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
the same count before and after; every sentence of the five chapters in
the new page or a kept pointer (a diff of the removed prose against
the page's body, empty); `test_docs_links_and_commands.py` green;
mutation: one moved sentence deleted from a scratch copy — the diff
names it. After it lands, `UX-689`'s own figure: `architecture.md`'s
lines outside the Verification Log, before and after the whole series.
