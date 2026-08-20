# UX-172: `bga blast` — what rebuilds if I touch this

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-171 (the inventory this queries)

## Motivation

UX-171's table ranks the widest resources; the developer's question
arrives pointed the other way — *I am about to touch this thing, what
does it cost?* — and deserves a query, not a scan of a report. Three
shapes of "this thing", one answer format:

- `bga blast <git-url>` — the monorepo case: every element sourcing
  that url, closure, kinds, measured time.
- `bga blast <path>` — a file or directory: for `local` sources, the
  elements whose staged directories contain it (the per-commit answer
  content keying makes possible); relative paths resolve against the
  project.
- `bga blast <element.bst>` — the existing downstream closure, now
  with the kind breakdown and measured cost, so the element and
  resource views read identically.

## Required Fix

One subcommand, `bga blast TARGET`, auto-detecting the target shape
(url / existing path / element name — ambiguity resolved in that order
and stated), printing: direct elements, closure size, counts by kind,
measured rebuild time from `@last`'s run when present (the alias
grammar, like every other command), and the keying clause. `--format
json` for CI. Exit 0 always — this is a question, not a gate (a gate
belongs in compare, where the refusal grammar lives).

Help stays under the UX-158 cap; the docs home is `real-project.md`'s
optimization section plus one line in the README command list.

## Out of Scope

- Watching a diff or a commit range and blasting its file list (a
  natural follow-up; the path form is its building block).
- Gates on blast growth (`UX-79`'s marginal-efficiency machinery is
  the precedent if wanted later).

## Acceptance Test

On the UX-171 git-url fixture: `bga blast <url>` names 6 direct
elements and the closure with kinds and measured time; `bga blast
files/src/lib-d` on the local-sources copy names exactly the elements
staging that directory; `bga blast lib-d.bst` matches the diagnostics
ranking's number for the same element. An ambiguous target states the
resolution order it applied. The docs-commands test covers the new
lines; help under cap.
