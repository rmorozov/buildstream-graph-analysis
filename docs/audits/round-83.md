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

| | |
|---|---|
| `UX-563` | Part 8.2's `UNKNOWN` holder retired in the registry — §32.7.1, with the fixture that would have produced it |
| `UX-564` | Parts 23 and 27 declined, and 32.4's ten `signals` keys mapped to what the analyzer actually publishes |
| `UX-566` | the spec carries its own map of which Parts are advisory, each with the document that is current |
| `UX-574` | argparse's usage error exits **1**, not ingestion's 2; the table derives from one `EXIT_CODES` registry |
| `UX-577` | the advised comparison is one the store can make — and there is no committed store, see below |
| `UX-586` | the premise is a declared Outcome field the bands tool reads, not a phrase it sniffs |
| `UX-587` | filed by this round against its own CI; the reference entry refreshed with the slope that explains it |

## Premises falsified by measuring

Round 81 re-measured thirteen filed rows and seven did not survive.
Every track this round is told to re-measure before implementing, and
to correct a task file's Motivation in place when its premise does not
hold.

| row | filed | measured |
|---|---|---|
| `UX-564` | 32.4's other `signals` keys "verified present" | 4 of 10 verbatim; three renamed or nested, one computed and read by nothing |
| `UX-566` | Part 39 names 32 modules, 12 present | 40 named, 13 present |
| `UX-577` | the **committed** example store's next step refuses | there is no committed store and never has been — `git ls-files \| grep -c .bga` is 0, and so is every commit in history |
| `UX-577` | advise `--baseline-run <stamp>` | that flag appends a band sample; it does not replace the positional baseline, and the published argv exits 1 |
| `UX-586` | `--window 20` reports round 81's falsified premises | round 81 closed 23 rows; a 20-item window cuts the two the item itself cites |
| `UX-587` | (this round's own filing) the drift arrived with the last diff | `UX-442`'s carry: the second run confirms what the first sighted |

`UX-577`'s is the one that reflects on method rather than on a number.
Round 82 read `examples/06-macro-micro-optimization/.bga/runs/` — one
machine's untracked leavings — as a repository fact, and filed against
it. The store has since drifted on that machine, so the refusal the
audit pasted no longer reproduces there either. A reviewer reading a
tree cannot tell tracked from untracked by looking; `git ls-files` is
the question, and this round asks it before trusting a path.

## The gate

*(filled at the end)*
