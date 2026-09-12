# UX-810: the Plane 3 chapter moves into the tools area page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-689 (the rule and the first area), UX-807 (the third, and the one-id-per-chapter rule) | **Found by:** round 113, `UX-807`'s Out of Scope | **Serves:** the reader pricing a change to the persisted-log reader; the session restructuring without losing a sentence | **Topic:** docs | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-807` named the next chapter: Plane 3, BuildStream's own persisted
logs, read by `tools/bst_cache_logs.py` — the `tools` area, whose
hand-written page does not exist yet. The log guard's anchor rule
(`tests/unit/test_the_verification_log_is_true.py`, `closing_commit`
takes the oldest commit naming an id) makes each chapter its own item,
its own entry, landed after the last.

```console
$ grep -n "^## " docs/design/architecture.md | sed -n 5p
163:## Plane 3: BuildStream's own persisted logs (`UX-91`)
$ sed -n 163,208p docs/design/architecture.md | wc -l
46
```

## Required Fix

The chapter at `docs/design/architecture.md:163-208` moves into a new
hand-written `docs/design/areas/tools.md`, the same shape as
`docs/design/areas/bga-replay.md`: a heading, the "Moved from" pointer
paragraph, the prose verbatim, links re-based; the page is the tools
area's, so its heading names the area and the chapter is its first
section — later chapters on the tools join it. `architecture.md` keeps
the heading and a one-paragraph pointer, plus any line a guard reads
(find them: `grep -ln "architecture.md" tests/unit/*.py`, then each
guard's landmarks inside lines 163-208). `docs/README.md`'s design
index names the new page; the generated `docs/backlog/areas/tools.md`
carries the derived `Mechanism:` line after `dev_close_task.py --check
--write`. A new Verification Log entry crediting `UX-810` rides the
same commit (the guard's rule), saying what was re-grounded and against
what.

## Out of Scope

- The other chapters — one item each, filed as the tracks land; the
  next is "Joining the planes" (`architecture.md:209`, `bga/correlate.py`,
  the `bga` area).
- The chapter's claims — moved verbatim, not re-measured; a figure
  found stale is a filing, not an edit here.

## Acceptance Test

`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
the same count before and after; every sentence of the 46 lines in the
new page or the kept pointer (a diff of the removed prose against the
new page's body, empty); `test_docs_links_and_commands.py` green;
`dev_close_task.py --check --write` a no-op after the commit; mutation:
one moved sentence deleted from a scratch copy — the diff names it.

## Outcome

### The gap → the close, measured

```text
$ python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q
437 passed   # before (this round's tip, f16c2ee9)
436 passed, 1 skipped   # after (uncommitted) — the one skip is
                        # test_nothing_landed_after_the_commit_the_entry_credits,
                        # which has no `UX-810:` commit to anchor on yet
437 passed   # after this commit (the anchor now resolves) — same count
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
59 passed    # before and after, unchanged
$ PYTHONPATH=. python3 tools/dev_close_task.py --check --write
0 problem(s) over 10 propert(y/ies), 807 backlog row(s)
--write changed no file(s).
```

Empirical check, not a string search: every one of the 21 test files
naming `architecture.md` was re-run against a scratch copy with lines
164-207 (the chapter's body) blanked, before the replacement was
written — still 437 passed, so **no line inside the chapter is read by
any guard**; only the heading and a one-paragraph pointer stay in
`architecture.md`. `docs/README.md`'s design index gained the page's
row; `docs/backlog/areas/tools.md` picked up the derived `Mechanism:`
line from the existing `write_area_pages` logic (`UX-689`/`UX-807`),
no code change needed. `PYTHONPATH=. python3 tools/dev_sizes.py
--check` reports `sizes ok` — the ledger tracks code files only, so a
doc-only move has no row to move or adopt.

### The sentence diff (empty)

```text
$ diff removed_prose.txt <(sed -n '8,$p' docs/design/areas/tools.md)
$                    # empty — removed_prose.txt is lines 163-207 of
                     # the pre-move chapter, verbatim (no links to
                     # re-base; the chapter has none)
```

### Mutation table (scratch diff, not a guard)

| # | mutation | diff names |
|---|---|---|
| S1 | the sentence "Nothing in Plane 3 may feed a certified floor, and the report says that too." deleted from a scratch copy of `docs/design/areas/tools.md` | the deleted sentence, as the sole hunk of a 2-line diff |

No new guard was added by this item — no existing guard reads inside
the chapter (confirmed above), so there was none to mutate; only the
scratch-copy diff the Acceptance Test asks for.

**Deviation.** None: unlike `UX-807`, no line of this chapter is read
by a guard from inside it, so the whole chapter moved and only the
heading plus a fresh one-paragraph pointer stay in `architecture.md`.
The page's H1 names the area ("The tools area") rather than the
chapter, per the brief, since later chapters on `tools/` are expected
to join it. One commit, one verifier (PASS).
