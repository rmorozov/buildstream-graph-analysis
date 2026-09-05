# UX-359: every guard measures a page with Plane 2 stripped out of it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-329 (the terminal and the viewer agree about Plane 2), UX-347 (the distance budget) | **Serves:** every budget, census and geometry assertion in the suite | **Topic:** guards | **Area:** bga/viewer

## Motivation

Every browser guard in the repository sets its page up the same way:

```python
run = tmp_path_factory.mktemp(f"shape-{name}") / "run"
shutil.copytree(fixture, run)
page = ... ; view.export(str(run), str(page))
```

`macro_micro`'s Plane 2 report is not inside `run/`. It is
`tests/fixtures/macro_micro/plane2.json`, a **sibling**, found by
`run_store.sibling_plane2` looking at `../plane2.json` from a directory
named `run`. `copytree` copies the run and leaves the sibling behind,
so every guard exports a page with Plane 2 missing:

```text
sibling plane2.json beside the fixture: True
sibling plane2.json beside the copy   : False

                                 height  sections  words  buttons  svg  strips
the page a user gets            24,689px       58  8,174      381   16      19
the page every guard measures   21,346px       55  6,845      341   15      18
```

Three sections, 1,329 words, 40 buttons and 3,343 px of page that no
guard has ever seen. Every budget in the repository — the distance
budget, the emphasis budget, the drawing census, the control counts,
the geometry assertions — is calibrated against a page 14% shorter
than the one users get, and the missing 14% is the *Plane 2* half: the
half the tool's second plane exists to produce.

This also cost this round an hour and a retracted finding. Measuring
through a copy, I concluded the page never rendered `plane2_absence`
and hardcoded a contradicting sentence. It does render it, correctly,
and differently per fixture (`NOT_CAPTURED` on `golden`,
`CAPTURED_NO_RAW_LOG` on `macro_micro`) — the copy had simply turned
one fixture into the other. An instrument that silently converts your
richest fixture into your poorest is worse than no instrument.

## Required Fix

- **Export from the fixture where it lies**, or copy the snapshot
  directory rather than the run. The reason a copy is made at all is
  `expected_output.json`, which some guards unlink; that is a
  one-file concern and does not require relocating the run away from
  its siblings.
- **One shared fixture helper**, in `tests/`, that produces the two
  exported pages every browser guard wants — so the next guard cannot
  reintroduce this by copy-pasting the setup, which is how all seven
  of the current ones got it.
- **A guard on the guards**: the exported page a test measures has the
  same section count as the page exported from the fixture in place.
  `UX-264` made the DOM shim shared for the same reason; this is the
  fixture half of that argument.

## Out of Scope

- Moving `plane2.json` inside `run/`. That would change
  `run_store`'s layout contract to suit a test, which is the wrong
  direction — the layout is what `bga snapshot` writes.
- Re-baselining every budget in one commit. The budgets should be
  re-measured against the real page, but each against its own item's
  argument; a blanket bump is how a bound stops meaning anything.
- `golden`, which has no Plane 2 at all and is unaffected. It is also
  why this went unnoticed: the fixture that would have shown it is
  the only one with a sibling.

## Acceptance Test

For each committed fixture, the page a guard exports and the page
exported from the fixture in place agree on section count, rendered
`data-section` keys, and whether `plane2_absence` renders — asserted
in one guard that names the copy as the thing under test. And the
seven existing browser guards go through the shared helper, so the
count they measure is the count a user gets.

## Outcome (round 56, 2026-08-28) — 🟢 Done

### The gap, measured

```text
$ python3 scratch/stripped.py
sibling plane2.json beside the fixture: True
sibling plane2.json beside the copy   : False
  the page a user gets            24689px  sections  58  words  8174  buttons  381  svg  16  strips  19
  the page every guard measures   21346px  sections  55  words  6845  buttons  341  svg  15  strips  18
```

### After

```text
$ python3 -m pytest tests/unit/test_the_guards_measure_the_page.py -q
14 passed, 1 skipped in 11.91s
```

`TestTheCopyRendersTheSamePage::test_the_two_pages_agree` is the one
that matters: it boots the page the copy produces and the page the
fixture produces in place, and compares sections, words, buttons,
inputs, svg, strips and which Plane 2 absence sentence renders. They
are equal on both fixtures.

### The copy was never the defect; copying only the run was

`tests/pages.py` copies the **snapshot** — the run directory and its
siblings — and returns the run inside it. Sixteen call sites across
fourteen guards now go through `snapshot_copy`, which is the whole of
what each of them was doing by hand:

```text
-    run = tmp_path_factory.mktemp(f"shape-{name}") / "run"
-    shutil.copytree(fixture, run)
-    (run / "expected_output.json").unlink(missing_ok=True)
+    run = snapshot_copy(fixture, tmp_path_factory.mktemp(f"shape-{name}"))
```

The copy is still made rather than exporting in place, and
`TestTheCopyIsStillNecessary` says why in a clause rather than a
comment: `golden` carries an `expected_output.json` that `bga view`
refuses to export beside, and dropping it is the only thing the copy
is for. If that file ever leaves the tree, that clause reddens and the
guards should export in place.

### What the blind spot was hiding

The conversion turned one guard red immediately:

```text
FAILED test_the_page_conforms_to_its_sections.py::TestTheDepthWalk::
       test_every_fold_either_counts_or_is_a_declared_layout_fold
AssertionError: fold(s) that announce no depth and are not declared
layout folds: {'macro_micro': [('evidence-fold', '7 measurements'),
                               ('evidence-fold', '7 measurements')]}
```

`renderFindingEvidence` in `app.js` builds a `<details>` by hand and
never gave it `data-levels` / `data-rows`. This is exactly the defect
`UX-320` found and fixed in its hand-built twin `evidence-detail` —
and the reason the conformance pass could not find this one is that
the fold only appears on a finding with more than `EVIDENCE_SHOWN`
scalars, and the only fixture with such a finding is the Plane 2 half
of `macro_micro` that every `copytree` was dropping. It now reads
`7 measurements · 1 level, 7 rows`, like every other value fold.

That is the argument for this item having been ordered first: a blind
spot does not announce what it is hiding, and one item's worth of
looking straight at it produced a §3a.1 violation nobody had filed.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `a4480b7`.

| # | mutation | reddened |
|---|---|---|
| N1 | `snapshot_copy` copies the run alone again — the defect itself | 5 clauses, including both `macro_micro` page comparisons and *"the fixture has a Plane 2 sibling (True) and its copy does not"* |
| N2 | one guard reverted to the hand-rolled copy, import removed | `test_every_macro_micro_page_goes_through_the_helper`, naming the file |
| N3 | the copy stops dropping `expected_output.json` | `test_the_copy_drops_it` |
| N4 | the evidence fold goes quiet again | the depth walk, naming `('evidence-fold', '7 measurements')` |

**N2 survived twice before it discriminated, and both survivals were
the guard's fault rather than the mutation's.** The first source rule
required the copy's *destination* to be spelled `… / "run"`; the idiom
binds that a line earlier and passes `run`, so the pattern matched
nothing and the clause was vacuous over the whole repository. The
second read the copy's source token against module-level names; the
idiom's source is a **loop variable** (`for name, fixture in
FIXTURES.items()`), so it was vacuous again. The third parses the
module and resolves a name through whatever bound it — an assignment
or a `for` — transitively, because `fixture` is bound by
`FIXTURES.items()` and it is `FIXTURES` two steps back that names the
path. `test_the_walk_can_see_a_macro_micro_copy` now exercises all
three spellings directly, so the next narrowing of that rule reddens
in the instrument rather than going quiet.

### Deviation from the Required Fix

- The Required Fix asked for the walk to cover "the seven existing
  browser guards". There were **fourteen**, at sixteen call sites; the
  count in the filing was of the guards visible in the round-55
  measurement rather than of the guards in the tree.
- Guards that copy only `golden` are deliberately **not** converted.
  `golden`'s fixture has no siblings — `tests/fixtures/golden/` holds
  nothing but `mixed_task_kinds` — so the run-only copy loses nothing
  there, and the rule the new guard enforces is scoped to
  `macro_micro` copies for that reason rather than becoming a rule
  about `copytree`.
- Two guards that copy a `macro_micro` run to build a **store** rather
  than a page (`test_a_capture_that_cannot_start.py`'s debris tree,
  `test_the_printed_sentences_are_contracts.py`'s store run) are out of
  the population and stay as they are: nothing in either reads Plane 2,
  and widening the rule to reach them would make it a rule about
  copying rather than about the page.
- No budget was re-baselined. The Out of Scope section asked for that
  and it turned out not to be needed: of the fourteen converted guards,
  only the conformance pass reddened, and it reddened on a defect
  rather than on a bound.
