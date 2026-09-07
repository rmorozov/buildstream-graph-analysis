# UX-747: the `derive` skill's own example crashes the tool it documents

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-340 (`dev_js_deps`), UX-450 (the skill's reason to exist) | **Serves:** the session about to move viewer code, which `CLAUDE.md` sends to `derive` first | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`CLAUDE.md` says *"`derive` before moving viewer code"*. Run the
example that skill documents and the tool raises:

```console
$ python3 tools/dev_js_deps.py --crossings bga/viewer/app.js --groups '{...}'
TypeError: '<' not supported between instances of 'str' and 'NoneType'
  tools/dev_js_deps.py:373, in crossings(), sorted(needed.items())
```

`needed.setdefault((home.get(name), home[word]), [])` (`:369`) puts
`None` in the key whenever an **unplaced** declaration references a
**placed** one. That is the normal state of a *partial* grouping — which
is the skill's entire stated use case, §"Deciding where to cut". An
exhaustive grouping does not crash, which is why nobody has hit it.

**And the guard cannot reach it.** `test_the_graph_is_derived_not
_guessed.py::test_a_grouping_that_leaves_a_declaration_out_is_named`
exists for exactly this path, but its fixture happens to pair a
grouping and a file in which no unplaced declaration references a
placed one, so the intended behaviour — exit 1, print `UNPLACED` — is
never exercised against the input that actually fires. `CLAUDE.md`
names this shape: *a guard whose setup another gate already excludes*.

The example is stale on top of the crash: `QUANTITY`, `columnSpecs`,
`buildTable`, `renderTable` and the rest are not declarations of
`app.js` any more — `UX-337` split them into `views.js`, `format.js`
and `structured.js`. `--declarations bga/viewer/app.js` lists
`stampHeader`, `wireJumpBox`, `boot`, `load` instead.

## Required Fix

`crossings()` handles an unplaced home — the tool already means to
report `UNPLACED` and exit 1, so the key needs an order the sort can
take rather than `None`. The guard's fixture is rebuilt so that an
unplaced declaration **does** reference a placed one; that is the
input the skill's own example produces.

Then the skill's example is re-derived from the file as it stands, not
edited to look plausible: run `--declarations bga/viewer/app.js` and
paste a grouping built from what it prints.

## Out of Scope

- Re-cutting `app.js`. This row is about the instrument, not a move.
- The other `dev_js_deps` modes (`UX-340`, `UX-742`), which the same
  guard file covers and which this review ran clean; **declined** as a
  target, there is nothing measured to fix in them.

## Acceptance Test

The skill's example, copied verbatim from `SKILL.md` and run, exits 1
and names the unplaced symbols. Mutation: restore the `None` key —
`TypeError` again, and the rebuilt fixture reddens where today's does
not. Second mutation: place every declaration — exit 0, no `UNPLACED`.
