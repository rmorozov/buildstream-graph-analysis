# Audit round 23: the report learns to answer first

Run on 2026-08-22, same retained environment as rounds 10-22. Two
inputs: the sibling's landing of the entire round-22 slate
(UX-198..206, nine items), and a second external review of the
shipped viewer — this one a Pareto argument rather than a feature
list, evaluated the same way as the first: claim by claim, against
the code.

## The landing, verified — eight hold, one only at home

The review agent re-ran nine mutations across the slate. Eight
reddened the guards that claim to watch them: the tab opening moved
after the fetch (two gesture tests red), section ids stripped,
questions dropped from the export, the attribution ticker removed,
name-sniffing put back above the schema (both round-22 fixtures
red), `idle_us` computed in the viewer, the compare document dropped
from `payloads()` (five red), the finding-to-query linkage detached,
thresholds compared against rendered text. The export was driven
live from a scratch venv install: 88,449 bytes, seventeen sections,
no error banner, the page itself 68,087 B against the 80,000 B
ceiling. Suite: **2,584 passed, 0 failed** (two initial failures
were a stale editable install predating the `bga._tools` mapping —
environmental, gone after `pip install -e .`); lint clean; the
status table and every task file's marker agree.

The ninth mutation is the round's finding, filed as **UX-213
(High)**: with the critical path's widths made uniform and the
blast tree's depth hardcoded flat, **everything stays green**. The
guards UX-206's acceptance names are pinned to
`examples/06…/.bga/runs/20260821T170127Z/run` — a capture that is
not in git and that no CI creates — so nine tests skip on every
machine but the sibling's. "Six mutations, each red" was only ever
true where the capture lives; round 21's guards-that-cannot-fail
class, back in the newest tests, wearing a skip.

Verification also caught the trend colouring being a **second
verdict chain** (**UX-214**, Medium): `_mark_verdicts` classifies
on band edges alone and emits `within_band`, a value outside
`schemas.VERDICT_KINDS` — so a run below the band but inside the
observed extent colours *improved* where `bga compare` on the same
pair answers `within_observed_range`. UX-170's disputed region,
re-litigated by a dot. The published `compare/v1` schema carries no
`enum` for `verdict_kind` either — the closed set UX-201 promised
external consumers exists only in Python and the viewer.

## The review, synthesized

The review's verdict is one this direction accepts in full: **stop
adding major viewer architecture; spend the next iteration on
compression and actionability.** Its diagnosis was checked against
`boot()` and holds — the page assembles evidence, overview, band,
verdict, summary, fourteen generic sections, then the drawings and
tools, all at one visual level; the TOC and collapse compensate for
density rather than solving prioritization. Its central observation
is the round's best sentence: the user has to read too much before
knowing what deserves attention, while the answer the product is
framed around — *what should I fix first, and what is it worth* —
already exists in the published payload and renders mid-list
(`blast-radius-ranking` is a finding like any other; the
chain-bound diagnosis computed at `bga/findings.py:974` is
published only as a clause of one finding's sentence).

- **Adopted**: first screen = decision (**UX-207** — with the house
  adjustment that the panel's inputs enter `analyze/v1` as a
  published `headline` block first, because a viewer that derives
  the diagnosis is a second analyzer; the same rule that put the
  compare payload and the blast depth into the JSON). Every
  important object carries its investigation — path-box popovers,
  a declared element-column role giving rows a generic Inspect,
  Copy on every SQL block, Top-N presets, blast example chips
  (**UX-208**). Questions for names and a rail for the contents
  page, the question library folded, the trend shrunk (**UX-209**).
- **Declined with the review's own argument**: the stat-card
  dashboard (its §15). bga's numbers are relational; a card grid
  is where the relations go to die.
- **Adjusted**: the review's compact overview sketches an "Other"
  row — a viewer-side sum. The compaction lands without it: fold
  the tail bars, print no number the pipeline did not publish.

## What the review missed

- **It praised the question library without reading the SQL**
  (**UX-210**, High). Four of six canned queries are track-blind:
  `element-time` groups every slice by name (Plane 2 command names
  pollute the per-element answer), `stalls` windows over all
  tracks (interleaved native slices zero the gaps it promises),
  `sandbox-tax` subtracts any time-nested slice regardless of
  track — wrong even on Plane 1 alone whenever two elements
  overlap — and `dependency-wait` matches names globally. Confident
  wrong answers on exactly the merged two-plane traces the tool is
  proudest of.
- **Its remember-my-state item is `localStorage` thinking**
  (**UX-211**, Low). The house ethos — evidence you can paste —
  wants filters, thresholds, sort and collapse in the URL fragment,
  which also survives `file://` exports where storage does not.
- **It never looked at the drawings' color-only encodings**
  (**UX-212**, Low). The trend's verdict dots and the band's two
  rectangles differ only by palette; the incomplete-snapshot
  squares in the same function already prove the shape-channel
  pattern.

## Standing

The Pareto turn is right, and it is earned: two rounds built the
viewer's capabilities, and the second reviewer's list of what
exists is this direction's own list. What changes hands now is
emphasis — reorder, compress, connect — plus the two defects
verification put on the table. Priority for the sibling: **UX-213
first** (a green suite must mean what it says before anything else
lands on it), then **UX-207** (the decision panel, and the
`headline` publishing everything later hangs off), then **UX-210**
(wrong answers beat missing features), then **UX-208 and UX-209**
in either order, with **UX-214** riding whichever lands near the
store, and UX-211/212 as polish. Two external reviewers have now
read this viewer and converged with the audits on where it stands;
the difference each time was the part only verification supplies —
the claims were true, except where they were only true at home.
