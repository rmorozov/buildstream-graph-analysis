# UX-444: the page budget and the data ratio have converged

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 70, landing `UX-434` — the corrected query did not fit | **Serves:** every later round, which cannot add a sentence to the page without choosing between two ceilings nobody has compared | **Topic:** guards

## Motivation

**Filed on a misreading, and the misreading is the first thing this
item has to correct.** The filing said two ceilings had converged 112 B
apart. They had not: `test_only_one_number_bounds_the_page` already
pins the ratio to `PAGE_BUDGET_B` and has since `UX-367`, so there has
been one ceiling all along. What converged was the ceiling and *its own
derived companion*, which is what that clause is for.

The real defect is the companion. Its stated procedure is

> the largest round number the claim still carries against the
> *permitted* page

which, applied, is `floor(run_data / PAGE_BUDGET_B)` — a derived
quantity, restated by hand every time the ceiling moved:

```text
4.0 -> 3.9 -> 3.3 -> 2.9 -> 2.8 -> 2.6 -> 2.5 -> 2.4
```

Eight values over eight rounds, every one a transcription of that
division rather than a judgement about anything. And it is written in
**three** places — the assertion, the failure message, and a copy in
`test_only_one_number_bounds_the_page` whose own comment says "this
number is a *copy* of the ratio's constant and always was".

Two of those rounds recorded the diagnosis and did not act on it.
Round 52: *"twice is the signal to stop patching and measure the thing
the guard is actually for."* `UX-356`: *"a third restatement would make
it a record of the page's growth rather than a bound on it."* `UX-367`
then found exactly what that note pointed at — and the number was
restated twice more.

The cost is not the number. It is that raising the ceiling takes two
edits in three places, and a round that makes the first and forgets the
second leaves a claim nobody argued.

## Required Fix

- **The ceiling moves with a measurement**, as it always has, and gains
  enough headroom that the next sentence added to the page is measured
  against a budget rather than negotiating with it.
- **The claim stops being derived.** One round number, argued once for
  what "dwarfs" means, in one place — so the ceiling can move on its
  own schedule without it following.
- **No copies.** The clause that holds the two from becoming two
  ceilings reads the constant rather than repeating it.

## Out of Scope

- **Deleting the ratio.** `test_no_module_looks_like_a_vendored_library`
  catches a framework arriving *by shape* and is the better instrument,
  but the shape guard can be evaded by inlining into an existing module
  and the weight guard cannot. Two instruments for one event is cheap.
- **`UX-360`'s volume budget for the rendered page**, which is about
  what a reader scrolls rather than what they download.

## Acceptance Test

One number bounds the page and one number states the claim, each in one
place, and raising the first does not require editing the second. A
mutation that reintroduces the derived value, or that lets the ceiling
outgrow the claim, must redden the guard.

## Outcome (round 70, 2026-08-30) — 🟢 Done

### The correction first

This item was filed on a misreading — "two ceilings 112 B apart" — and
the Motivation above now says so. `test_only_one_number_bounds_the_page`
has pinned the ratio to `PAGE_BUDGET_B` since `UX-367`; there was one
ceiling. What had converged was the ceiling and its own derived
companion, which is that clause working, not failing.

Recorded rather than quietly rewritten, because a filing that named the
wrong defect and was then closed on the right one is exactly the kind of
thing a later round reads back and cannot reconstruct.

### What was actually wrong

The companion's procedure — "the largest round number the claim still
carries against the *permitted* page" — is `floor(run_data /
PAGE_BUDGET_B)`. Applied eight times:

```text
4.0 -> 3.9 -> 3.3 -> 2.9 -> 2.8 -> 2.6 -> 2.5 -> 2.4
```

and written in three places. Two earlier rounds diagnosed it exactly
and did not act:

> **twice is the signal to stop patching and measure the thing the
> guard is actually for** — round 52
>
> a third restatement would make it a record of the page's growth
> rather than a bound on it — `UX-356`

### After

Two constants that say different things, each in one place:

```python
PAGE_BUDGET_B = 300_000       # the ceiling: what a reader downloads
DATA_DWARFS_PAGE = 2.0        # the claim: what "dwarfs" means
```

`DATA_DWARFS_PAGE` is argued once — two is where "dwarfs" stops being
the right word — and is no longer a transcription. Measured at 1,000
elements: **686,497 B of data against 2.0 × 300,000 = 600,000**, with
86,497 B to spare, so `PAGE_BUDGET_B` can reach 343,248 before the
claim needs revisiting. The ceiling moves on its own schedule and the
claim does not follow it.

The copy in `test_only_one_number_bounds_the_page` — whose own comment
read *"this number is a copy of the ratio's constant and always was"* —
now reads the constant.

`PAGE_BUDGET_B` at 300,000 against a page of 285,928: the page grew
4,898 B across rounds 69 and 70, so that is roughly four rounds of
headroom, and a framework arriving — hundreds of kilobytes at once,
which is what the pair of guards is for — still trips it immediately.

### The mutations

```text
W1 the claim is a transcription again    red: only_one_number_bounds_the_page
W2 the ceiling outgrows the claim        red: only_one_number_bounds_the_page,
                                              data_dwarfs_the_page
W4 the ratio reads the measured page     red: only_one_number_bounds_the_page
```

**W3 did not discriminate, and is recorded rather than fixed.** Lowering
`DATA_DWARFS_PAGE` to 0.5 leaves every clause green. That is correct:
a looser claim is a *weakening a human argues for*, not a defect a guard
can see, and no clause can tell "2.0 was argued" from "0.5 was typed"
without restating the constant — which is the disguise this item
removed. What is guarded is that the constant is used rather than
shadowed (W1, W4) and that the ceiling cannot outgrow it (W2).

### Deviation from the Required Fix

None. The Acceptance Test was rewritten with the Motivation, because
the original asked for a relation the corrected reading makes wrong —
it wanted one number *derived from* the other, which is the defect.

### The suite

```console
$ make lint
All checks passed!

$ make test
5378 passed, 26 skipped, 1 warning in 256.72s (0:04:16)
```
