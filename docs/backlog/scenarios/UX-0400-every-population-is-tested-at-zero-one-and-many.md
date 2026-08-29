# UX-400: every population is tested at zero, one and many

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-388 (what zero does today), UX-367 (what many did until the sweep held it) | **Serves:** every future section, before its bug is filed | **Topic:** guards

## Motivation

The escape ledger for population-shape bugs is now three entries
long, and each was found by an audit round rather than the suite:

- **zero**: six sections vanish without a word on an incremental run
  (`UX-388`, found only because round 63 ran the cycle twice);
- **one**: superlatives and labels written for populations read wrong
  over a single row (`UX-365`'s class);
- **many**: the volume budget was unheld at the size people build at
  until the capacity sweep found it (`UX-367`).

Each class was fixed *where it was seen*. Nothing asserts the next
section handles all three, so the next section ships the same three
bugs — the suite tests sections on the populations their fixtures
happen to have.

## Required Fix

A parametrized sweep in the browser tier: for every section the
chapters registry knows, render the page against a payload where that
section's population is (a) empty, (b) one row, (c) the capacity
sweep's large size, and assert the section's contract at each point —
present-and-saying-empty at zero (`UX-388`'s rule once it lands), no
plural/superlative lies at one, within the volume budget at many.
`tests/degenerate_store.py` already builds degenerate payloads; this
sweep drives it per-section instead of per-filing.

## Out of Scope

- Fixing what the sweep finds on its first run — each real failure is
  its own filing; this task builds the instrument.
- Plane 2 capture-side populations — `UX-375` bounded the unbounded
  one; this sweep is about what the page does with what arrives.

## Acceptance Test

- The sweep runs in the browser tier and enumerates every registered
  section (guard: the enumeration count equals the chapters
  registry's count, so a new section cannot dodge it).
- Falsification: revert `UX-388`'s fix (once landed) — the zero leg
  must go RED; cap one budget clause — the many leg must go RED.

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, measured

Every guard in the suite reads a population at the one size its
fixture happens to have. `macro_micro` publishes 11 record
populations; the largest has 18 rows and six have fewer than five, so
no guard in the repository had ever rendered a section at zero rows,
at one row, or above `TABLE_OPENS_BOUNDED_ABOVE` — the three sizes the
escape ledger is made of:

```text
$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/macro_micro/run \
    --format json | python3 -c "import json,sys;d=json.load(sys.stdin);
print([(k,len(v)) for k,v in d.items() if isinstance(v,list) and v
       and all(isinstance(r,dict) for r in v)])"
[('findings', 11), ('readers', 4), ('next_steps', 5),
 ('critical_path_detail', 6), ('optimization_horizon', 3),
 ('latent_heavies', 4), ('serialization_point_risks', 1),
 ('element_join', 11), ('restructuring', 18), ('binary_cost', 4),
 ('provenance', 7)]
```

### After

The sweep renders all ten swept populations at 0, 1 and 120 rows
(`TABLE_OPENS_BOUNDED_ABOVE * 3`) and asserts the contract at each:

```text
$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_every_population_at_zero_one_and_many.py -q
.............
13 passed in 1.36s
```

### What the first run found, and what was filed

`UX-400`'s Out of Scope says a real failure it turns up is its own
filing. Three were, and each is carried in the file as a **declared
ledger** — population, leg, filed id — with the clause asserting
`measured == ledger` in both directions, so a new offender reddens
because it is absent from the ledger and a fixed one reddens because
it is still in it.

- **`UX-412`** — `badgeText(1, 1)` returns `1 rows`. Nine populations,
  twelve badges, one helper.
- **`UX-413`** — the volume bound is applied by setting the Top-N
  preset, and a table with no numeric column has no preset, so
  `readers`, `next_steps`, `restructuring` and `provenance` draw all
  120 rows and `findings` draws 120 cards. `UX-367`'s budget turns out
  to have been enforced only where something was rankable.
- **`UX-414`** — `restructuring` and `binary_cost` resolve to the
  fallback chapter. `chapters.js` says that chapter "is not a hiding
  place" and names `test_the_report_has_chapters` as what keeps it
  empty; that guard exports a **single-plane** fixture, and neither
  section exists on a single-plane run.

The **zero** leg was clean on its first run — which is the answer
`UX-388`'s fix could not otherwise get, because it says the rule holds
for every population rather than for the six that vanished.

### Four measurements this file got wrong before it got them right

Each would have been filed as a defect in the page. Recorded because
the fixing guide asks for guards of one's own that did not
discriminate, and these are the sweep's own failure modes:

- it swept `element_join`, which `DRAWN_ELSEWHERE` merges into the
  element table on purpose (`UX-338`), and read the deliberate `null`
  as a section that had vanished — "6 sections vanish at zero";
- it counted `<tr>` elements, and both `foldTheMiddle` and the Top-N
  preset *hide* rows rather than removing them, so a table bounded to
  25 of 120 read as 121 rows drawn — "9 populations draw every row at
  120", of which only 4 were real;
- it scanned the whole section for comparative words and matched
  `Top 25 by duration_us` inside an `<option>` — a control offering a
  ranking, not a claim that one was made;
- it matched `Biggest wait category` inside a finding's own headline,
  which is the payload's sentence about a measurement rather than the
  renderer's sentence about a population.

The two survivors of that pass — the plural badge and the unbounded
table — are `UX-412` and `UX-413`.

### Mutations verified red and reverted (5)

Counts are what the run printed. Each was applied to the committed
tree and reverted with `git checkout` after the run.

| # | mutation | reddened |
|---|---|---|
| A1 | `renderSection` returns `null` for an empty declared collection - `UX-388`'s fix, reverted | all three `TestZero` clauses; 3 failed, 10 passed |
| A2 | `TABLE_OPENS_BOUNDED_ABOVE` 40 → 200 | `test_the_threshold_is_the_one_this_sweep_was_sized_for`, `test_a_long_population_opens_bounded`, `test_a_bounded_table_says_what_it_is_bounding`; 3 failed, 11 passed |
| A3 | `badgeText` pluralised properly - i.e. `UX-412` **fixed** | `test_no_badge_pluralises_a_single_row`, `dict_keys([]) == dict_keys([...9 populations])`; 1 failed, 13 passed |
| A4 | `restructuring` filed under the `change` chapter - i.e. `UX-414` half fixed | `test_every_swept_population_is_filed_under_a_chapter`, `dict_keys(['binary_cost']) == dict_keys(['restructuring', 'binary_cost'])`; 1 failed, 13 passed |
| A5 | `element_join`'s entry deleted from `DRAWN_ELSEWHERE`, so an eleventh population arrives unswept and unledgered | `test_no_badge_pluralises_a_single_row`; 1 failed, 13 passed |

A3 and A4 are the ledger's second direction, and the reason it is
written as equality: a *fix* reddens the clause, so the ledger cannot
outlive what it records. A5 is the acceptance test's "a new section
cannot dodge it", driven by the only mechanism that can add one.

### A guard of my own that did not discriminate

A2 was run twice. The first time it passed, 13 green, because `MANY`
was `TABLE_OPENS_BOUNDED_ABOVE * 3` read from source: raising the
viewer's threshold raised the sweep's population with it, every table
stayed bounded, and the mutation moved the expectation instead of
breaking it. `UX-392` hit the same shape this round and answered it
the same way - `BOUND_AS_MEASURED = 40` beside the value read from
source, with a clause asserting they agree. That clause is what makes
the second copy safe, and it is what A2 reddens first.

### Deviation from the Required Fix

- **The enumeration clause is not the count the item names.** The
  acceptance test asks that "the enumeration count equals the chapters
  registry's count". Measured, those are not the same number and
  cannot be: the registry files **57** sections while the payload
  publishes **11** record populations — the rest are scalars, objects,
  drawings and namespaces. What actually makes a new section unable to
  dodge the sweep is three clauses instead: the populations are
  *discovered* from the payload rather than listed; nothing published
  is left out unless `DRAWN_ELSEWHERE` carries a written reason for
  it; and every swept population resolves to a **named** chapter.
- **The sweep runs in the node shim, not the browser tier.** The item
  says "a parametrized sweep in the browser tier". Thirty renders is
  thirty browser boots for claims — a section drawn, an empty marker,
  the rows a reader can see, the badge over them — that are in the DOM
  either way, and `UX-360` already measures pixels at scale in Chrome.
  Measured cost of the choice: **1.3s** in the medium tier, of which
  the `analyze` subprocess is nearly all.
- `tests/degenerate_store.py`, which the Required Fix names, builds
  degenerate *stores*; this sweep needs degenerate *populations* of a
  real payload, so it slices and repeats the payload's own rows
  instead. Nothing in that file was reusable here.
