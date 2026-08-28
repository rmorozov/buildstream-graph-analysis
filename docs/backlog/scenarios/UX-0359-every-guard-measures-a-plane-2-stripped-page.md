# UX-359: every guard measures a page with Plane 2 stripped out of it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-329 (the terminal and the viewer agree about Plane 2), UX-347 (the distance budget) | **Serves:** every budget, census and geometry assertion in the suite | **Topic:** guards

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
