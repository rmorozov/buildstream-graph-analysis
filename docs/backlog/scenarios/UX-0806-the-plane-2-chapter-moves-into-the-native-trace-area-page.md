# UX-806: the Plane 2 chapter moves into the native-trace area page

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-689 (the rule and the first area), UX-688 (the generated pages) | **Found by:** round 111, `UX-689`'s first track | **Serves:** the reader pricing a change to the tracer; the session restructuring without losing a sentence | **Topic:** docs | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

`UX-689` plans one area per track, each track a `UX-689:` commit. The
verification-log guard anchors on the **oldest** commit naming an id
(`tests/unit/test_the_verification_log_is_true.py:248-265`,
`closing_commit`), and reds on any substantive `architecture.md` commit
the newest entry's anchor does not reach (`_landed_after`, line 326).
The first track (`2749a34a`) proved it on a scratch commit: a second
`UX-689:` commit touching the document reds the guard for good. So each
further area is its own item, its own entry, landed after the last.

```console
$ grep -n "^## " docs/design/architecture.md | sed -n 4p
153:## Plane 2: intra-element native-build-system tracing (`UX-11`)
$ sed -n 153,177p docs/design/architecture.md | wc -l
25
```

## Required Fix

The chapter at `docs/design/architecture.md:153-177` moves into a new
hand-written `docs/design/areas/tools-native_trace.md`, the same shape
as `docs/design/areas/bga-viewer.md`: a heading, the "Moved from"
pointer paragraph, the prose verbatim, links re-based. `architecture.md`
keeps the heading and a one-paragraph pointer, plus any bullet a guard
reads (find them: `grep -ln "architecture.md" tests/unit/*.py`, then
each guard's landmarks). `docs/README.md`'s design index names the new
page; the generated `docs/backlog/areas/tools-native_trace.md` carries
the derived `Mechanism:` line after `dev_close_task.py --check --write`.
A new Verification Log entry crediting `UX-806` rides the same commit
(the guard's rule), saying what was re-grounded and against what.

## Out of Scope

- The other chapters — one item each, filed as the tracks land; the next is the projection chapter (`architecture.md:560`) into `docs/design/areas/bga-replay.md`.
- Changing the log guard's anchor rule — declined: the oldest match is the rule that keeps a later commit from walking the anchor forward.

## Acceptance Test

`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
the same count before and after (435 at `2749a34a`); every sentence of
the 25 lines in the new page or the kept pointer (a diff of the removed
prose against the new page's body, empty); `test_docs_links_and_commands.py`
green; `dev_close_task.py --check --write` a no-op after the commit;
mutation: one moved sentence deleted from a scratch copy — the diff
names it.

## Outcome

### The gap → the close, measured

```text
$ python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q
437 passed   # before (this round's tip, c5c0cef2)
437 passed   # after this commit (4981a282) — same count; the
             # staleness clause skipped once, mid-work, uncommitted,
             # for lack of a closing commit to anchor against
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
59 passed    # before and after, unchanged
```

25 lines moved (heading + 24 of prose); the four `tools/native_trace/`
members the one substantive guard reads
(`test_the_architecture_lists_every_native_trace_member`) stay named
at "Real package structure" (line 94) and three later sites, outside
the moved chapter, so no bullet had to stay behind it — unlike
`UX-689`'s viewer chapter, no other guard string-matches inside lines
153-177. `docs/README.md`'s design index gained the page's row;
`docs/backlog/areas/tools-native_trace.md` picked up the derived
`Mechanism:` line from the existing generic `write_area_pages` logic
(`UX-689`), no code change needed.

### The sentence diff (empty)

```text
$ diff <(sed -e '$ { /^$/d }' /tmp/plane2_body.txt) \
       <(tail -n +7 docs/design/areas/tools-native_trace.md)
$                    # empty — the one line diff before trimming was
                     # the chapter-boundary blank line, not content
```

### Mutation table (scratch diff, not a guard)

| # | mutation | diff names |
|---|---|---|
| S1 | one moved sentence ("Reported as \"no single process here exceeded this\"...the sum between them.") deleted from a scratch copy of `docs/design/areas/tools-native_trace.md` | the deleted sentence, as the sole hunk of a 1-line diff |

No new guard was added by this item (the existing
`test_the_architecture_lists_every_native_trace_member` already
covered the population, from outside the moved chapter), so there is
no guard to mutate — only the scratch-copy diff the Acceptance Test
asks for.

**Deviation.** None: the guard over the four `tools/native_trace/`
members reads the whole document, so no bullet stayed behind. One
commit, one verifier (PASS).
