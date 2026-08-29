# UX-394: nothing in the page moves between runs

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-234 (the store speaks for more than one build), UX-226 (what happened to this element since last time), UX-221 (which elements caused the regression), UX-211 (URL state) | **Serves:** anyone who has captured the same project twice | **Topic:** viewer

## Motivation

The user's instinct was right, and it is measurable. Round 63 ran the
capture cycle twice, so the store held two runs of the same project
while the report was open. No control in the page reaches the other
one:

```text
runs in the store                        2
controls in the page reaching another    0
```

`bga view` is a single-run window. The tool already knows how to speak
about more than one run — `bga compare`, `bga view @prev`, `@last`,
the store's own listing — but all of it is CLI vocabulary, and a
reader in a browser has to go back to a terminal, work out which run
identity they want, and re-invoke.

This is the largest gap between what the store holds and what the page
offers, and it falls precisely on the tool's own use case: *did my
change make the build faster*. `UX-226` published what happened to an
element since last time and `UX-221` which elements caused a
regression; both answer inside one page for one run, and neither can
be reached from the run beside it.

## Required Fix

- **A run selector in the page**, listing the store's runs for this
  project with the identity `UX-95` established (what the run *is*,
  not a directory name), and switching to one without a terminal.
- **The selection travels in the URL** (`UX-211`), so a reader can
  send someone the same view of the same run.
- **The obvious neighbours are one click**: previous run, latest run,
  and — where a comparison exists — the comparison against the run
  currently shown.
- The page keeps working with no store and one run: the selector is
  absent, not empty, which is `UX-388`'s rule.

## Falsification

A store holding two captures of one project, exported and driven: the
run selector lists both, selecting the other re-renders the page
against the other run's payload, and the URL after the switch reloads
to the same view. Today the selector does not exist.

The other direction: `--export` produces a single self-contained file
(`UX-195`) and must keep doing so. An exported page cannot reach runs
it does not carry, so it either embeds the run list as identities
without payloads and says the payload is elsewhere, or renders no
selector — what it must not do is offer a control that fails.

## Out of Scope

- Embedding several runs' payloads in one export. That is the volume
  budget's problem (`UX-360`, `UX-367`) and a separate decision.
- The aggregate view. `bga analyze --aggregate` already crosses runs;
  this item is about moving between single-run reports.
