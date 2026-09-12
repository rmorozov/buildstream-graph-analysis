# UX-815: the ingestion-path chapter moves into the tools area page

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-689 (the rule), UX-810 (the tools page it joins) | **Found by:** round 114, `UX-810`'s Out of Scope | **Serves:** the reader pricing a change to the capture path; the session finishing `UX-689` | **Topic:** docs | **Area:** tools | **Shape:** mechanical

## Motivation

The largest chapter left in `docs/design/architecture.md` is the
capture path's own — how the tracer, the shim and the spine measure
themselves (`UX-105`–`UX-110`) — 217 lines of `tools/` mechanism. The
tools area's page (`UX-810`) holds one section; this is its second.
The log guard's anchor rule makes it its own item.

```console
$ grep -n "^## " docs/design/architecture.md | sed -n 7p
187:## The ingestion path now measures itself (`UX-105`–`UX-110`)
$ sed -n 187,403p docs/design/architecture.md | wc -l
217
```

## Required Fix

The chapter at `docs/design/architecture.md:187-403` moves into
`docs/design/areas/tools.md` as its second `##` section, after the
Plane 3 one, prose verbatim, links re-based; `architecture.md` keeps
the heading and a one-paragraph pointer, plus any line a guard reads
from inside the chapter (find them: `grep -ln "architecture.md"
tests/unit/*.py`, then each guard's landmarks inside lines 187-403 —
blank the chapter and re-run the files, as `UX-810` did). A new
Verification Log entry crediting `UX-815` rides the same commit.

## Out of Scope

- The chapters left after this one — `UX-816` takes the `bga` area's
  five (joining the planes, the two round-history chapters, the core
  invariants, the real extensions) into `docs/design/areas/bga.md`,
  landed after this one.
- The chapter's claims — moved verbatim, not re-measured.

## Acceptance Test

`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
the same count before and after; every sentence of the 217 lines in
the new section or the kept pointer (a diff of the removed prose
against the section's body, empty); `test_docs_links_and_commands.py`
green; mutation: one moved sentence deleted from a scratch copy — the
diff names it.

## Outcome

### The gap → the close, measured

```text
$ python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q
437 passed   # before (24098978)
437 passed   # after (uncommitted; the anchor test skips until the
             # `UX-815:` commit exists — same shape UX-810 measured)
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
59 passed    # before and after, unchanged
$ PYTHONPATH=. python3 tools/dev_close_task.py --check --write
0 problem(s) over 10 propert(y/ies), 812 backlog row(s)
--write changed no file(s).
$ python3 -m pymarkdown --config .pymarkdown.json scan \
    docs/design/areas/tools.md docs/design/architecture.md
(clean)
$ PYTHONPATH=. python3 tools/dev_sizes.py --check
sizes ok: 122 file(s) measured, none above the cell
# no row to move: the ledger tracks code files only, a doc-only move
# has no cell (same as UX-810)
```

Empirical check: the chapter's body (lines 188-403, heading kept) was
blanked in place, all 21 test files naming `architecture.md` re-run —
still 437 passed, so **no line inside the chapter is read by any
guard**; grepping the 21 files for 20 distinctive chapter phrases
(`PTRACE_SEIZE`, `stream_records`, `PLANE1_ANNOTATIONS`, `UNCOVERED`,
`sibling_order_rank`, etc.) found none. Only the heading and a fresh
one-paragraph pointer stay in `architecture.md`. The one link inside
the chapter, `docs/audits/data/spine-cost-storm.md`, was re-based
`../audits/` → `../../audits/`. The contract-table counts re-ran
unchanged: 25 emitted ids, 10 superseded, 3 read-never-written, 9
printable/16 not, `analyze/v6` 61 top-level properties, 22 viewer
modules — carried into the new Verification Log entry.

### The sentence diff (empty)

```text
$ diff removed_prose.txt <(sed -n '55,$p' docs/design/areas/tools.md)
$                    # empty — removed_prose.txt is lines 187-403 of
                     # the pre-move chapter (heading + body), verbatim
                     # except the one re-based link
```

### Mutation table (scratch diff, not a guard)

| # | mutation | diff names |
|---|---|---|
| S1 | the sentence "It is **compared, never substituted**: the elapsed prefix is a second-resolution lower bound, and moving a span's endpoint to satisfy it would manufacture overlap the capacity model reports as a violation." deleted from a scratch copy of `docs/design/areas/tools.md` | the deleted sentence, as the sole hunk of a 4-line diff |

No new guard was added — no existing guard reads inside the chapter
(confirmed above), so there was none to mutate; only the scratch-copy
diff the Acceptance Test asks for.

**Deviation.** None: like `UX-810`, no line of this chapter is read by
a guard from inside it, so the whole chapter moved and only the
heading plus a fresh one-paragraph pointer stay in `architecture.md`.
The tools area page's own pointer paragraph gained a clause naming
this second move. One commit, one verifier (PASS).
