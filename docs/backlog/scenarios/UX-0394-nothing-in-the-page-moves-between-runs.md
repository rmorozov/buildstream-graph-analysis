# UX-394: nothing in the page moves between runs

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-234 (the store speaks for more than one build), UX-226 (what happened to this element since last time), UX-221 (which elements caused the regression), UX-211 (URL state) | **Serves:** anyone who has captured the same project twice | **Topic:** viewer

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

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The selector, driven

A project whose store holds three analysable snapshots, served, and the
page driven in Chrome:

```text
nav.toc .run-picker
  Run: [ 20260101T000000Z — 46.1s          ]
       [ 20260102T000000Z (@prev) — 46.1s  ]
       [ 20260103T000000Z (@last) — 46.1s  ]   ← selected
  [← Previous run]

?run=20260101T000000Z  →  #run-path reads …/20260101T000000Z/run
                          and the selector shows that stamp selected
?run=nope              →  the run this server was started on, rendered
```

The identity is `UX-95`'s — the alias a reader already types at a
terminal and what the run measured, never a directory name, and a
clause asserts no `/` reaches a label.

### A navigation, not a re-render

The page reads its payload once at boot (`UX-296`: it parses nothing),
so `?run=<stamp>` **is** the state. Choosing a run loads that URL and
sending someone the URL sends them the same view of the same run
(`UX-211`). Three things had to follow:

- `serve()` learns the store's other runs from the listing the page is
  already given, so the selector and the server cannot disagree about
  what is on disk;
- the documents for another run are **built on request and cached per
  stamp** — a server that analysed every run in the store at startup
  would pay for runs nobody opens, which is `UX-296`'s rule for the
  timeline applied to the second run;
- every document fetch carries the query (`runQuery()`), or the page
  would render the run the server was started on while its own
  selector said otherwise: two answers to one question, from one URL.

### Absent, not empty

An export carries one run's payload and can reach no other, so it
renders no selector — the list comes from `store.json`, which only a
served page has. That is the Falsification's own "what it must not
do", and `TestAnExportOffersNothingItCannotReach` is the clause.

One run is not a choice either: below two the selector is absent
rather than a menu with one entry.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| J1 | drop the `?run=` from `load`'s fetch | 2 of 8, incl. `test_the_other_run_s_payload_is_what_comes_back` |
| J2 | ignore `?run=` in the handler (serve the started run always) | 2 of 8, incl. `test_the_other_run_s_payload_is_what_comes_back` |
| J3 | render the selector on one run too | 1 of 8: `test_it_renders_no_selector` |
| J4 | label the options with the run directory path | 1 of 8: `test_the_identity_is_what_the_run_is` |

### One bug the guard's own probe found before a clause did

`urlFor` was declared below the option loop that used it, so
`runSelector` threw `ReferenceError: Cannot access 'urlFor' before
initialization` — and the boot swallowed it, leaving the rail rendered
and the selector silently absent. Calling `runSelector` directly from a
driven page, with `Browser.observe`, is what surfaced it; the page's
own console was clean because the throw never reached it.

### Deviation from the Required Fix

- **"the comparison against the run currently shown" is not a third
  control.** The page already renders `compare/v2` against the previous
  run whenever the store has one (`UX-203`), so a button that offered
  the comparison would navigate to what the reader is already looking
  at — the dead affordance `UX-194` ruled out. Previous and latest are
  the two neighbours that are one click; on the latest run "latest" is
  not offered, for the same reason.
- **The trace is not offered for a run the server was not started on.**
  A timeline belongs to its own snapshot, and rendering another run's
  would be a second decision (`UX-296` moved that cost off the startup
  path deliberately). `run.json.has_timeline` is `false` for a switched
  run, so the handoff is undrawn rather than dead.
