# UX-398: the library question, measured against the factory

**Priority:** High | **Status:** 🟢 Done Done | **Depends on:** UX-397 (the filed question), UX-392 (the filters it would buy), UX-367 (the volume budget that arbitrates) | **Serves:** R8, and anyone deciding what this page may depend on | **Topic:** viewer

## Motivation

`UX-397` files the Tabulator question with one argument for adoption:
"a library answers sorting, filtering, and virtual scrolling at 1,200
rows **in one dependency rather than in twenty-one modules**."

Round 64 measured that premise, and it is wrong:

```text
$ grep -l 'renderTable\|buildTable' bga/viewer/*.js
bga/viewer/app.js          (the caller)
bga/viewer/primitives.js   (the factory's parts)
bga/viewer/structured.js   (the factory)
```

Every one of the 31 tables flows through one factory —
`buildTable`/`renderTable` in `structured.js` — which already
implements declared column specs, declared-not-sampled sorting
(`UX-284`/`UX-289`), the 22 preset menus (`presetColumns`), Top-N,
fold-the-middle, the density strip and the copy control. The 21
viewer modules *consume* the factory; none hand-rolls a table. So the
marginal cost of `UX-392` (a filter on all 31 tables) is one change
to one factory, and every future table gets it free — which is
exactly the economics a library promises, already owned.

The against-side stands as `UX-397` filed it (a ~400 KB library on a
477 KB self-contained export; four-CDN CSP so it ships inside the
file) and gains three arguments the filing did not price:

1. **The styleguide is law over this DOM.** `shapes.js classify()`,
   the §2a/§3a/§3b guards and the conformance walks all assert the
   page's own markup. A library's DOM either fails those guards or
   gets wrapped until the visual contract is re-implemented on top of
   it — the "reimplementing the world" cost, inverted.
2. **The console guard would light up.** `UX-334` holds every served
   page to zero CSP violations; table libraries write inline style
   attributes as a matter of course.
3. **There is no toolchain to carry it.** The repo has no
   npm/bundler/lockfile; one runtime dependency imports the whole
   supply-chain and upgrade question the page was built to avoid
   (`UX-296` — the view that parses nothing).

## Required Fix

Record the decision in `UX-397` and replace the standing question
with a standing **rule**, in `docs/design/styleguide.md` (one short
section beside §6's export rules):

- A JS dependency is admitted only when a required behavior
  (a) cannot be met by the factory plus a platform primitive within
  the volume budget — shown by a measured before/after of the
  export's page half, the `UX-382` split — and (b) the library's
  wiring-plus-conformance cost measurably undercuts the in-house
  cost. The trackevent precedent (`tools/native_trace/trackevent.py`
  instead of a protobuf dependency) is the named prior.
- The factory measurement above is pasted beside the rule, so the
  next person to ask starts from the number, not the impression.

## Out of Scope

- Adopting or rejecting any specific library forever — the rule
  prices future candidates; it does not blacklist them.
- The rail pin and the other half of `UX-397` — that half stands on
  its own.
- Implementing `UX-392`'s filters — this task only establishes where
  they land (the factory); the filing itself stays the work order.

## Acceptance Test

- The styleguide carries the rule and the pasted measurement; the
  docs guards pass.
- `UX-397`'s file records the decision under its "Falsification"
  clause ("the decision is recorded here either way"), with the
  export's measured page and data halves beside it.

## Outcome (round 65, 2026-08-29) — 🟢 Done

Done, and the filing's measurement holds in a stronger form than it was
written in.

### The gap, measured

`UX-397` priced the question against "twenty-one modules". The strongest
version of the counter-measurement is not that three modules mention the
factory — it is that **one line in the whole viewer constructs a table**:

```text
$ grep -rn 'el("table"' bga/viewer/*.js
bga/viewer/structured.js:435

viewer modules                21
modules that construct a table 1
modules that call the factory  2   (app.js, structured.js itself)
```

Nothing held that. The premise the price is computed from could have
gone stale to a single hand-rolled table in any module, and the next
person to ask the question would have been argued at with a number that
was true in 2026 and false by the time they read it.

### After

`docs/design/styleguide.md` §6b carries the rule with both conditions,
the named prior (`trackevent.py` instead of a protobuf dependency), the
pasted factory measurement, and the export halves the price is against:

```text
bga view tests/fixtures/macro_micro/run --export
  export total   417,859 B
    page half    269,531 B
    data half    148,328 B
```

`tests/unit/test_one_factory_builds_every_table.py` holds the premise —
four clauses, 4 passed in 0.08s.

### The shape: hold the premise, not the conclusion

The guard deliberately does **not** assert "no library, ever". §6b
prices candidates rather than blacklisting them, and a guard asserting
the conclusion would have to be deleted the day a candidate met the
price — which is the shape that teaches people to delete guards. What is
guarded is the sentence the price is computed from: one factory, its two
exported entry points, at least one caller outside it, and the rule's
two clauses plus its measurement surviving an edit of the section.

**A guard this round did not add.** The obvious one — the export
references no external origin — already exists as
`test_the_report_you_can_attach.py::test_no_reference_reaches_the_network_or_the_filesystem`,
which allowlists `#`, `data:`, `mailto:` and `ui.perfetto.dev`. Writing
a second copy would have been a fifth number in a fourth place.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| A1 | a second viewer module constructs `el("table", {})` | `test_one_module_constructs_a_table` (1 failed, 3 passed) |
| A2 | the factory stops exporting `renderTable` | `test_the_factory_publishes_the_entry_points_the_page_uses` (1 failed, 3 passed) |
| A3 | §6b's rule drops "inside the volume budget (§3e)" | `test_the_dependency_rule_states_both_of_its_conditions` (1 failed, 3 passed) |
| A4 | §6b keeps its prose and drops the pasted command | `test_the_rule_carries_the_measurement_it_was_written_from` (1 failed, 3 passed) |

A1 is the defect the rule's premise dies of. A3 and A4 are the pair the
section is really about: a rule with one clause admits a library on
bytes alone, and a rule with no measurement is an opinion.

### Deviation from the Required Fix

**None.** Both bullets landed: the rule with its two conditions and the
trackevent prior in the styleguide, and the pasted factory measurement
beside it. `UX-397`'s file records the decision under its Falsification
clause with the export halves, as the Acceptance Test asks.

`UX-397` itself stays open — its rail pin is untouched work and this
item's Out of Scope says so.

### Verification

```text
pytest tests/unit/test_one_factory_builds_every_table.py           4 passed
pytest tests/unit/test_docs_links_and_commands.py                 36 passed
make test-touching                              396 passed, 1 skipped, 132.8s
make lint                                                          clean
```

The full suite runs once at the end of round 65's phase A rather than
once per item; its line is in `docs/audits/round-65.md` beside the
phase it covers.
