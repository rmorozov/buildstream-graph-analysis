# UX-289: one element table, many presets

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-288 | **Serves:** R1 and R7 | **Topic:** viewer

## Motivation

Filed from Direction 14, and the half of it the reader sees.

Measured on the 1,202-element synthetic run: **19 tables name elements
and they draw 13 distinct populations**, every one of them a subset of
the single 1,202-row element table `UX-268` built. Seven pairs overlap
100%:

```text
   100%      14  signals/critical_path   [2 cols]  <-> critical_path_detail [5 cols]
   100%     135  signals/leaf_analysis   [8 cols]  <-> structural/deferrability [6 cols]
   100%     135  signals/value           [2 cols]  <-> signals/value [4 cols]
```

Each is the same elements with a different column set — which is the
definition of a **view**, and the page has no way to say so. It has
bounds (`UX-262`'s `Top N`) and filters (`UX-205`), and **zero named
presets**: measured, no element on the page carries a preset role.

The cost is not only repetition. It is that the widest table carries
**13 columns** because one table has to serve every question, while a
reader asking one question wants four.

## Required Fix

1. One element table. A **preset** is a named `(filter, columns, sort,
   bound)` over it — "Critical path", "Leaves", "Latent heavies",
   "Choke points" — selectable, and named in the rail.
2. A preset is declared in the **schema's view-hints**, not in the page.
   `UX-201` established that sections, columns and units come from the
   published schema; a preset is the same kind of declaration and must
   not become the one thing the page decides for itself.
3. The current URL state (`UX-211`) carries the preset, so a link opens
   the view it names.
4. Every preset's population is a filter over published fields — which
   is what `UX-288` makes possible and why it comes first.

## Out of Scope

- Removing the element detail blocks. They answer a different question
  (one element, everything about it) and `UX-278` is about reaching
  them.
- Deriving a preset the payload cannot express. Direction 7's boundary
  holds: if a view needs a number the payload does not carry, the
  payload gains it (`UX-288`) rather than the page computing it.
- Doing this before `UX-288`. Deduplicating the page while the contract
  still publishes three copies makes the page and the payload disagree.

## Acceptance Test

On the 1,202-element run, no two tables carry identical element sets.
The critical path, the leaves and the choke points are presets over one
table, each reachable from the rail and from a link, and no table shows
more than eight columns by default.

## Outcome

🟢 Done (round 38). The element table is drawn as the view a reader
asked for, and the views are declared in the schema.

**Where the page stood before this, and after.** The sweep counts every
table that names elements, attributing each cell to its *nearest*
table — the first draft let an outer table absorb its nested table's
rows and reported three 100%-overlap pairs that do not exist, which is
the same double count `UX-277` had to fix in its own guard.

```text
1,202-element synthetic run    filed (v1)   after UX-288   after this
  tables naming elements               19             11           11
  distinct populations                 13             11           11
  pairs at 100% overlap                 7              0            0
  widest table, columns                13             13            6
  tables over eight columns             -              1            0
  named presets                         0              0            5
```

`UX-288` did the population half; this does the width half and the
naming. The union is still one of the views (`All elements`), so
nothing became unreachable — it stopped being the only thing on offer.

**The five views, on the committed 11-element run:**

```text
view             cols  rows   first rows
All elements        6    11   core.bst, codegen.bst, lib-b.bst, lib-d.bst
Critical path       5    10   toolchain.bst, core.bst, lib-a.bst, lib-b.bst
Leaves              5     1   all.bst
Choke points        5     9   toolchain.bst, lib-a.bst, lib-b.bst, lib-c.bst
Latent heavies      5     1   codegen.bst
```

Every membership was checked against the payload rather than eyeballed:
`Critical path` and `Choke points` match `critical_path_detail` and
`bottleneck.choke_points` **including order**, and `Leaves` matches
`leaves_detail`'s keys.

**Every population is a filter over a published field**, which is
Required Fix item 4 and why `UX-288` came first. Two forms, both
declared:

- `from` — a dotted path to a selection the payload publishes once. The
  rows are that selection *in the order it is published*, which is how
  the critical path is drawn in path order without the page knowing
  what a critical path is.
- `where` — `{column, equals}` over a column the element records already
  carry (`is_leaf`, `observed_critical`).

The two are alternatives and the schema validator refuses a preset that
says both: two ways of choosing rows are two answers to one question,
which is the defect `UX-288` had just finished removing from the
payload.

**A view this run cannot support is not offered.** "There are no choke
points" and "this run does not carry choke points" are different claims,
and a view drawn empty makes them look alike. The same rule applies to a
pasted link: a fragment naming a view this run lacks is ignored rather
than landing the reader somewhere else under the name they asked for.

**Two defects found while measuring, both fixed here:**

1. **The shim disagreed with a browser.** `tests/dom_shim.mjs` reflected
   attribute → property and not the reverse, so a node built by setting
   `.value` or `.href` read `null` from `getAttribute` in the harness
   and the real thing in a browser. Two reads in this item were written
   against the browser and found nothing. Measured in the Chromium this
   repository drives and pinned in the shim's own agreement test:

   ```text
   option.value = "Critical path"  ->  getAttribute("value")  "Critical path"
   a.href       = "#element-x"     ->  getAttribute("href")   "#element-x"
   div.id       = "an-id"          ->  getAttribute("id")     "an-id"
   input.value  = "typed"          ->  getAttribute("value")  null
   ```

   `<input>` is the exception and not an accident — its `value` is the
   *current* value, which is why a form reset restores the attribute —
   so a shim that reflected it too would be wrong in the other
   direction.

2. **The last table over eight columns was a duplication one level
   down.** `structural.serialization_point_risks[]` published `elements`
   (a list), `element_max_jobs` and `element_duration_us` (two maps
   keyed by it) — the same membership three ways, at *one* element per
   risk, which is exactly why `UX-288`'s two-element floor did not see
   it. It is one list of records now (`pinned_elements`, named to avoid
   a fourteenth view-state key collision — see below), and the table it
   draws went from 9 columns to 7.

**Filed, not fixed here:** the page keys a table's view state by its
payload field name (`UX-211`), and `renderStructured` names every nested
table `value` — so **thirteen tables answer to `f.value`** on both runs.
A filter typed into one is captured once and applied to whichever the
loop reaches first ([`UX-292`](UX-0292-thirteen-tables-share-one-view-state-key.md)).
Not a regression: `UX-277` made these tables, and before it they were
stringified cells that carried no state to collide.

**One exemption in the guard, measured rather than assumed.** Two nested
`structural` tables draw the same five elements on the committed
fixture — `sensitivity.top_opportunities` and
`batch_opportunities.serialized_pairs`:

```text
mm     top_opportunities   5  serialized_pairs   5  identical: True   shared: 5
scale  top_opportunities   5  serialized_pairs   5  identical: False  shared: 3
```

A coincidence at eleven elements and not at 1,202 is a coincidence. It
is named as an exact expectation rather than filtered out by a rule, so
a real duplication changes the list and reddens the guard — and a second
test asserts the two fields are still two different values.

**Falsification, and the two guard defects it found.** Eight mutations,
each asserted to land before the suite was trusted:

```text
M1 a view ignores its declared columns        -> 1 failed  (width)
M2 a `from` view re-sorts the payload's order -> 1 failed  (published order)
M3 an unsupported view is offered empty       -> 0 failed  <- non-discriminating
M4 the fragment stops carrying the view       -> 1 failed
M5 the rail stops naming the views            -> 1 failed
M6 the page names a view of its own           -> 1 failed
M7 the serialization table triples again      -> 1 failed  (width)
M8 PRESET_COLUMNS_MAX = 40                    -> 0 failed  <- non-discriminating
```

Both were fixed rather than counted.

**M3** passed because an absent *selection* is refused where the path is
resolved, so a run with no choke points never reaches the "no rows"
check — the `where` half of the rule had no case. A run whose leaves are
all cleared now covers it.

**M8** passed because every column test measured against the constant it
was checking: `len(columns) <= schemas.PRESET_COLUMNS_MAX` is true for
any bound, and the refusal case built `PRESET_COLUMNS_MAX + 1` columns
so it kept raising however far the constant moved. The bound is stated
in the guard as a literal now, with a second test pinning the module to
it — the same fix `UX-277`'s nesting guard needed one round back, and
the same defect.

Tests: 20 new (`tests/unit/test_one_table_many_views.py`), 4 new pinned
behaviours in the shim's agreement test. Every guard runs on
`tests/fixtures/macro_micro/run`, which is committed — `UX-276`'s rule,
applied from the start.
