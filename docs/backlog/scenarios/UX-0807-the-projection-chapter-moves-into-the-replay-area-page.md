# UX-807: the projection chapter moves into the replay area page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-689 (the rule and the first area), UX-806 (the second, and the one-id-per-chapter rule) | **Found by:** round 112, `UX-806`'s Out of Scope | **Serves:** the reader pricing a change to a projection; the session restructuring without losing a sentence | **Topic:** docs | **Area:** bga-replay | **Shape:** mechanical

## Motivation

`UX-806` named the next chapter: the projection one. The log guard's
anchor rule (`tests/unit/test_the_verification_log_is_true.py`,
`closing_commit` takes the oldest commit naming an id) makes each
chapter its own item, its own entry, landed after the last.

```console
$ grep -n "^## " docs/design/architecture.md | sed -n 13p
545:## What a projection is, and why it is a bound (`UX-230`, `UX-74`)
$ sed -n 545,601p docs/design/architecture.md | wc -l
57
```

## Required Fix

The chapter at `docs/design/architecture.md:545-601` moves into a new
hand-written `docs/design/areas/bga-replay.md`, the same shape as
`docs/design/areas/tools-native_trace.md`: a heading, the "Moved from"
pointer paragraph, the prose verbatim, links re-based. `architecture.md`
keeps the heading and a one-paragraph pointer, plus any line a guard
reads (find them: `grep -ln "architecture.md" tests/unit/*.py`, then
each guard's landmarks inside lines 545-601). `docs/README.md`'s design
index names the new page; the generated `docs/backlog/areas/bga-replay.md`
carries the derived `Mechanism:` line after `dev_close_task.py --check
--write`. A new Verification Log entry crediting `UX-807` rides the same
commit (the guard's rule), saying what was re-grounded and against what.

## Out of Scope

- The other chapters — one item each, filed as the tracks land; the
  next is Plane 3 (`architecture.md:163`), its area page named when
  filed.
- The chapter's claims — moved verbatim, not re-measured; a figure
  found stale is a filing, not an edit here.

## Acceptance Test

`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
the same count before and after; every sentence of the 57 lines in the
new page or the kept pointer (a diff of the removed prose against the
new page's body, empty); `test_docs_links_and_commands.py` green;
`dev_close_task.py --check --write` a no-op after the commit; mutation:
one moved sentence deleted from a scratch copy — the diff names it.

## Outcome

### The gap → the close, measured

```text
$ python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q
437 passed   # before (this round's tip, 7beb7e5c)
437 passed   # after this commit — same count
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
59 passed    # before and after, unchanged
$ PYTHONPATH=. python3 tools/dev_close_task.py --check --write
0 problem(s) over 10 propert(y/ies), 804 backlog row(s)
--write changed no file(s).
```

56 lines of prose moved (the heading is line 57, kept). One paragraph
is guarded and stays in `architecture.md`, under the heading:
`test_the_whatif_convention_is_one_claim.py`'s `TestTheReasoningHasAHome`
reads the chapter text itself for "never a sum", "same chain",
"different chains", "maximum", "1569.8" and "2605.8" — all six inside
the "It is one recompute, never a sum." paragraph and the
freedesktop-sdk table that follows it (lines 562-573 of the pre-move
document). No other of the 20 files naming `architecture.md`
string-matches inside lines 545-601 — checked by grepping each for the
chapter's distinctive strings (`compute_joint_saving`,
`sum_of_individual_us`, `whatif/v1`, `codegen.bst`, `1569.8`,
`2605.8`, `same chain`, `never a sum`, `edg.py`); only the one guard
above matched. `docs/README.md`'s design index gained the page's row;
`docs/backlog/areas/bga-replay.md` picked up the derived `Mechanism:`
line from the existing `write_area_pages` logic (`UX-689`), no code
change needed.

### The sentence diff (empty)

```text
$ diff removed_prose_clean.txt <(tail -n +8 docs/design/areas/bga-replay.md)
$                    # empty — removed_prose_clean.txt is lines
                     # 547-560 + 575-600 of the pre-move chapter (the
                     # guarded 562-573 excluded, kept in architecture.md
                     # instead), link re-based
```

### Mutation table (scratch diff, not a guard)

| # | mutation | diff names |
|---|---|---|
| S1 | the sentence "A re-capture is still the ground truth." deleted from a scratch copy of `docs/design/areas/bga-replay.md` | the deleted sentence, as the sole hunk of a 2-line diff |

No new guard was added by this item (the existing
`test_the_whatif_convention_is_one_claim.py` already reads the one
guarded paragraph, and it stayed in place), so there is no guard to
mutate — only the scratch-copy diff the Acceptance Test asks for.

**Deviation.** None: unlike `UX-806`, one paragraph of the moved
chapter is read by a guard from *inside* the chapter itself, so it
stayed behind in `architecture.md` beside the pointer rather than
moving wholesale; the Required Fix anticipated this ("plus any line a
guard reads"). One commit, one verifier (PASS).
