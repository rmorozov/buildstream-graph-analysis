# UX-593: the regression verdict carries no evidence chain

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-229 (why bga believes what it believes), UX-221 (the culprits), UX-581 (the status that names this tail) | **Serves:** R4, the CI gatekeeper asked to defend a red gate | **Topic:** analysis

## Motivation

Direction 8's decomposition landed `UX-227`..`UX-230` and the CI
comment quotes a chain (`_why_block`). What it quotes is the
*candidate diagnosis*'s chain. The regression verdict itself — the
one a contributor argues with — publishes none:

```text
git grep -l "evidence chain" -- docs/backlog/scenarios   1 (UX-581's own file)
```

So "why did you call this REGRESSED" is answerable over `UX-221`'s
culprits by reading the numbers, and not by the tool.

## Required Fix

The regression verdict publishes the chain `UX-229` defined, over the
culprits `UX-221` ranks: the baseline it compared against, the band it
used, which elements crossed it and by how much.

## Out of Scope

- Re-arguing the verdict vocabulary (`UX-214`) — declined: this is the chain behind the word, not the word.

## Acceptance Test

A `compare` that verdicts REGRESSED publishes a chain naming its
baseline and its culprits; mutation: drop the culprits from the chain — red.

## Outcome (round 84)

### The Motivation re-measured

```text
git grep -l "evidence chain" -- docs/backlog/scenarios   3, not 1
  README.md (this item's own row), UX-581, this file
```

The count moved because this file and its row now exist. The substantive
half reproduced, on a pair regressing +9.5%:

```text
CI comment folds:  <details>Why the candidate looks like this
                     (CHAIN_BOUND_RATIO, over analyze/v5) - none for the verdict
compare/v2 keys carrying a verdict record: 0 of 28
text report:       Verdict: REGRESSED (+9.5%), then the band and the
                   culprits as two blocks with no rule, no baseline
                   reference and nothing joining them
```

### The close

```text
<details><summary>Why the verdict is REGRESSED</summary>
The candidate is +5.7% against baseline run <id>, which is outside the
noise band from 5 baseline runs (median +/- 3x scaled MAD) - so
regressed. 4 element(s) present in both runs grew, and the 4 largest are
cited.
Rule `DEFAULT_BAND_K` = `3.0` (bga/compare.py). Paths are into this
comparison's own `compare/v2`:
`baseline_run_id` = … · `baseline.total_duration_us` = 435000 ·
`candidate.total_duration_us` = 460000 · `deltas…` = 25000 ·
`baseline_band.n` = 5 · `…low_us` = 412761.0 · `…high_us` = 457239.0 ·
`element_deltas.counts.grew` = 4 · `element_deltas.rows[element_uid=
big.bst].delta_us` = 60000 · …tiny 40000 · …mid 30000 · …small 10000
</details>
```

Three rule cases, because a copied constant gets the third wrong: no
band → `_SIGNIFICANCE_PCT`; a band wider than the fixed rule →
`DEFAULT_BAND_K`; a band **widened** by `widen_band` →
`_SIGNIFICANCE_PCT` again, the band's own `k` no longer being the rule.

**One line of references, not a table.** The comment's total is capped at
60 lines and a second `<details>` table put the large-addition case at
**65**; a row per reference is unbounded, so they render as one line and
the block costs 10 whatever it cites — 57.

### Mutations verified red and reverted (16)

| mutation | reddened |
|---|---|
| drop the culprits from the chain | 3 |
| cite culprits by index, not uid | 3 |
| rank culprits by bare magnitude (the element that *shrank* is named) | 2 |
| never cite the band / always cite it, on a run with none | 1 / 2 |
| copy `_SIGNIFICANCE_PCT` as `1` / `DEFAULT_BAND_K` for the band's `k` | 1 / 1 |
| ignore `widened_to_fixed_pct` | 1 |
| publish a chain for `not_comparable` | 1 |
| quote a resolved value off by one | 6 |
| the CI comment / the terminal words its own sentence | 2 / 1 |
| uncap the citation | 1 |
| the terminal prints the raw evidence paths | 1 |
| drop the baseline reference / the crossing count | 1 / 2 |

Every anchor grepped back; all 16 landed.
`test_the_fixture_actually_regresses` is not mutation-covered: it
asserts the fixture reaches the sentence, not a claim about the code.

**Deviation from the Required Fix:** one, a boundary rather than a
choice. The record is **not a `compare/v2` key**: a new top-level key
must be declared in `bga/schemas.py` (the emitted-key census and the
unit census both fail otherwise) and that file was another track's this
round. Nesting the verdict's chain inside `element_deltas` to dodge the
declaration would put the record inside an object it cites, so it was
refused. `bga.compare.verdict_provenance` carries `document: compare/v2`
and every path resolves against the payload a reader already has;
publishing it as a key is a filing. `trace_query` is null — `TRACE_QUERIES`
is keyed by one run's claims, which deepen the candidate, not the pair.
