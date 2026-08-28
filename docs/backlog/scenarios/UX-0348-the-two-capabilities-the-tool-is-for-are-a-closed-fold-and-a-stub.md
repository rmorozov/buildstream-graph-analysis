# UX-348: the two capabilities the tool is for are a closed fold and a stub

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-298 (the timeline speaks Perfetto), UX-312 (the canned question library), UX-172 (bga blast) | **Serves:** the reader who came for the thing this tool does that others do not | **Topic:** viewer

## Motivation

Two things distinguish this tool: it hands a build's two planes to
Perfetto as one timeline with a query library, and it answers *what
does changing this rebuild*. Measured on the exported report, which is
the shape a reader is most likely to be handed:

**Perfetto** is a section 5.9 screens down, 216 px tall, holding four
`details` — `Scheduling (3)`, `Execution (4)`, `Dependencies (2)`,
`Resources (4)` — of which **zero are open**. Thirteen queries, all
closed, under one paragraph of instructions. Nothing on the page shows
what a query returns, and the section is the smallest in its chapter.

**Blast** is this, in full:

```text
Blast radius
Not available in an exported report - the search asks the server, and
there is not one here. Run bga blast <target> <run>
```

103 px, one placeholder command with angle brackets, in a chapter
titled "What if I change this?". The rail entry for it reads **"Blast
offline"** — the navigation announces the capability as unavailable.

The data is not missing: `signals.blast_radius` is a column of the
element table, and `resource_blast` is its own section. What is missing
is the thing the section is named for. And on the first screen, two
`Next` steps *do* print a real `bga blast core.bst <run>` with a Copy
button — so the export can spell the command with the run's own path,
and the section that exists to spell it does not.

## Required Fix

**Perfetto.** The section leads with what the handoff *is* — one
button that opens this run's timeline, and one worked example showing a
query and the shape of its answer — before the library of thirteen.
The four category folds stay; they are the library, not the pitch. It
moves to where a reader meets it: `UX-286`'s chapter order puts "What
if I change this?" second, and the timeline is the answer to *how do I
look at this myself*, which belongs beside the decision rather than
below the findings.

**Blast.** The export's blast section spells the real command for this
run, the way the first screen already does — target prefilled from the
elements the report ranked, run path filled in, Copy button — instead
of `<target> <run>`. The rail entry names the capability, not its
absence: "Blast radius" with the served/exported difference stated
inside the section, which is where `UX-282` put the Perfetto fallback
for the same reason.

## Out of Scope

- Making the interactive search work offline. It asks the server
  because the answer is a graph walk over the whole run; `UX-297`'s
  streaming boundary is where that would be decided, not here.
- Embedding a Perfetto screenshot. `UX-307` and the export's size
  budget both argue against shipping an image; the worked example is
  text.

## Acceptance Test

On the exported report for both committed fixtures: the Perfetto
section carries one open worked example before any closed fold, and its
top is within the first N screens (the bound `UX-347` sets). The blast
section's command contains no `<` placeholder and contains the run's
own path, asserted by reading the rendered text. No rail entry contains
the word "offline".

## Outcome (round 53, 2026-08-28) — 🟢 Done

### The gap, measured

The exported report, both committed fixtures, at 1440x900 with every
chapter opened:

```text
             perfetto  216 px  order=['fold', 'fold', 'fold']  folds=4 open=0
             columns  []
             blast    103 px  heading='Blast radius'
             command  'bga blast <target> <run>'  copies=0
             rail     ['Blast offline']
```

Thirteen queries behind four closed folds, nothing saying what any of
them returns, and a command with two angle brackets in it.

### After

```text
golden       perfetto  758 px  order=['worked', 'fold', 'fold']  folds=4 open=0  top=3.6
             columns  ['element', 'spans', 'seconds']
             blast    heading='Blast radius'
             command  'bga blast base.bst /tmp/tmps481mqy5/golden-run'  copies=2
             rail     ['Blast radius']
macro_micro  perfetto  758 px  order=['worked', 'fold', 'fold']  folds=4 open=0  top=5.1
             columns  ['element', 'spans', 'seconds']
             blast    heading='Blast radius'
             command  'bga blast core.bst /tmp/tmps481mqy5/macro_micro-run'  copies=2
             rail     ['Blast radius', 'Blast radius distribution']
```

The two runs publish different first elements (`base.bst`,
`core.bst`), which is the point of reading the command rather than
composing it.

### One query in full, and the columns it returns

The worked example is a `div`, not an open `details`: the acceptance
is that a reader meets it *before* any fold, and a fold that happens
to be open is one click from being the closed thing this item was
filed about.

What it adds over the library entry is `returns:` — the columns the
query comes back with, each with a sentence. Declared, never
illustrated: a sample result table would be some other run's numbers
pasted into this page, which is the shape of lie most of this
repository's guards exist to catch. The guard reads the declared
column names back out of the SQL (`as <name>`), so a column that is
described but not selected reddens.

The four category folds stay closed. They are the library, not the
pitch, and `UX-347` spent a round recovering the height that opening
them would spend again.

### The command is read, not composed

`renderBlastOffline` takes the first `next_steps` entry whose `argv[1]`
is `blast` and prints `argv` joined — Direction 7's rule, that the page
never derives what the pipeline decides. Which element is worth asking
about is a ranking, and a page that picked its own would be a second
one. When a run publishes no blast step, the section says to run
`bga blast` against this run and prints no command at all, rather than
inventing a target.

The served/exported difference is stated inside the section (`UX-282`),
and both shapes now carry `data-toc-label="Blast radius"`, because a
reader looking for the blast radius is looking for the same thing
either way.

### Mutations verified red and reverted (11)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `19dd2fe`.

| # | mutation | reddened |
|---|---|---|
| M1 | no worked example — the library alone, as filed | 4: `test_a_worked_example_comes_before_any_fold`, `test_the_example_says_what_comes_back` |
| M2 | the example drawn, but below the four folds | 2: `test_a_worked_example_comes_before_any_fold` — and the `returns` clause stays green, so the two are separate properties |
| M3 | the library's folds `open` by default | 2: `test_the_library_stays_folded` |
| M4 | a declared column (`slices`) the query does not select | 2: `test_the_example_says_what_comes_back` |
| M5 | the lead drops the one-trace handoff and the absence sentence | 2: `test_the_lead_says_how_to_open_the_timeline` |
| M6 | `bga blast <target> <run>` again — the defect itself | 6: the placeholder, the published-step and the run-path clauses |
| M7 | the page composes `bga blast all.bst …` instead of reading `next_steps` | 4: `test_the_command_is_the_published_one`, `test_the_run_path_is_in_it` |
| M8 | the heading reads "Blast offline" | 2: `test_the_section_names_the_capability_not_its_absence` |
| M9 | the export ships `renderBlastSearch` after all | 7: the blast clauses, and `test_the_export_does_not_ship_a_search_box_that_cannot_work` in `test_a_report_you_can_navigate.py` |
| M10 | the lead quotes a button label `index.html` does not draw | 1: `test_the_quoted_button_label_is_the_one_the_page_draws` |
| M11 | `data-toc-label` dropped, so the rail titles the key | 2: `test_the_rail_names_the_capability_not_its_absence` — *"the rail entries for this section are ['Blast']"* |

M2 is the one that matters for the acceptance's wording: it draws the
example, so only the ordering clause reddens.

### Deviation from the Required Fix

- **"one button that opens this run's timeline"** inside the section:
  not drawn. The button exists once, in the header
  (`index.html`'s `Open timeline in Perfetto`, `UX-198`), and a second
  one would be `UX-338`'s defect on a control. The lead names it by
  the label the page actually draws — guarded source-level by M10's
  clause, because both committed fixtures are snapshots *without* a
  build log and no browser measurement of them can reach that branch.
  For those runs the lead says the timeline is absent and why, which
  is `UX-194`'s rule rather than a dead pointer.
- `test_the_export_does_not_ship_a_search_box_that_cannot_work` used
  to assert the *section's* absence. After this item that is no longer
  what the clause means — the export may not ship the box and must
  ship the section — so it now asserts the section is present with no
  form in it, and its served counterpart has one. Both directions, so
  the guard cannot pass by both shapes drawing the same thing.
