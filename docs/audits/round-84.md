# Round 84 — the fifteen rows round 83 left

Input: the fifteen rows open after [round 83](round-83.md) merged. They
are not one audit's findings. Three came from round 83's own tracks
reporting what they could not file themselves, three from architecture
review 14, and the rest from round 82's reading of the documents. What
they have in common is the shape round 83 established:

> a sentence a guard reads is true; a sentence no guard reads has
> drifted at the rate the tool moves.

Round 83 closed the documentation half of that. What is left is
mostly the other half — **quantities the tool publishes that no
document names**, and **guards that read the wrong thing**.

## Decomposition

Surfaces derived before the split. Three collisions decide the tracks:
`tests/unit/test_docs_links_and_commands.py` (`UX-599`, `UX-600`),
`docs/contributing/fixing-guide.md` (`UX-590`, `UX-603`), and
`UX-595`'s own Out of Scope, which defers anything needing the
requested-at instant until `UX-594` lands.

| track | rows | why together |
|---|---|---|
| A | `UX-602` → `UX-598` | both are a published quantity no contract names |
| B | `UX-593` → `UX-596` | both extend what the report prices, in `bga/report/` |
| C | `UX-594` → `UX-595` | the model stands on the measurement |
| D | `UX-599` → `UX-600` | one guard file |
| E | `UX-590` → `UX-603` | one guide |
| F | `UX-589` · `UX-604` | two guards that read the wrong text |
| G | `UX-591` · `UX-597` · `UX-601` | three documents, disjoint |

## Landed

Filled from `closed.md` at the gate, not typed.

## The gate

`make test`, `make lint`, the index counts derived, this document, then
the PR.
