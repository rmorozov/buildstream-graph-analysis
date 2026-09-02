# UX-136: the two most-read docs teach only the superseded flows

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-96, UX-115, UX-124, UX-126 (the shipped replacements) | **Topic:** docs

Docs polish round (round 14). Sibling of `UX-135`; full read in
[`round-14`](../../audits/round-14.md).

## Motivation

Every one of these replacements shipped, verified, in the last three
rounds — and the docs a user actually reads still teach what they
replaced (each verified by grep this round):

1. **`bga baseline` appears zero times in `README.md` and
   `real-project.md`** — both teach the manual three-`--baseline-run`
   band assembly exclusively (README:240-248, real-project:627-633).
   The one-command replacement is documented only in cli.md and the
   capture guide.
2. **`ci-comment.md`'s main YAML teaches `bga wrap` + `bga extract`**,
   with `--run-dir` (one command, and required anyway for the
   never-read column) appended afterwards as a retrofit (88-91 vs
   150-161).
3. **`cli.md:544-558` and `real-project.md:543-557` still print
   correlate output the tool no longer produces** — "multiply by
   however many elements build concurrently", which UX-104/UX-124
   replaced with the computed memory envelope; `real-project.md` never
   mentions the envelope at all. The walkthrough teaches an output a
   user cannot reproduce.
4. **README:344-353 shows the three-command dual capture before its
   `bga correlate @last` one-liner**; the order should invert.
5. Smaller, same class: cli.md's Example Workflows section uses
   `/path/to/run-directory` throughout with no `@last`/`@prev` (the
   alias section is 500 lines earlier in the same file);
   `optimization-walkthrough-06.md:48` uses `-d`, a short flag no
   current doc defines.

The pattern is structural: features ship with their own doc section,
and nobody's job is to re-teach the *old* sections. (The capture guide
did this right — its superseded block is in a `<details>` marked as
historical — so the convention exists; it was applied once.)

## Required Fix

Fix the five, each the same way: the shipped short form becomes the
taught form where users read; the long form survives once, as
"what it composes" (the cli.md plumbing pattern) or a `<details>`.
Item 3 additionally adds the memory-envelope line to
`real-project.md`'s correlate step with its capture named, per style
rule 4 — a re-run against the retained capture, not a paste.

## Out of Scope

- README's overall reorder (`UX-134`); dedup/terminology
  (`UX-137`/`UX-138`).

## Acceptance Test

`grep -c 'bga baseline' README.md docs/guides/real-project.md` ≥ 1
each; ci-comment.md's first YAML block contains `--run-dir` and no
`bga extract`; `grep -rn 'multiply by however' docs/guides/` is empty;
the walkthrough's correlate output block is re-generated from the
retained capture and shows the envelope; every changed command block
passes the docs-commands test.


---

## What was built

All five, and one correction to the finding itself.

1. **`bga baseline` is taught where users read.** README's band block
   leads with the one-command form and keeps the manual
   three-`--baseline-run` assembly as "what it composes"; `real-project.md`
   and the new CI page do the same.

   *(`UX-154`: this claim was false for `real-project.md` when it was
   written — README and `ci-comment.md` were edited and the guide named
   in the sentence was not, `grep -c` returning 0. Corrected there, and
   the docs-commands guard below now covers it.)*
2. **`ci-comment.md`'s first YAML** is now `bga capture run --run-dir`,
   one build for both planes. `wrap` + `extract` survives as the
   Plane-1-only alternative, named as such.
3. **Both correlate blocks regenerated** from the retained capture
   (`captures/fdsdk/953683fb-incremental-b4j4-32064333551`, fetched and
   re-run through today's `bga correlate`).
4. **README's join leads with `bga correlate @last`**; the explicit
   three-command form follows as the outside-a-project case.
5. `cli.md`'s workflow examples use `RUN/` and `@last`; `-d` is defined
   where it is used.

### The finding was under-stated, and in an interesting direction

Item 3 says the docs "print correlate output the tool no longer
produces". Checked against the real capture, it is worse than that in
`cli.md` and milder in `real-project.md`:

- **`cli.md`'s block was a composite no run ever produced.** It printed
  `core.bst` — an `examples/06` element — carrying freedesktop-sdk's
  `cmake-stage1` figures: 885 `cc1plus` processes, 4353 CPU s, `dwz` at
  138.6s, 1902 MB peak. Those are all in README's Plane 2 section under
  the element they belong to. Two real captures were spliced into one
  fictional row and labelled real output.
- **`real-project.md`'s block was genuinely stale** but honestly
  attributed: right element, output the tool has since changed (`UX-89`
  now groups `cmake-stage1` with `doxygen` and collapses their figures
  to ranges).

Both are replaced with output regenerated today from the retained
capture.

### Deviation, recorded

The acceptance asks that `grep -rn 'multiply by however' docs/guides/`
come back empty. It does not, and should not: that line is what the tool
**still prints** for a capture with no host memory recorded — which the
retained fdsdk capture is — and it now carries the clause explaining why
(*"the capture recorded no host memory, so this cannot do it for you"*).
Deleting a line the tool really emits would trade one wrong doc for
another. The computed envelope is shown beside it, from `examples/06`,
labelled with which capture each came from.
