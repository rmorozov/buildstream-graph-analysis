# UX-258: the blast ranking tells you to optimize the base image

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R1, who acts on the ranking; R3, who knows which of it the graph forbids | **Topic:** analysis

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
