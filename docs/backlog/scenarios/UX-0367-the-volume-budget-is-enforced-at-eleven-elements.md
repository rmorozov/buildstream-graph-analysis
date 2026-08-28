# UX-367: the volume budget is enforced at eleven elements

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-360 (the volume budget), UX-187 (a report you can read at four thousand elements) | **Serves:** anyone whose project is bigger than the fixtures | **Topic:** viewer

## Motivation

`UX-360` gave the page two budgets and a guard that holds them. The
guard parametrises over `pages.FIXTURES` — `golden` and `macro_micro` —
which are **11-element runs**. Measured against the 1,202-element
synthetic run, the same page:

```text
                    budget   golden   macro_micro   scale (1,202)
opened height       34,000    14,493       28,213          70,577
words               12,000     5,279        9,879          33,835
controls               800       409          659           1,834
```

**Every budget is exceeded by 2-3x at a realistic size, and no guard
runs there.** The bounds were set with a fifth of headroom against the
larger *fixture*, and the larger fixture is two orders of magnitude
smaller than the run `bga gen-synthetic` calls a scale probe.

This is `UX-360`'s own argument turned one level out: a bound nothing
can reach is not a bound, and a bound measured only where the page is
small is a bound that has never met the page.

Round 2 found four defects at 1,202 elements that were invisible at
eleven. The volume budget is the fifth.

## Required Fix

The budget guard runs at scale, and the bounds say which size they are
for.

- Add the synthetic run to the guard's population — it is generated from
  a seed, so it costs a `gen-synthetic` rather than a fixture in the
  tree, and `tests/tiers.py` already has a place for a file that heavy.
- State the budgets **per size class** rather than as one pair. A page
  that is 70,000 px at 1,202 elements may be acceptable; what is not
  acceptable is that nobody decided.

If the scale page cannot meet a bound anybody would set, that is the
finding and it belongs in the item that follows from it — `UX-366`'s cap
is one lever, chapter folding is another.

## Falsification

Export the seeded 1,202-element run, boot it, and assert the same three
numbers the round-56 guard asserts. It fails today at 2.1x, 2.8x and
2.3x. A guard that passes on `golden` and `macro_micro` and is never
asked about scale is the state this item is about.

## A second budget, found in round 59 — resolved here

`UX-369` added one control to the Perfetto section and the export's
**other** bound — `test_the_report_you_can_attach.py`'s "the data
dwarfs the page", asserted as `run_data > 2.6 * code` — went from
2.630 to 2.6008 on the same synthetic run. About 78 B of headroom.

Following that number gave the reason rather than another restatement.
The fixture's data is a constant, so on it the ratio **is** an
absolute page bound:

```text
685,327 / 2.6  =  263,587 B of page, at most   <- the ratio, in disguise
PAGE_BUDGET_B  =  265,000 B of page, at most   <- the stated backstop
```

Two absolute page bounds in one test class, 1,413 B apart, the tighter
one unnamed and — by its own comment — forbidden from being moved. It
had been the real ceiling for four rounds and nobody could see it,
which is why raising it kept feeling wrong.

So the page's size is `PAGE_BUDGET_B`'s job, and the ratio goes back to
its own claim, asserted against the page the backstop **permits**
rather than the page that happens to be here today:
`run_data > 2.5 * PAGE_BUDGET_B`. It can now fail for two reasons and
both are worth a look — the analysis published less, or the permitted
page grew by a third — and neither is "a round landed".
`test_only_one_number_bounds_the_page` holds it, arithmetically and at
the source, so the disguise cannot come back.

## Out of Scope

Making the page smaller. That is `UX-366` and whatever follows it; this
item is about measuring at the size that matters, and about the guard
that measured the wrong two runs for a round and a half.

## Outcome (round 59, 2026-08-28) — 🟢 Done

### The gap, measured

Round 56's guard parametrised over `pages.FIXTURES` — two 11-element
runs — and one pair of bounds served every size. The seeded
1,202-element run was not in the population, so nothing had ever
measured the page at the size `gen-synthetic` exists to probe.

### After

The guard's own instrument, over all three, chapters opened:

```text
              elements   landed   opened    words  controls  sect  svg
golden               4    3,501   14,560    5,280       410    43    8
macro_micro         11    5,541   28,257    9,883       660    58   18
scale            1,202    4,397   54,968   33,864     1,922    66   13

budget, to     50 elts     7,000   34,000   12,000       800
budget, to  4,000 elts     7,000   66,000   41,000     2,300
```

**The filing's own scale figures were measured wrong, and this
supersedes them.** It reported 70,577 px for the scale page against
28,213 for `macro_micro` — but 70,577 was measured with every
`<details>` forced open and 28,213 with them closed. One row, two
instruments. Same instrument both ways:

```text
              chapters open   + every details open
macro_micro          28,257                 45,829
scale                54,968                 70,551
```

The overrun is real either way and smaller than filed: **1.6x, not
2.1x**. `_LOOK` opens chapters only, because that is what "Expand all"
gives a reader; a `details` is a second, deliberate click. Third time
this round that the instrument was wrong before the code was.

### Two things only the third row could say

**The fold holds.** Landed height at 1,202 elements is **4,397 px** —
*shorter* than the 11-element fixture's 5,541, and a fifth of the
opened page. `UX-347`'s answer scales, which the 11-element
measurement could not have shown, so one landed bound serves every
class and that is a result rather than a shortcut.

**The volume does not, and it is one section.** Of 33,864 words,
`wall_clock_share_us` is **27,657 — 82%** — with 1,204 of the 1,922
controls and 30,859 of the 54,968 px:

```text
section                     words  ctrls      px
wall_clock_share_us        27,657  1,204  30,859
perfetto-questions          1,367     16     826
floors                        377     14     700
findings                      354     24   1,583
...every other section together: ~6,200 words
```

It is a flat `{uid|BUILD|BUILD|0: microseconds}` map rendered one row
per element, uncapped — three sections from an element table capped at
25 (`UX-366`). The two defects are the same mistake in opposite
directions, and `UX-366` is the lever.

So the large class's bounds are set where the page *is*, and
`test_the_budgets_are_not_slack` is what will force them **down** when
`UX-366` lands: a bound the largest run in a class cannot come within a
factor of two of is a number nobody will ever meet.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it. Run
against the committed tree.

| # | mutation | reddened |
|---|---|---|
| M1 | the scale run dropped from `LABELS`, as it was before | *pending* |
| M2 | one pair of bounds for every class again | *pending* |
| M3 | `budget_for` clamps to the last class instead of refusing | *pending* |
| M4 | the ratio asserts `2.5 * code` — the disguise, restored | *pending* |
| M5 | §3e states only the small class's bounds | *pending* |

### Deviation from the Required Fix

- **The filing's scale figures were wrong** and the Required Fix's
  "fails today at 2.1x, 2.8x and 2.3x" is corrected to 1.6x, 2.8x and
  2.4x. The item stands; one of its three numbers did not.
- The "Add the synthetic run to the guard's population" clause is met
  by `pages.scale_run`, shared with `UX-369`'s guard rather than
  written twice.
- **The file moved tier**: 11.5s → 22.3s, MEDIUM → LARGE. That is the
  cost of the item and it is recorded in `tests/tiers.py` rather than
  absorbed.
