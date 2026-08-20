# UX-172: `bga blast` — what rebuilds if I touch this

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-171 (the inventory this queries)

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

## What was built

`bga blast TARGET [RUN]` (`bga/blast.py`), auto-detecting the target
shape in a stated order - **url, then path, then element** - and saying
which reading it used whenever more than one applied. `@last` by
default, the same alias grammar as everything else, `--format json` for
CI.

- A **url** finds every element whose ref-keyed sources name that
  repository, normalised so one repository has one identity.
- A **path** finds the elements whose content-keyed sources stage it,
  including a path *inside* a staged directory - which is the form the
  question actually arrives in, since the developer has just edited a
  file, not a source stanza.
- An **element** gets the closure the tool has always been able to
  compute, printed in the same shape so the three views read alike.

A question, not a gate: exit 0 on an answer of zero and on an answer of
two hundred alike. Exit 2 is reserved for a run directory that is not
one, which is a usage error rather than an answer.

Two things the first live run corrected. A path had to *exist* to be
read as a path, so asking about a file you just deleted answered
"nothing sources it" - a false negative on the most common form of the
question; a target containing `/` now reads as a path whether or not it
is on disk. And a run with no inventory said "nothing sources it" where
the truth was "this capture cannot answer that" - two different facts,
now two different sentences.

Measured live on `examples/01-resource-contention`:

```text
$ bga blast files/runtime
  Sourced directly by 1 element(s): runtime.bst
  Rebuilds 10 element(s) (8 that build, 2 that assemble) of 10 in this build
    8 manual, 1 import, 1 stack
  Cost: 22s of build work, measured for 10 of 10
  keys on content: only the elements whose files changed rebuild

$ bga blast work-a.bst --format json     # 2 elements, 3.0s
```

Guards in `tests/unit/test_blast_query_and_kinds.py`; the resolution
order, the path-prefix rule (a source staging `files/src` must not
match `files/src2`), the no-inventory sentence and the always-zero exit
each have one, and each mutation reddens.
