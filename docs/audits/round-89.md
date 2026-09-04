# Round 89 — the five open rows, and three the round itself found (2026-09-04)

Round 88 left five rows open, all filed by architecture review 16. This
round took all five in three parallel tracks on disjoint file ownership,
and filed three more from what the work turned up. Six rows closed,
three filed.

## What landed

| | | |
|---|---|---|
| `UX-651` | the spec's Part 32 block is two ids behind | Medium |
| `UX-652` | the currency guard resolves to a day, and a day holds three rounds | Medium |
| `UX-653` | a contract bump rewrites the record of what it superseded | Low |
| `UX-654` | the vocabulary module still says nine hints | Low |
| `UX-655` | a contract bump landed one level below the key population | Medium |
| `UX-657` | the priority column has no guard | Low |

Filed and left open: `UX-658` (a ninth topic exists that no open row may
carry), `UX-659` (two superseded ids sit on a live line of the spec's
registry).

## The round's shape: four unguarded copies of a guarded fact

Every closed row is the same defect at a different scale. A fact is
written down twice; one copy has a guard and is exact, the other does
not and has drifted at the rate the tool moves.

| the fact | the guarded copy | the copy that drifted |
|---|---|---|
| which contracts exist | Part 32.5's registry table | Part 32's opening block, two ids behind |
| the `bga:` vocabulary | `styleguide.md` §1a, 19 rows | `format.js`'s docstring, "nine" |
| a row's priority | — | both the index and the task file, 3 of 654 apart |
| what a log entry checked | `UX-353`'s retired-id guard | the entry itself, swept forward four times |

`UX-655` is the same shape one level in: the coverage *statement* was
guarded, and the population it quantified over reached one level less
than the schemas publish.

## Where the filings were wrong, and the measurement that said so

**`UX-655`'s proposed widening does not reach the keys it was filed
about.** The row asks for "a row under an array at any depth". Measured:
that rule is 218 keys and contains neither `level` nor `width`.
`analyze/v6`'s `parallelism.levels` node has **no `type` and no
`items`** — the row is declared entirely by `bga:columns` on the array
node. The rule that reaches it is 236 keys against today's 199, which is
within one order and so the row's own decision rule says *widen*. 37 new
keys, 15 of them undocumented, all now named in `docs/guides/cli.md`.

**`UX-651`'s "nothing present that nothing emits" needs three sets, not
one.** The block names `analysis/v9`, `graph/v9`, `run-context/v9` and
`trace/v9`, none of which are in `contracts.ids()`. A naive clause
reddens on all four. It reads `ids()`, `reads()`, and the ids Part 32
gives a numbered subsection to.

**`UX-652`'s day census was 26/9 when filed and is 27/10 now**, and the
commits after the credited item are four, not three. The row was filed
against a tree that had moved by the time it was worked — which is the
row's own argument, arriving as evidence for itself.

**`UX-653`'s premise held but its restoration was already in.** Review
16 had added the word *superseded* to the 2026-08-25 entry, so the
record was right and nothing was holding it there. Both halves of the
Required Fix landed anyway: the log is stated append-only below its
newest entry, and the guide names which of `UX-353`'s two greens is
meant.

**`UX-654`'s "one more side of the same equality" is false.**
`test_the_contract_names_its_vocabulary.py` holds `emitted ==
documented` at 19. `format.js` declares a strict *subset*, 17 of 19,
missing `bga:always_written` and `bga:markers`. Deriving cost two counts
and a subset assertion.

## Three guards that first did not discriminate

Each was caught by mutating it, and each is the `falsify` skill's own
failure mode.

- **`UX-651`'s citation clause.** Its first cut asserted that the cited
  item's task file names the newest id on the retired line. `UX-0535`
  names `analyze/v5` twice — it *created* it — so the exact defect the
  row was filed for passed. It now also requires the live id of the
  same family, which only the retiring item carries.
- **`UX-652`'s merge clause.** `test_a_merge_naming_two_items_closes_
  neither` survived the mutation that unanchored its regex, because the
  call is `re.match`, which anchors anyway. The mutation that reads the
  property is `.match` → `.search`.
- **`UX-657`'s pair clause** would have gone quiet on a row it could not
  parse and a file that declared nothing. Both non-vacuity clauses were
  added and both were mutated red.

## The one instrument this round did not re-decide

`UX-655`'s acceptance names three keys. Only `level` would actually have
reddened the naming clause: `width` was already "documented" through
`el.style.width`, `graph-width` and `--width 200`, because
`code_spanned` splits identifiers. That instrument is `UX-628`'s and the
row did not ask for it to be re-taken; the reach clause reads the row's
own columns instead. It is stated in `UX-655`'s Outcome rather than
fixed.

## What the round found while working

- **`UX-657`** — the index's `Priority` column had no guard and 3 of 654
  rows disagreed with their task files. Two of the three were written by
  hand in round 88, one round before the clause that would have caught
  them. `priority_disagreements()` is now `--check`'s sixth property,
  with one reading in the tool as `UX-387` requires.
- **`UX-658`** — `process` reaches the index's derived topic table but
  no open row may carry it: `UX-656` was filed and closed inside one
  round, so its row went straight to `closed.md` and never sat in the
  index the guard reads. A topic entered the vocabulary through the one
  path that is not checked.
- **`UX-659`** — `plane2/v1` and `plane2/v2` are in
  `contracts.superseded()` and sit on the block's live Plane 2 line, so
  `UX-651`'s retired-line clauses are outside them by construction.

## The gate

```text
make lint                All checks passed!
make check-clean         OK: no ignored files are tracked
python3 tools/dev_close_task.py --check
                         0 problem(s) over 6 propert(y/ies), 657 backlog row(s)
python3 tools/dev_touching.py --spread
                         11-126 of 473 test files, median 17
make test                28 failed, 7036 passed, 82 skipped, 17 errors in 289.32s
```

The 28 failures and 17 errors are all in **18 `bst`-invoking files**,
and they are this sandbox rather than this round. Run in isolation
against a worktree at the base commit `933de24` and against this branch,
the failing sets are identical:

```console
$ comm -13 base.txt head.txt   # only at HEAD - would be this round's
$ comm -23 base.txt head.txt   # only at base
$ wc -l base.txt head.txt
18 base.txt
18 head.txt
```

`bst` cannot stage into CAS here (`FAILURE Staging local files into CAS`
/ `Cache too full`, exit 255). CI runs these green.

No shared constant moved this round: `UNRESOLVABLE` is still 61,
`HANDFUL` 25, `CENSUS_FLOOR` 11, and no track added a test file, so
`tests/tiers.py` is untouched.
