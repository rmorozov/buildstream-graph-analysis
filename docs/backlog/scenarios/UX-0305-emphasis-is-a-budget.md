# UX-305: emphasis is a budget, spent once per block

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-304 (the tokens), styleguide §4.6 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer

## Motivation

The user's ask — rules for emphasis and color so valuable
information stands out — inverted into the rule that makes it
possible: emphasis only works when it is scarce. Styleguide §4
budgets it: one emphasized element per block, one accent for the
whole page, text in ink never in status tone, status tone never
without a shape. The current page grew section by section and has
never been audited against a budget — the audit *is* this task.

## Required Fix

A conformance pass over every rendered section against §4: demote
double emphases, move status tones off text onto badges/borders,
collapse any second accent into the one. Then the guards that keep
it: a booted check that no block contains two emphasis-class
elements; the status-tone-with-sibling check (`UX-304`); and the
checklist line in the fixing guide so a new section ships within
budget or amends the guide.

## Out of Scope

- New emphasis mechanisms (size scales, animation — declined:
  §4's budget is about scarcity, not new instruments).
- The chapter structure and ordering (UX-286's domain).

## Acceptance Test

The booted golden and 1,202-element pages pass the budget walk
(zero blocks with two emphasized elements; zero status-toned text
nodes; one accent hue in computed styles); mutation: bolding a
second value in the headline block reddens; the pass's demotions
are listed in this file's log with before/after screenshots or DOM
extracts for three sections.

## Outcome

🟢 **Done.** Five findings from the conformance pass, all fixed, and an
instrument that says the budget is kept rather than a claim that it is.

**What the audit found**, reading the stylesheet and then the booted
page in a real browser:

```text
1  a second accent, eight times   `var(--accent, #4a7ebb)` and
                                  `var(--muted, #777)` — fallbacks for
                                  tokens `:root` always defines, so they
                                  never applied and sat in the file as a
                                  palette nobody chose
2  a colour with no name          `var(--muted-bg, rgba(127,127,127,
                                  0.08))` — `--muted-bg` was declared
                                  nowhere, so the *fallback* was the
                                  live value
3  a fill wearing a text token    `.horizon-bar`
4  one class, two rules           `svg.sparkline` and `.spark-point`,
                                  declared by UX-226 and again by
                                  UX-303, disagreeing about width and
                                  about token grade
5  text wearing a status tone     `.delta.better` / `.delta.worse`
                                  coloured the *value*
```

**(1) and (3) are one defect seen twice**, and the rule that follows is
the item's most useful product: **a colour-valued `var()` fallback is a
second palette, and it hides the first from every guard that reads the
stylesheet.** `UX-304` was written a day earlier and asserts that a
fill names a mark-grade token; `.horizon-bar` filled with
`var(--accent, #4a7ebb)` and passed, because the guard matched
`var(--accent)` exactly. Remove the fallbacks and the same guard
reddens immediately. Geometry fallbacks — `var(--w, 0%)`,
`var(--head, 5.5rem)` — are what a fallback is *for* and stay; the
guard distinguishes by whether the fallback names a colour.

**(5) is §4.4's own example.** The number is ink now and the tone moved
to a marker beside it — `UX-212`'s triangles, which is simultaneously
§4.3's non-colour channel, so the delta carries its direction three
ways: the glyph, the sign, and the tone.

**The emphasis walk found nothing.** Zero blocks over budget on both
pages at 1440×900, 1280×800 and 390×844. Stated plainly rather than
implied as a rescue: what this item adds there is the **instrument**,
not a repair. The instrument had to be taught two things before it
measured anything real — a `<th>` is bold in every browser's default
sheet and is a column's *label*, and a block's own heading is its name.
Without those two exclusions the golden page reported dozens of blocks
over budget, all of them table headers, which is precisely how a scan
gets muted.

**The falsification round**, against the committed tree — eight
mutations, all discriminating:

```text
E1  a second value is bolded in a block       6 clauses red
E2  a colour fallback comes back              1 red
E3  a token is used and never declared        2 red
E4  a second accent hue token                 1 red
E5  one class, two disagreeing rules          1 red
E6  text wears a status tone again            2 red
E7  the runtime property loses its setter     1 red
E8  the checklist leaves the fixing guide     1 red
```

Two of them were green first time and both were the *mutation's* fault
rather than the guard's — one coloured an element the fixtures do not
render, and one left the checklist's words behind while removing its
lead-in. The second is the useful one: the clause was matching
"budget" and "sentence", words the fixing guide uses for other things,
so it would have passed on a deleted checklist. It matches the three
questions' own wordings now.

**The checklist.** §7 promised it would "join the fixing guide", and
the fixing guide is `docs/contributing/fixing-guide.md` — item 6 of §2
now asks the three questions and names the four guards that answer
them. Its §6 context map also gains the four viewer modules added
since it was written (`chapters.js`, `shapes.js`, `rawjson.js`,
`drawings.js`), which is a slice of `UX-294` taken on the way past
rather than a claim to have closed it.

**Out of scope, held.** No new emphasis mechanism, and the chapter
order untouched.
