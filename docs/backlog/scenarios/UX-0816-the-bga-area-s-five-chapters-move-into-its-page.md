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

## Outcome

### The gap → the close, measured

```text
$ python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q
437 passed                # before (66b5266b, after UX-815)
436 passed, 1 skipped     # after (uncommitted) - anchor test skips
                          # until a `UX-816:` commit exists (UX-810/815 shape)
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
59 passed                 # before and after, unchanged
$ PYTHONPATH=. python3 tools/dev_close_task.py --check --write
0 problem(s) over 10 propert(y/ies), 816 backlog row(s)  # docs/backlog/areas/bga.md
gained its `Mechanism:` line; a no-op on the second run
$ python3 -m pymarkdown --config .pymarkdown.json scan docs/design/areas/bga.md \
    docs/design/architecture.md docs/README.md
(clean)
$ PYTHONPATH=. python3 tools/dev_sizes.py --check
sizes ok: 122 file(s) measured, none above the cell
```

Blanked chapter-by-chapter (heading kept), 21 files re-run each time:
"Joining the planes", both round-history chapters and "Core invariants"
gave no failure, no guard reads inside any of the four; moved wholly.
"Real extensions" alone reddened `test_the_architecture_table_is_read_at_all`
(reads its `UX-01`..`UX-76` table scoped by that heading) and
`test_the_table_status_matches_the_task_files` (cross-checks the same
rows). Its two prose paragraphs and the `UX-08` footnote, blanked alone,
caused no failure - but both refer to the table ("everything **below**",
"the table covers...") so the whole chapter stays in `architecture.md`
unchanged; `bga.md`'s section is a pointer back, not a duplicate.
Chapters 1-2's `sensitivity`/`peak_memory`/`capacity_verdict` mentions
also reddened `test_a_new_key_with_no_prose_reddens_naming_the_key`, but
that guard scans all `docs/**/*.md`, not `architecture.md` alone -
confirmed green with the text placed only at `bga.md`. No guarded line
from those two chapters needed to stay.

### The sentence diff (empty) and mutation

```text
$ diff removed_prose.txt page_body.txt
$                    # empty; no link needed rebasing - the one link in
                     # the five chapters sits in the "table covers"
                     # sentence, which stayed in architecture.md unmoved
$ diff removed_prose.txt mut_page_body.txt   # scratch copy, one sentence deleted
15d14
< - **Negative results are load-bearing.** "Already compute-bound at 3.41
  cores busy" tells a reader to stop looking inside that element...
```

### Mutation table (new guard)

| # | mutation | reddened | count |
|---|---|---|---|
| G1 | `docs/backlog/areas/bga.md`'s `Mechanism:` line deleted | `test_the_bga_area_gained_its_hand_written_page` (new; replaces the retired negative fixture on `bga.md`) | 1 failed, 9 passed → 10 passed restored |

### The UX-689 figure

```text
$ awk '/^## Verification Log/{exit} {n++} END{print n}' docs/design/architecture.md
593   # before this commit (66b5266b)
490   # after (this commit)
$ git show 2749a34a~1:docs/design/architecture.md | awk '...'
1044  # before the whole UX-689 series began
```

**Deviation.** The invariants list turned out unread by any guard
(moved wholly, unlike the brief's guess); the real-extensions table's
guard needs the whole table under its own heading, so the whole fifth
chapter stayed rather than one guarded line beside a pointer.
Undeclared surface: `tests/unit/test_every_task_names_its_area.py`'s
negative fixture named `bga.md` (now wrong) - repointed at
`bga-attribution.md`, positive clause added and mutated above. One
commit, one verifier (PASS).
