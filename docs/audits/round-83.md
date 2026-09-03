# Round 83 — the twenty-four rows round 82 filed against the documents

Input: the twenty-four rows [round 82](round-82.md) filed by reading
every document against the tool it describes. That review's finding is
the shape of this round:

> a sentence a guard reads is true; a sentence no guard reads has
> drifted at the rate the tool moves.

So most of these items are not "correct a sentence". They are "give the
sentence a guard, and let the correction follow from it" — the `UX-549`
shape (a figure the guard derives) and the `UX-511` shape (a block
labelled with its date and its cuts), extended to the places round 82
found them missing.

## Decomposition

Surfaces were derived before the split, not guessed. The one real
hotspot is the pair of shared docs guards —
`tests/unit/test_docs_links_and_commands.py` and
`test_a_counted_figure_is_derived.py` — which four items extend; those
four are serial. Every other item either owns its surface or writes a
new guard file named for its claim.

| phase | tracks (parallel) | serial within a track |
|---|---|---|
| A | `UX-563`/`564`/`566` · `UX-574` · `UX-586` | the three registry decisions share Part 32 |
| B | `UX-575`→`579` · `UX-577` · `UX-576` | `579` consumes `575`'s piped shape |
| C | `UX-570` · `UX-571` · `UX-572` · `UX-573` | — |
| D | `UX-580`→`581` · `UX-582` · `UX-583` | both extend the Serves guard |
| E | `UX-565` · `UX-567` · `UX-568` | — |
| F | `UX-569`→`584` · `UX-585` | both extend the shared docs guards |
| G | the gate: suite, lint, the index counts, this document | — |

Three files are merge hotspots every track is told not to touch, and
the orchestrating session edits once, at the end:
`docs/backlog/scenarios/README.md`, `closed.md`, and `tests/tiers.py`
with `tests/ci_reference.json`. That rule is `UX-561`'s, and this is
the first round to carry it in the briefs rather than discover it.

## Landed

*(filled per phase)*

## Premises falsified by measuring

Round 81 re-measured thirteen filed rows and seven did not survive.
Every track this round is told to re-measure before implementing, and
to correct a task file's Motivation in place when its premise does not
hold. What that found is recorded here.

*(filled per phase)*

## The gate

*(filled at the end)*
