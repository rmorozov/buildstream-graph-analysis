# UX-372: the page has one reader

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-231 (every direction names its reader), UX-353 (the roles table), UX-365 (the finding that claims the superlative) | **Serves:** the build engineer, the CI owner and the module author, who currently share one page | **Topic:** viewer

## Motivation

The round asked whether the report should show the biggest problem *per
role*. It does not show one per role because it does not know roles
exist.

`bga:role` is in the vocabulary, and it is a **column** role — what a
cell is for a renderer, checked in `bga/schemas.py` against a closed set
and read by `bga/viewer/format.js`. There is no reader role anywhere in
the payload or the page.

So the page opens with one question — "What should I do?" — answered
once, for whoever is looking. Measured on `macro_micro`, the three top
actions are all the same kind of advice: shorten this element, shorten
that one, shorten the third. That is the right answer for someone who
can change `core.bst`. It is not an answer for:

- **the CI owner**, whose lever is `capacity-recommendation` (builders
  x max-jobs, finding #9) and the efficiency gate, not any element;
- **the module author**, who cannot see their own element unless it
  happens to be in the top three, and whose question is "is my thing a
  problem" rather than "what is the biggest problem";
- **the person who ran the build once** and wants to know whether the
  number is normal, which is `cache-hit-ratio` and the trend.

Every one of those answers is already computed. `capacity-recommendation`
is finding #9 of 11. The element table can be filtered to one element.
The cache and trend sections exist. What is missing is any statement of
who each is for, so the reader does the routing.

## Required Fix

Name the readers, and route the top of the page by them.

- A small closed set — the roles `UX-231` already made every *direction*
  name, applied to the report's own findings.
- Each finding declares which reader it serves, in the contract, so the
  page does not derive it (Direction 7).
- The decision chapter offers the biggest lever **for the reader who
  says who they are**, defaulting to today's behaviour when nobody says.

The default matters: this must not become a page that answers nothing
until you fill in a form.

## Falsification

Every published finding declares a reader, and the set of readers with
at least one finding is more than one. That fails today at zero.

Then the routing: choosing a reader changes which finding the decision
chapter leads with, and choosing a different one changes it again. A
selector that reorders nothing is furniture.

## Out of Scope

Per-role *pages*. One page, one payload; the roles select what leads,
not what exists — `UX-281` is what happens when the tool grows pages
nobody navigates back from.

## Outcome

Round 59. Five readers, declared in the contract and routed by the
page.

**The vocabulary is `roles.md`'s.** R1-R5, by their own ids, so the
backlog's `Serves:` lines and the payload speak one language rather
than two — `UX-353` is what happens when they do not. R6-R8 are absent
for the reason the filing's own gap section gives: their questions live
across builds, and one run's findings have nothing to put under them.
`docs/design/roles.md` gained a fourth traceability rule saying so.

**Declared, not derived.** `bga/findings.py` carries `FINDING_READERS`,
a map from every one of the twenty-one ids the module can emit to the
reader it serves, and `compute_findings` stamps `finding['reader']`
once over the finished list. A map rather than an argument at nineteen
call sites, because the interesting question about the assignment is
*who is left with nothing to read*, and that question cannot be asked
of nineteen scattered literals. `reader_index()` then publishes
`readers`: for each reader this run has findings for, their question
and `leads_with` — the finding that is their biggest lever.

**The headline wins where it speaks.** Severity-then-published-order
alone gave R1 `wait-category` on `macro_micro` — "5.9% of wall-clock is
UNTRACKED HEAD", 2.72s — while `headline.top_actions` and the decision
chapter both named `time-concentration`, worth 23.1s. That is exactly
`UX-365`'s defect one field over, and the fix is not a second ranking
but deferring to the first: the reader who owns
`headline.top_actions[0].finding_id` leads with that finding.

Measured on the two fixtures, after:

```text
golden       local-optimizer    -> blast-radius-ranking
             ci-gatekeeper      -> confidence
macro_micro  local-optimizer    -> time-concentration
             recipe-author      -> latent-heavies
             graph-owner        -> mesh-graph
             ci-gatekeeper      -> cache-hit-ratio
             capacity-operator  -> capacity-recommendation
```

Five distinct answers where there was one. The Falsification's two
clauses hold: every published finding declares a reader (it was zero of
eleven), and the set with at least one finding is more than one.

**The page.** The decision chapter offers a picker over the readers the
run publishes and shows the chosen one's lever below the diagnosis;
the choice travels in the fragment like every other view control. With
nobody chosen the chapter is exactly what it was, which the filing
requires in as many words and `TestTheDefaultStillAnswers` holds in
four clauses. `readers` also renders as its own section directly under
the decision panel — round 58's "the biggest problem for every role",
answered for everyone at once in one table.

### Two guards that read a literal where they meant a property

Both were found by this item's changes rather than by argument, and
both are stated as properties now:

- `test_the_authority_still_declares_an_order` pinned the first
  chapter's first three sections by name. That is a list of the
  chapter's members, not a property of the ordering, so adding a
  section to a chapter failed it while the thing it is non-vacuous
  about was untouched. It asserts the decision leads and the evidence
  follows in order.
- `test_the_rule_that_ranked_it_comes_from_the_provenance_record`
  (`UX-371`, the same round) had asserted the rule's *position*.

The geometry clause that would have been the third — nothing but the
diagnosis between the findings and the blast control (`UX-285`) — is a
real property and it held: `readers` went into the first chapter ahead
of `findings`, where the claim is about what sits *after* them.

### The export

Page 264,382 -> 267,286 B (+2,904, all checked-in modules); golden data
89,154 -> 91,401 B. Both companion guards — the module accounting and
the vendored-library check — stayed silent, which is the procedure
`PAGE_BUDGET_B` states rather than an assumption. The three bounds are
restated with the split named.

### Falsification run

Nine mutations against the committed tree, all caught:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | `capacity-recommendation` loses its reader | `test_every_published_finding_declares_one` |
| M2 | the stamp is a no-op — nothing declares a reader | six clauses |
| M3 | the headline no longer wins | `TestTheHeadlineWins`, all three |
| M4 | a reader is chosen for the user on load | `test_nobody_chosen_leads_with_nothing_extra` |
| M5 | the selector is furniture — one answer for everyone | five clauses |
| M6 | every reader offered whatever the run measured | `test_a_reader_with_nothing_to_say_is_not_offered` |
| M7 | the page picks the first, not the published lever | `test_the_lead_is_the_published_one` |
| M8 | the reader never reaches the fragment | `test_the_reader_reaches_the_fragment` |
| M9 | the fragment carries it and nothing applies it | `test_a_pasted_link_lands_on_the_same_answer` |

**Two of the nine passed first, and both were the instrument.** This is
the round's recurring finding, twice more:

- **M1 passed the exhaustiveness clause.** Its id scan read
  `'<id>', SEVERITY_<BAND>` and so found nineteen of the twenty-one
  ids, missing exactly the two whose severity is computed into a local
  and passed as a variable — `memory-envelope` and
  `capacity-recommendation`, *both* of which belong to
  `capacity-operator`, the reader this item was filed about. It reads
  `_finding(`'s first argument now, holds the count it found, and
  checks the map in both directions.
- **M9 passed the round-trip clause**, which loaded `uri + hash` on the
  page the browser was already on. That is a *same-document*
  navigation: nothing reloads, the DOM survives, and the select is
  still where the drive left it. A direct probe on a fresh page showed
  the reader coming back empty at the same moment. The fixture exports
  a second copy and loads that, so the second URL is a document the
  browser has not got.
