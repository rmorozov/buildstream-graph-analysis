# UX-371: a fifth of the page is repeated text

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-360 (the volume budget), UX-305 (emphasis is a budget) | **Serves:** anyone reading more than the first screen | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome

Round 59. The second of the Required Fix's two shapes: the repeated
provenance line was collapsed into one statement about the list.

**Where the concentration was.** A per-section probe put the worst
repeats in two chapters at once — `"No named threshold; computed in
bga/findings.py"` ×6 in `decision` and ×6 in `provenance`, `"Where the
time is: …"` ×3 in `decision` plus one per element section. The cause
is one line: `renderWhyRanked` draws the provenance record of the
finding each top action came from, and on both fixtures **all three
actions come from one finding** (`blast-radius-ranking` on `golden`),
so the same record was rendered once per row — three identical rule
blocks on the first screen.

`renderDecision` now decides whether that record is shared by every
action. Where it is, the per-row copies are suppressed and the rule is
stated once *below* the list it ranked, under "How these were ranked" —
below, because the reader came for the actions. Where the actions come
from different findings there is no shared rule and the per-row
placement stands, so this is a branch and not a move.

**Measured, one instrument either side** — every `p`, `li`, `summary`,
`td`, `h3`, `h4` over 40 characters, every chapter and every `details`
open:

```text
                     blocks  distinct  repeated chars  of total  share
golden      before       81        61           1,876    11,048  17.0%
            after        77        61           1,434     9,730  14.7%
macro_micro before      180       138           4,769    26,919  17.7%
            after       176       138           4,401    25,681  17.1%
```

**Distinct is unchanged on both**, which is the Falsification's
discriminating half: a copy was removed and no claim was.

**A deviation from the filing, recorded.** The Motivation's 21.6% is
not comparable with either column above. Round 58 measured 4,742
repeated characters out of 21,914; this round measures 4,769 out of
26,919 on the same fixture with the same rule. The repeated count
agrees to within 27 characters — the denominator does not, because the
two passes opened a different set of folds before counting. The bound
is therefore set against a measurement taken by the guard that enforces
it, and both readings are recorded beside it in §5a so the next round
compares like with like. The item's premise — a fifth of the page said
twice, concentrated on the first screen — is unaffected.

**The bound, and what it does not do.** `REPEATED_SHARE_MAX = 0.21` is
a ceiling on the page, not a ratchet on this item: mutation M1 (the
shared branch removed, so the rule renders per row again) restores
17.0%/17.7% and **passes** the share clause. What catches it is the
placement clause in `test_why_is_this_ranked_first.py`, which holds
which placement the data calls for. That division is deliberate — a
budget tight enough to catch a three-block regression would fail on the
next item that adds a paragraph — but it is worth stating, because the
share number alone would have read as the guard for this fix and is
not.

`test_why_is_this_ranked_first.py` had asserted the rule's *position* —
one `.why` inside every row's fold — which is why this change broke it.
It now asserts reachability (the sentence is under the row or stated
for the list), with a second clause holding the placement in both
directions, so the first cannot be satisfied by never printing the
sentence at all.

Golden's export bound moved 567 B to 354,000, all of it source: the
data half is 89,154 B either side of the change, which is the split
`test_the_data_is_the_documents_and_the_schemas` exists to tell apart.

### Falsification run

Six mutations against the committed tree, all caught:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | the `shared` branch removed — the rule renders per row again | `test_the_rule_is_stated_where_the_findings_put_it` |
| M2 | `REPEATED_SHARE_MAX` tightened to 0.17 | `test_repetition_is_under_the_budget[macro_micro]` |
| M3 | `DISTINCT_BLOCKS` raised by one | `test_nothing_was_deleted_to_meet_it` (both) |
| M4 | the block walk replaced by a sentence splitter | `test_the_count_is_of_blocks_and_not_sentences` (both) |
| M5 | the copies removed and the shared rule never stated | both rule clauses |
| M6 | the branch collapsed — one rule hoisted whatever the findings | `test_two_findings_behind_two_actions_keep_their_own_rules` |

M6's clause exists because **no committed fixture ranks its actions
from more than one finding**, so the `else` branch would have been
asserted against nothing — the gap `UX-368` spent four rounds inside.
It builds the payload by re-pointing one action at another published
claim.
