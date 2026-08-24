# UX-258: the blast ranking tells you to optimize the base image

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R1, who acts on the ranking; R3, who knows which of it the graph forbids | **Topic:** analysis

## Motivation

Reported from a real project and reproduced on a 1,202-element run.
`bga analyze` publishes:

```text
next_steps[0]: "toolchain.bst is the first thing to fix - this is what
                changing it rebuilds."
                argv: ["bga", "blast", "toolchain.bst", "/tmp/vrun"]

blast_radius["toolchain.bst"]:
  downstream_count    1201
  element_kind        "import"
  is_structural_kind  true
```

The advice is true and unactionable. A base image, a toolchain, a
`host_strip_tool` has a thousand dependents **on purpose** — that is
what makes it a base image. "Changing it rebuilds everything" is a fact
about the graph, not an optimization.

**The tool already knows.** `is_structural_kind` is computed in
`bga/analyzer.py` and published on the entry the ranking puts first.
And `bga/findings.py` applies exactly the right rule one function
away — `_criticality_findings` excludes structural kinds outright:

> `and not item[1].get('is_structural_kind')`
> *"UX-76: structural elements are excluded rather than annotated
> here"*

The blast ranking never got the same treatment. This is not a new
policy; it is `UX-76`'s policy reaching the one ranking it skipped.

## Required Fix

1. **Structural elements are reported, not ranked as actions.** They
   leave `blast-radius-ranking`'s ordered list and the `next_steps`
   that follow from it, the way `UX-76` removed them from criticality.
2. **They stay visible.** A separate statement — *"`toolchain.bst`
   reaches 1201 of 1202 elements; that is the graph's shape, not a
   task"* — because `UX-203` was filed over unreachable views and
   hiding them would trade this defect for that one.
3. `next_steps` follows the corrected ranking, so the first thing the
   reader is told to run is a thing they can act on.

## Out of Scope

- Changing what `is_structural_kind` means, or which kinds are in
  `STRUCTURAL_ELEMENT_KINDS`. That set is `UX-76`'s and this item
  consumes it rather than revisiting it.
- Removing structural elements from `bga blast`. Asking *"what does
  changing the toolchain rebuild"* is a legitimate question with a
  legitimate answer; this is about what the report volunteers.

## Acceptance Test

On the 1,202-element run, `blast-radius-ranking` no longer leads with a
`is_structural_kind` entry and `next_steps[0]` names an element a
reader can act on; the structural entry is still present in the
payload and still reachable in the report, with its count stated. A
graph whose top blast entries are *all* structural still says
something rather than rendering an empty ranking.

## Outcome

**Status:** 🟢 Fixed & Verified

`UX-76`'s rule reached the ranking that skipped it. On the same
1,202-element run, before and after:

```text
before
  1. toolchain.bst (1201 downstream elements) [structural kind: import]
  2. layer00/mod037.bst (753 downstream elements)
  3. layer00/mod003.bst (753 downstream elements)
  next_steps[0]: "toolchain.bst is the first thing to fix"

after
  1. layer00/mod037.bst (753 downstream elements, at or above p99 of this run)
  2. layer00/mod003.bst (753 downstream elements, at or above p99 of this run)
  3. layer00/mod058.bst (739 downstream elements, at or above p99 of this run)
  these 3 are within 2% of each other - the order between them is not a
  difference worth acting on
  Shape: half of this run's 1202 elements reach 30 or fewer, the top tenth
  reach 465 or more (max 1201)

  Reaching most of the graph by design: toolchain.bst (1201 downstream) -
  structural elements (import) whose dependents are the graph's shape, not
  a task

  next_steps[0]: "layer00/mod037.bst is the first thing to fix"
```

`next_steps` follows the corrected ranking without a second change,
because it already read the ranking's own elements.

**It is still reported, with its number.** `UX-203` was filed because
views were unreachable; answering this by hiding `toolchain.bst` would
have traded one defect for an older one. The new `blast-radius-structural`
finding carries the element, its count and its kind, and has its own
provenance entry (`UX-229`) and its own row in `cli.md` — both demanded
by existing guards rather than remembered.

### This was an existing rule, not a new policy

`_criticality_findings` has excluded structural kinds since round 12,
citing `UX-76`: *"structural elements are excluded rather than
annotated here"*. The blast ranking annotated instead, via
`structural_kind_tag`. One guard here pins that premise: if criticality
ever stops excluding them, this item's argument is gone and the file
fails loudly rather than quietly guarding nothing.

**Mutations verified red and reverted (2 of the round's 12):**
structural elements returned to the ranking; the structural statement
suppressed.

**Deviation from the Required Fix:** none.

Small tier: `2118 passed, 1142 deselected in 44.79s`.
Full suite: `3257 passed, 3 skipped in 427.82s`. `make lint`: clean.
