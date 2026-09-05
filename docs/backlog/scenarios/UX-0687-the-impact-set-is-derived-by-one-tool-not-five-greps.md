# UX-687: the impact set is derived by one tool, not five greps

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-524 (the CI-measured touching map), UX-498 (decompose), UX-499 (the orient recipes) | **Serves:** the session at the design stage, before the first edit | **Topic:** guards

## Motivation

The `decompose` skill derives *surfaces* — the files a change touches
and the guards that name them (`dev_touching`, the touch map). What
a design-stage reader also needs is the *impact*: which contracts a
module emits, which findings it produces, which guides name the
module or its command, which styleguide sections cite the viewer
module, which open filings sit on the same area. Today that is five
recipes in the `orient` skill, run by hand, or not.

```text
tools/dev_touching.py     grep selector           module → test files
tools/dev_touch_map.py    coverage map (CI-filled) module → test files
tools/dev_js_deps.py      viewer import graph
module → contracts / findings / guides / styleguide § / open filings   no index (grep tools/ → 0)
```

## Required Fix

`tools/dev_impact.py <diff | UX-NNN | module>` prints the impact set:
modules; contracts (`bga/schemas.py` keys by emitting module, via
`bga/contracts.py`); finding ids (`bga/findings.py` by module);
guides and README lines naming the module or its `bga` command;
styleguide sections the viewer module cites; guards (grep ∪ touch
map ∪ census set); open filings whose area (`UX-688`) matches. The
`decompose` skill's §1 becomes "run the tool and paste"; a filing's
decomposition block carries the set.

## Out of Scope

- Judging the impact — the tool lists; the session decides what a
  change may break.

## Acceptance Test

For a diff in `bga/correlate.py` the set names `correlate/v2`, the
restructuring finding, `real-project.md`'s Step 6, the join guards
and any open correlate filing; mutation: drop the contracts source —
red on the contract row.
