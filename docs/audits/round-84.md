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

## What the round found

**Five of the fifteen filed premises were false or half-false**, and
every one was caught by re-measuring before implementing rather than
at the merge:

| item | what the filing said | what the tree said |
|---|---|---|
| `UX-589` | the namer read a junit an earlier step left behind | that junit was the run's own; the two names were true, and `UX-592` had already explained why they fail only under load |
| `UX-590` | `csv` is not in the writer's registry | it is — six subcommands declare it; what `UX-573` removed was a *path* claim |
| `UX-598` | two of four percentile rows publish no distribution | all four do; the filing's `grep` was a proxy that could not see `correlate/v2`. The real gap was one level down and worse — neither key was *declared* |
| `UX-597` | three release rows and no tag | two releases and a pre-versioning row: `0.2.0` was never a version in the tree |
| `UX-611` | `bga whatif` prints `the top 3 are worth 23.1s` | that is the `analyze` headline. The gap was real; the quoted string was not its evidence |

Round 83's finding was that *a sentence a guard reads is true and a
sentence no guard reads has drifted*. Round 84 is the same finding
applied one level up: **a filing is a sentence no guard reads.** Four
of the five had stood for a round; `UX-589`'s had been contradicted by
another item closed in the same round that filed it.

The practice that caught them is cheap and is now the round's rule:
re-measure the Motivation, paste the result, and correct the file in
place before writing any code.

### The defect only a merge could find

`0bc5aff` on `main` — CI adopting the coverage map its own run
measured — turned `test_the_loop_stays_fast.py` red on PR #201's
*merge* commit while both parents were green. `--cov-context=test`
attributes a module's import-time lines to every test that imports it,
so 38 of 85 mapped modules named 100+ of 449 test files and a
one-module diff selected 180. That is `UX-605`; `UX-606` is the second
finding underneath it, that the ≤25 bound it restored was itself a
claim about one well-chosen module.

### Guards that did not discriminate

Six, across five tracks, each found by its own mutation rather than by
review: a reporter clause vacuous in both directions, two clauses
comparing `parse_instant` against itself, a shape check accepting a
lowercase prose word, a currency scan that went red on the preamble,
and a finding typed out as a literal that the clauses around it
already implied. Each is recorded in its item's Outcome.

## Landed

Filled from `closed.md` at the gate, not typed.

## The gate

`make test`, `make lint`, the index counts derived, this document, then
the PR.
