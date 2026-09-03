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

23 rows, derived from `closed.md` rather than typed:

| | |
|---|---|
| `UX-563` | the ambiguous holder state is retired in the registry, not left for the next review to rediscover |
| `UX-564` | Parts 23 and 27 declined in the registry, and 32.4's ten signals mapped to what the analyzer publishes |
| `UX-565` | analyze reads the store's prior same-host runs; the sample count does not depend on when it is asked |
| `UX-566` | the spec carries its own map of which Parts are advisory, with the document that is current |
| `UX-569` | the two counts derive, backticked *.md names must resolve, and the planes' entry points are named as files |
| `UX-570` | the contents table and cadence sentence derive from the yml the workflow actually runs |
| `UX-571` | the facts cite the bst the guard ran on, dated; the machine still has 2.7.0 |
| `UX-572` | the equality names merge_record_streams and its guard; measured 174 raw to 87 joined |
| `UX-573` | the map walks tools/ and the viewer, enumerated from git ls-files, not the checkout |
| `UX-574` | argparse's usage error exits 1; the table derives from one registry in bga/exceptions.py |
| `UX-575` | a broken pipe on stdout exits 0 silently; the deferred flush is caught in a finally |
| `UX-576` | one derived count — seventeen — and a sweep that reads every counted phrase against questions.js |
| `UX-577` | the advised comparison is one the store can make; there was never a committed store to fix |
| `UX-578` | every prompted guide block is diffed against a fresh run or dated with its cuts listed |
| `UX-579` | every fenced bga line in the guides parsed by the real parser, executing only tracked operands |
| `UX-580` | R5 and R7 name the mechanisms that serve them; each row's served-by cell is derived from closed filings |
| `UX-581` | every direction carries landed/partial/declined, and a partial names a filed id or a stated decline |
| `UX-582` | §7's three prose tables are one derived ledger; four of the seven it called guardless had one |
| `UX-583` | the history table and the audits list are read against docs/audits/; three rounds were missing, and not the three filed |
| `UX-586` | the premise is a declared Outcome field the bands tool reads, not a phrase it sniffs |
| `UX-587` | the reference entry refreshed with the slope that explains it: 0.0185s per backlog row |
| `UX-588` | the floor comes from pyproject.toml and every annotation is walked for a PEP 604 union |
| `UX-592` | the harnesses wait for the mark; the from-nowhere branch has its own guard |

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

## What the round cost itself

Three defects this round caused and then had to find, kept because each
is a shape that will recur.

**Six tracks launched into one checkout.** The orchestrator omitted the
worktree isolation flag, so six agents edited `main`'s working tree
concurrently. Caught when a test file the session had not touched grew
five new tests. Nothing corrupted reached a commit — the briefs had
made the surfaces disjoint by file, which is the only reason. Each
track's partial diff was saved as a patch and handed back with "read
it, do not trust it"; two tracks re-derived their conclusions and
rejected the patch on measured grounds, one of them because the
patch's spec hunk targeted a Part 32 that does not exist in this tree.

**A derived count of a growing population.** `UX-569` made
`architecture.md`'s opening derive its backlog count from
`git ls-files`. The orchestrator files rows *during* a round, so the
next filing reddened a guard in a file the filer never touched — 598
tracked against 591 written, one commit after the merge. Typing the
new number would have re-armed it. `dev_close_task.py --check --write`
writes that sentence now, beside the index counts it already derived.

**Two guards that were each right.** `UX-582`'s scan holds that a `§N`
cited in a test file exists as a heading, in two documents. `UX-569`
then cited `§9` of `docs/contributing/style-guide.md` — a *third*
§-numbered document, one letter from `docs/design/styleguide.md` in
name. All four interpreters went red at the small tier. The fix is the
third document's ids, and the ambiguous set is byte-identical with it
(measured). The mutation that was supposed to prove the fix did not
land: `§([0-9][a-g]?)` read a planted `§42` as `§4`, so a two-digit
section had always been invisible. Both patterns take `[0-9]+` now.

## The gate

*(filled at the end)*
