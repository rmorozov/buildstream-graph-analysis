# UX-371: a fifth of the page is repeated text

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-360 (the volume budget), UX-305 (emphasis is a budget) | **Serves:** anyone reading more than the first screen | **Topic:** viewer

## Motivation

Counted over the rendered blocks a reader sees — every `p`, `li`,
`summary`, `td`, `h3`, `h4` longer than 40 characters, on `macro_micro`
with every chapter and fold open:

```text
138 distinct blocks, 17 of them repeated
repeated text: 4,742 of 21,914 block characters = 21.6%
```

The worst offenders:

```text
x9  "No named threshold; computed in bga/findings.py"
x7  "Where the time is: 4 element(s) are 71.9% of the 43.2s critical path…"
x5  "Together, the top 3 are worth 23.1s (50% of the build)…"
x5  "Also in: bottleneck critical path drawn critical path detail"
x4  "Published whenever the critical path has measured elements on it…"
```

Three of these are visible **on the first screen at once**: the decision
chapter draws three top actions, and each carries the same provenance
sentence and the same "No named threshold" line under it. A reader's
first impression of the page is the same two sentences three times.

**Sentence-level counting says zero.** The first pass of this
measurement split `main.textContent` into sentences and found no
duplicates at all, because the repeated blocks sit inside different
surrounding text and the splitter never produced identical strings.
Counting *blocks* is what shows it. Any guard for this has to count what
a reader sees as a unit, not what a regex finds between full stops.

Each repeat is individually defensible — `UX-229` says every claim
carries its provenance, and a finding cited twice is cited twice. What
nobody has measured is the total, which is a fifth of the page and is
paid for out of `UX-360`'s volume budget.

## Required Fix

A repetition budget, in the same guard as the volume budget, because
they are the same currency.

The design question the number forces: a sentence that appears nine
times is not a sentence, it is a footnote. The two shapes that fix it
without losing the claim:

- **State it once per section and reference it**, the way `UX-346` put
  the schema's sentence on a door rather than beside every value.
- **Collapse the repeated provenance line into the fold it belongs to**,
  so three top actions share one "how this is computed" rather than
  three copies of it.

## Falsification

The measurement above, as a bound: repeated block characters as a share
of block characters, against a stated ceiling. It is 21.6% today.

And the discriminating half, so the fix cannot be "delete the second
copy of everything": the count of *distinct* blocks must not fall with
it. Losing a claim is not deduplicating it.

## Out of Scope

Short repeated labels — column headers, units, control names. Those
repeat because they label repeated things, which is what a table is.
The floor at 40 characters is what separates a label from a sentence.
