# UX-351: the label prints the unit the value already carries

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-341 (one unit per dimension) | **Serves:** anyone reading a field name on the page | **Topic:** viewer

## Motivation

`title(key)` turns a payload key into a label by replacing underscores
with spaces. Since `UX-341` every key that holds a duration ends `_us`
and every key that holds memory ends `_bytes`, so the reader now meets
this:

```text
Execution on chain us    43.2 s   Time the chain's own elements spent...
Dependency wait us        0 ms    Time a chain element spent ready but...
Untracked head us         2.7 s   Wall-clock before the first tracked...
Idle us                   0 ms    Time with nothing running at all.
Category us               2.7 s   Wall-clock in the attribution category...
```

"Execution on chain us" is not English, and the `us` is answering a
question the value has already answered in the same line: the number
beside it reads `43.2 s`. The suffix exists so the *contract* says what
the number is; the label is for the reader, and the renderer has
already used the declaration to format the value.

This got worse rather than better with `UX-341`: before it, some of
these keys ended `_s` or carried no suffix at all, and the ones that
did were fewer. Unifying the payload's units is right; letting the
payload's spelling reach the reader's eye is the cost that came with
it, and it is one function.

## Required Fix

`title()` drops a trailing unit token when the key's declared quantity
already accounts for it — `_us` on a `duration_us`, `_bytes` on a
`bytes`, `_share` on a `share`. Derived from the declaration rather
than from a list of suffixes, so a key whose name ends `_us` and is
*not* a duration keeps its suffix and looks as odd as it is.

## Out of Scope

- Renaming the payload keys. The suffix is `UX-341`'s rule and the
  contract is where it belongs.
- Prettier labels in general (`Cpu` → `CPU`, and the rest). A separate
  and larger question about a label table.

## Acceptance Test

On both committed fixtures, no rendered label ends in a unit token that
its column's or term's declared quantity already carries, asserted by
walking every rendered term against the schema. `Execution on chain us`
reads `Execution on chain`, and its value still reads `43.2 s`.

## Outcome (round 53, 2026-08-28) — 🟢 Done

### The gap, measured

Every rendered `<dt>` and column header on the exported report, against
what the payload declares that key to be — the walk the acceptance
asks for, run with `title()` ignoring the declaration:

```text
golden       41 label(s) print a unit their declared quantity already carries:
             [('Build suffix us', 'build_suffix_us', 'duration_us'),
              ('Capacity cpu us', 'capacity_cpu_us', 'duration_us'),
              ('Category us', 'category_us', 'duration_us'),
              ('Certified headroom us', 'certified_headroom_us', 'duration_us'),
              ('Chain bound share', 'chain_bound_share', 'share'),
              ('Chain share', 'chain_share', 'share'),
              ('Critical path share', 'critical_path_share', 'share'),
              ('Critical path us', 'critical_path_us', 'duration_us')]
macro_micro  52 label(s), the same shape
```

Larger than the twelve and sixteen the motivation counted, because
that count came from reading the page and this one asks the schema.

### After

Zero on both fixtures, and the values are untouched: `Execution on
chain  43.2 s`.

### The rule is the declaration

`title(key, kind)` takes the quantity the value is being rendered
under — `quantityFor`'s answer, so declared still beats guessed — and
drops the trailing token that quantity accounts for. `UNIT_SUFFIX` is
keyed by the *quantity*, not by the suffix, which is the property the
item is about: `retries_us` declared a `count` keeps its `us`, because
there the suffix is the surprising and true half of the label.

Only the quantities whose *rendered value* spells its unit are in the
table. A `count` renders as `1204` and a `ratio` as `1.50x`, so
"Process count" and "Inefficiency ratio" are telling a reader
something the number beside them does not — asserted, because tidying
those two into the table is the most likely way a later round undoes
this.

Every call site that already resolved a quantity passes it: column
specs, the inline object, a map table's value column, the element-join
columns, the distribution strip, and `describedTerm`, which is where
all three pairs lists build their terms. `chapters.js` had its own
`.replace(/_us$/, "")` for the attribution sentence and calls the
shared rule instead.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `681272d`.

| # | mutation | reddened |
|---|---|---|
| N1 | `title` ignores the quantity — the defect itself | 3 clauses: *"golden: 41 label(s) print a unit their declared quantity already carries"*, 52 on `macro_micro`, and the unit-level trim |
| N2 | trim by a suffix list, whatever the quantity | 2: `test_a_key_that_only_looks_like_a_duration_keeps_its_suffix`, `test_a_key_with_no_quantity_is_untouched` |
| N3 | the guard against a key trimmed to nothing removed | `test_a_key_the_trim_would_empty_keeps_its_label` |
| N4 | `count` and `ratio` added to the trim table | `test_a_count_and_a_ratio_keep_their_word` — *"['Process', …, 'Inefficiency'] == ['Process count', …, 'Inefficiency ratio']"* |
| N5 | the label renders empty rather than trimmed | `test_the_labels_are_still_labels`: *"golden: 178 label(s) render empty"*, 228 on `macro_micro` |
| N6 | `describedTerm` stops taking the quantity — the pairs lists regress while the tables stay right | both fixtures' acceptance clause |

N3 and N4 each began as a non-discriminating mutation and are recorded
because the fix was to the *guard*: N3's first form used the keys `us`
and `bytes`, which no suffix pattern matches, so it proved nothing
until the case became `_us`; N4 passed until the count/ratio clause
existed at all.

### Deviation from the Required Fix

- Eight labels per fixture still end in `us`: the `attribution_hints`
  terms (`Idle us`, `Retry wait us`, …). They are outside the property
  and the guard skips them by measurement, not by name — the clause
  reads the term's *value*, and these hold a sentence rather than a
  number, so nothing beside the label spells the unit for it to
  repeat. The keys name the metric each sentence explains and the
  block declares no quantity of its own, so there is no declaration to
  derive a trim from. Making those two sections agree is `UX-317`
  work about where the sentences live, not about `title()`.
