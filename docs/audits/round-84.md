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

Derived from `closed.md` at the gate, not typed — **19 rows**.

| row | what it was |
|---|---|
| [UX-589](../backlog/scenarios/UX-0589-the-namer-reads-a-junit-the-run-did-not-write.md) | the failure namer reads a junit the run did not write |
| [UX-590](../backlog/scenarios/UX-0590-the-context-map-s-non-path-claims-are-unguarded.md) | the context map's non-path claims are unguarded |
| [UX-591](../backlog/scenarios/UX-0591-the-architecture-review-log-is-in-no-index.md) | the architecture review log is in no index |
| [UX-593](../backlog/scenarios/UX-0593-the-regression-verdict-carries-no-evidence-chain.md) | the regression verdict carries no evidence chain |
| [UX-594](../backlog/scenarios/UX-0594-a-capture-cannot-say-when-the-build-was-requested.md) | a capture cannot say when the build was requested |
| [UX-595](../backlog/scenarios/UX-0595-the-capacity-model-has-a-fact-base-and-no-model.md) | the capacity model has a fact base and no model |
| [UX-596](../backlog/scenarios/UX-0596-build-time-in-the-team-s-units.md) | build time in the team's units |
| [UX-598](../backlog/scenarios/UX-0598-two-of-the-four-percentile-rows-publish-no-distribution.md) | two of the four percentile rows publish no distribution |
| [UX-599](../backlog/scenarios/UX-0599-a-guard-pins-a-contract-version-by-typing-it.md) | a guard pins a contract version by typing it |
| [UX-600](../backlog/scenarios/UX-0600-the-rules-card-has-one-guard-it-cannot-mark.md) | the rules card has one guard it cannot mark |
| [UX-601](../backlog/scenarios/UX-0601-two-guard-ledgers-of-the-same-kind.md) | two guard ledgers of the same kind, two mechanisms |
| [UX-602](../backlog/scenarios/UX-0602-two-hard-gates-are-published-and-named-nowhere.md) | two hard gates are published and named nowhere |
| [UX-603](../backlog/scenarios/UX-0603-the-python-floor-reaches-no-reader.md) | the Python floor reaches no reader |
| [UX-605](../backlog/scenarios/UX-0605-the-touching-map-adopted-a-selection-that-is-everything.md) | the touching map adopted a selection that is everything |
| [UX-606](../backlog/scenarios/UX-0606-the-selectors-bound-is-measured-on-one-module.md) | the selector's bound is measured on one module |
| [UX-607](../backlog/scenarios/UX-0607-a-paragraph-in-the-guide-is-a-two-file-change.md) | a paragraph in the guide is a two-file change |
| [UX-608](../backlog/scenarios/UX-0608-fifteen-commands-the-context-map-never-names.md) | fifteen commands the context map never names |
| [UX-609](../backlog/scenarios/UX-0609-the-invariants-docstring-lists-five-of-six-gates.md) | the invariants docstring lists five of six gates |
| [UX-611](../backlog/scenarios/UX-0611-whatifs-saving-is-still-in-build-seconds.md) | what-if's saving is still in build seconds |

## The gate

```text
$ make test          6814 passed, 29 skipped in 267.38s (load 0.67)
$ make lint          All checks passed!
$ dev_close_task.py --check --write    0 problem(s) over 5 propert(ies)
```

Backlog after the round: **19 closed, 13 open**, against the
fifteen this round was handed. Two of the fifteen stay open with their
reasons on the row — `UX-597`, whose tags are cut and cannot be pushed
by this session's credential, and the `UX-610`/`UX-612` contracts pair,
which no track reached.
