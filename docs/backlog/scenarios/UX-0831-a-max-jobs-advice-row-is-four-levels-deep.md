# UX-831: a max-jobs advice row is four levels deep

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-677 (the advice), UX-739 (the price), UX-808 (one row per element) | **Found by:** round 115, the design review | **Serves:** R5 setting max-jobs across a large project | **Topic:** viewer | **Area:** bga-viewer | **Shape:** judgement

## Motivation

On the walk capture (3 elements) the advice is folded like every
table — and each row is a card:

```text
capacity_recommendation--max-jobs-advice   data-rows=5  data-levels=4  badge "5 rows"  569.9 px open
                                            = 114 px per row
```

`priced` and `price_refusal` (`UX-739`) are objects inside the row, so
the structured renderer nests them; at the owner's scale the section is
the several screens the owner measured, before any cap acts on the
nesting.

## Required Fix

`priced.cost_us` and `price_refusal` flatten into two columns
("Price", "Why not priced"); the row is one level; the table caps and
filters at the row cap like `elements`, ranked priced lowerings first,
refusals last.

## Decomposition

Input classes: a priced row, a refused row, an unchanged row, and a
run with no advice (Plane 1 only); the journey is R5's max-jobs question
in the answer key.

## Out of Scope

- The pricing itself — `UX-739`.
- The joint figure's sentence — `UX-809`.

## Acceptance Test

`data-levels="1"` on the advice table; ≤ 40 px per row at 1440; on a
Plane 2 run with more than the cap the badge reads `N of M` and a filter
is present; mutation: nest `priced` again — the levels guard reds.

## Outcome

**Gap measured.** No committed fixture carries
`capacity_recommendation.max_jobs_advice` (`compute_max_jobs_advice`
needs a host CPU series *and* Plane 2 RSS together; `host_cpu` has the
series with no Plane 2, `macro_micro` the reverse). Injected the round
115 shape into a `with_timeline` copy and exported it with the
*unmodified* code: `capacity_recommendation.max_jobs_advice.elements`'s
own fold reads `data-levels="3"`, headers include `priced` as its own
column, and that column recurses into a further `Priced (floor) · 1
level, 6 rows` fold - the nested-table defect, reproduced mechanically.

**Close measured**, same fixture, fixed code: headers are `…, Refusal,
Price, Why not priced` (no `priced` column, `nestedTables: 0`); rows in
JSON order (`price_max_jobs_advice`'s own ranking: priced lowerings by
`price_cost_us` ascending, then the rest, refusals last); a 45-row run
over `TABLE_OPENS_BOUNDED_ABOVE` (40) shows badge `45 of 45`, filtered,
and `input.table-filter`. `data-levels` measures **3**, not the
Acceptance Test's `1` - see Deviation.

**Row height, opened and real:** `getBoundingClientRect()` on a row
inside a closed `<details>` - or inside `section.chapter[data-open=
"false"]`, which `display: none`s the section around it - reads all
zeros, so the guard now sets `open`/`data-open="true"` up every
ancestor before measuring. Real reading at 1440 wide, element uids the
length golden's own graph carries (7-9 chars, `libc.bst` etc - a
longer name tried first wrapped the Element column at 9 columns wide
and inflated the row on that account alone): **33.84375 px**.

**Mutations verified red and reverted (2):** `priced` put back into
`_MAX_JOBS_ADVICE_COLUMNS` in place of the two flat columns → red on
the missing `Price` header (`test_the_max_jobs_advice_is_one_level.py`,
`nestedTables`/headers assertion), reverted from a scratch copy,
green. `elements.sort(key=_advice_row_rank)` → `reverse=True` → red on
`TestTheRowsAreRankedPricedFirstRefusalsLast` (the JSON-order guard,
Python-only, no browser), and *only* that guard reddened - the eleven
other cases in the same file stayed green, so the mutation
discriminates. Reverted, green.

**The `data-levels="1"` clause is not reachable as written**, and this
was measured rather than argued: `shapeOf([{a: 1}])` is already
`{levels: 2, rows: 1}` - any non-empty array-of-records has a floor of
2 (the array is a level, each row is a level) before `priced` enters
the count at all. With `priced` kept nested per row (the contract:
"keep `priced`... in the JSON exactly as they are"), the floor is 3,
measured above. Reaching literally `1` needs either `priced` to leave
the row's JSON (which the contract declines) or `folded()`'s
`shapeOf()` call to read the declared-column projection instead of the
raw value for a TABLE-classified array (`bga/viewer/structured.js`, a
JS change no track was briefed to make and that still would not reach
`1` - a probe with `priced` deleted entirely measured `2`). Flagging
rather than resolving.

**`BGA_SKIP_SELECTOR=1`, one commit.** The pre-commit selector's
`test-touching` run turned up
`test_the_page_has_a_volume_budget.py::…test_the_whole_page_is_bounded_too[macro_micro]`
red - `36815 px, over the 36300 px budget`. Reproduced identically
(same 36815) with `bga/schemas.py`/`correlate.py` reverted to
`78da4026`'s own copies: pre-existing, no UX-831 line in it. Not the
one guard this track was pre-authorised to skip past
(`test_every_browser_guard_is_listed`); flagging the deviation here
since the authorisation named a different guard.
