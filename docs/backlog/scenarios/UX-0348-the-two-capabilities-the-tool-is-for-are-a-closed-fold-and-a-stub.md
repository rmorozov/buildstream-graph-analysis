# UX-348: the two capabilities the tool is for are a closed fold and a stub

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-298 (the timeline speaks Perfetto), UX-312 (the canned question library), UX-172 (bga blast) | **Serves:** the reader who came for the thing this tool does that others do not | **Topic:** viewer

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
