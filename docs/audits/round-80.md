# Round 80 — the round-79 slate, in six parallel tracks

Input: the sixteen rows round 79 filed (`UX-514`, `UX-516`..`UX-539`,
less the four it closed), plus `UX-92`'s reopened clause and
`UX-500`'s second regime. Twenty-four rows closed. This document is
the `UX-500` measurement; the items' own records are their task files.

## The regime this round ran — Regime B

`UX-500` names two. Round 75 ran **A** — fixing guide §3 as written,
the whole suite before any item is marked done. Round 80 ran **B**:
per item `make test-touching` plus the item's own mutations, and
`make test` once per merge batch.

Six `implementer` tracks in worktrees, then two merges into this
branch, then one gate over the merged tree.

| | round 75 (A) | round 80 (B) |
|---|---|---|
| items closed | 7 | **24** |
| suite runs | 15 | **6** |
| gate wall clock | ~80 min | **~63 min** |
| commits per task | 1.0 | **1.83** (44 / 24; 1.46 excluding 9 merges) |
| defects the batch gate caught | 5 | **9** |
| **of those, ones `test-touching` would not have run** | **2 of 5** | **4 of 9** |

Regime A for 24 items implies **at least 24** suite runs — about 3.5
hours of gate at this round's 527 s — against B's six.

## The number that decides

`UX-500`: *"If B's missed-defect count is zero across three rounds, §3
changes to name the batch as the unit the suite gates. If not, the
number is the reason §3 stays."*

Measured, not argued — `dev_touching.select` over each responsible
commit's own diff, asking whether the guard that caught the defect is
in the set that selector would have chosen:

```text
commit    item    the guard that caught it                      sel?  set
7176c3a   UX-520  test_the_contract_inventory_is_derived.py     NO    129
7176c3a   UX-520  test_every_emitted_contract_is_answerable.py  yes   129
7176c3a   UX-520  test_docs_links_and_commands.py               yes   129
7176c3a   UX-520  tests/test_golden.py                          NO    129
7176c3a   UX-520  test_the_verification_log_is_true.py          yes   129
be4e3e0   UX-537  test_the_dom_shim_is_one_instrument.py        yes    78
f41f121   UX-536  test_the_journey_has_an_answer_key.py         NO     57
a6cf3b5   UX-528  test_the_tiers_are_a_partition.py             NO    143
2d15b0a   UX-523  test_one_page_behind_the_button.py            yes   417
```

**Four of nine.** Non-zero, so the condition `UX-500` set can no
longer be met by running a third round: B does not reach zero, and §3
stays. The count is 2 of 5 and 4 of 9 over the two rounds — 6 of 14,
and it did not fall when the batch got three times larger.

**What the four have in common** is worth more than the count. None of
them is in the changed module's neighbourhood at all:

- `test_the_contract_inventory_is_derived.py` and `tests/test_golden.py`
  broke because `bundle-manifest/v1` joined `producer.contracts`, which
  every committed analysis carries. A new contract changes documents in
  fixtures no file in the diff names.
- `test_the_journey_has_an_answer_key.py` broke because `UX-536`'s
  better empty-section wording no longer contains the phrase a guard in
  another file tests for. A word, in a page, read by a guard that names
  neither the module nor the item.
- `test_the_tiers_are_a_partition.py` broke because `UX-528`'s change
  made its own file slower. The selector maps a diff to guards that
  *name* what it touched; a file's own duration is not in the diff.

The selector answers "which guards name this file". Three of these four
are guards that read a *consequence* of the change, which no grep over
the diff can find. That is a statement about what `make test-touching`
is, not a defect in it.

## What the two regimes do not separate

Under either regime, a defect that only CI can produce is found by CI
and by nothing here. This round had none of that shape — the six suite
runs and the tracks' own gates found everything except the two spine
timing clauses, which are contention and passed alone (28.73 s, two
passed, single-process).

What B *did* produce that A cannot is a class of defect A never sees:
**three cross-track collisions**, each invisible to every track and to
every per-item suite run inside a worktree.

| collision | shape |
|---|---|
| `tables.js` | two tracks each added a row selector; each broke the other's claim. Resolved into one family (`ownRows`/`everyRow`/`columnCells`) with a fixture neither track had |
| `UX-523`'s settle | green in its own whole-suite run; red three merges later, because the condition was keyed on the page that was not the one under load |
| `docs/README.md` | two tracks each half-updated the contract count, leaving "Twenty-two ids over 23 rows" |

None is a reason to prefer A: A does not run tracks in parallel, so it
does not have these to find. It is a reason the batch gate is not
optional under B, which is what §3 already says.

## Two tracks falsified their own item's premise

Both by measuring rather than by implementing:

- `UX-535` filed "the producer stamp is published twice". The two
  stamps are different facts — the build that *analysed* and the build
  that *captured* — and `UX-250`'s refusal reads the capture one.
  Neither copy went; the graph-shape half was real and moved `analyze`
  to v5.
- `UX-530` filed "the spine counts every process twice, so the track
  ceiling is spent on records". `UX-406`'s `merge_record_streams`
  already fixed it; the track kept the claim as a guard
  (`test_the_second_record_does_not_halve_the_room`) instead of a fix.

## What a track cost

`tools/dev_track_cost.py` (`UX-525`, built this round), on the six
transcripts:

```text
track                    wall   responses     tokens   read  edit  test  other
UX-526/527/528          8732s        278   1,256,699  13.2  55.4  26.5    0.3
UX-520                  7423s        157     942,191  26.9  22.6  12.5   36.1
UX-535                  6329s        158   1,117,704   6.4  66.6  10.4   14.1
Track G                 6198s        190   1,155,807* 10.5  54.7  12.2   20.4
UX-538                  5397s        174     673,692  11.8   8.0  74.7    0.2
UX-539                  4623s        146     545,739  11.8  10.4   1.2   73.5
```

\* the printed total for that track; the phase columns are its own.

The `test` share is the round's spread, not a constant: 1.2% on a track
whose work was a profile, 74.7% on one whose whole item was a ranking
guard under contention. Round 75's 10-16% was three tracks of one
shape.

## Nine rows filed

`UX-540`..`UX-547` and the two skip-reason holes, every one from a
measurement a track took rather than from a review: three contracts in
no registry, the gap sweep still quadratic as a contract, diagnostics
now the largest phase, a second ranking clause under contention, a hole
in the node census, a refused timeline that says the wrong thing, a
fetch guard flaky under load, a fixture differ blind to key order.
