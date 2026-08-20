# UX-174: the monorepo patterns page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-171 (the numbers the page reads), Direction 6 (the argument it condenses)

## Motivation

The user's framing, verbatim: *"if i am not mistaken buildstream is
not the best tool for monorepo integration but there must be patterns
how to resolve this case."* Both halves true, and the tool is about to
measure the difference between the patterns (UX-171) — so the docs
should say what the patterns are, in bga's house style: semantics
first, then the number that makes the choice.

The core fact the page turns on (Direction 6): a `git` source keys on
its **ref** — `directory:` narrows staging, not keying, so any commit
rebuilds every element on that url; a `local` source keys on
**content** — per-directory blast. BuildStream has no native
per-subdirectory git keying, and no amount of element layout changes
that; what changes it is which pattern the project consumes the repo
through.

## Required Fix

One section in `real-project.md` (or a short guide it links, if it
outgrows a section — concision rules apply), covering:

1. **The keying semantics** in five lines — ref vs content, with the
   `directory:` caveat called out, because it is the single most
   surprising fact.
2. **The four patterns**, each with its blast shape and its cost:
   whole-repo git url (simplest; widest blast — the one UX-171's
   headline measures); per-component repositories or refs (smallest
   blast; most maintenance); the workspace/local-checkout pattern
   (content keying, per-directory blast — the practical monorepo
   answer where CI checks the repo out anyway); junction pinning
   (blast at junction granularity).
3. **How to read the new report section** and the one-command loop:
   see the headline resource → `bga blast <url>` → compare patterns
   by measured hours, not taste.
4. Honest limits: this reads *declared* sources; tracking behavior
   (`bst track` cadence, ref pinning policy) moves when rebuilds
   happen, not what a rebuild costs.

## Out of Scope

- Recommending one pattern universally (the page shows costs; the
  project chooses).
- Junction-update blast mechanics beyond the one paragraph (its own
  item if a real project asks).

## Acceptance Test

The section exists where real-project.md's optimization flow points at
it; every command line in it passes the docs-commands test; the
keying-semantics claim about `directory:` is stated and carries a
provenance note (BuildStream source-kind docs or a measured
demonstration on the UX-171 fixture — measured preferred, per house
rule); `make lint-docs` green; the docs corpus line-count delta stays
within the concision budget (one screenful, or the split-out guide).
