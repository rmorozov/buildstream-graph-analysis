# UX-747: the `derive` skill's own example crashes the tool it documents

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-340 (`dev_js_deps`), UX-450 (the skill's reason to exist) | **Serves:** the session about to move viewer code, which `CLAUDE.md` sends to `derive` first | **Topic:** guards | **Area:** tools | **Shape:** judgement

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

## Outcome (round 103, 2026-09-07) — 🟢 Done

**Premise:** held, and understated — the documented command raised
**two** different exceptions, not one, and the second fires on every
grouping the skill writes.

### The gap, measured

```text
$ python3 tools/dev_js_deps.py --crossings bga/viewer/app.js --groups '{"consts": [...], "fetch": ["watchTheFetch"]}'
TypeError: '<' not supported between instances of 'NoneType' and 'str'
  dev_js_deps.py:373, sorted(needed.items())

$ python3 tools/dev_js_deps.py --crossings bga/viewer/app.js --groups '{<the skill's three groups>}'
OSError: [Errno 36] File name too long
  dev_js_deps.py:463, pathlib.Path(raw).exists()
```

The second was not in the filing. `--help` promises `--groups` takes
"a file or a literal", and the path test ran first: any literal past
the 255-byte name limit made `exists()` itself raise, before a line of
JSON was parsed. Every grouping the skill documents is past it.

### After

```text
$ python3 tools/dev_js_deps.py --crossings bga/viewer/app.js --groups '{...}'
app <- handoff               inflated inlined optional wireTheHandoff
fetch <- handoff             announceHandoff
handoff <- app               load
handoff <- fetch             watchTheFetch
```

The re-derived example is a better teacher than the stale one: it shows
**two real cycles** (`app`/`handoff`, `fetch`/`handoff`), which is the
thing the surrounding prose tells the reader to look for and previously
only asserted.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| P1 | the `None` sort key restored | the partial-grouping clause |
| P2 | the `None` label restored | 2 clauses |
| P3 | `unplaced` stops being reported | 2 clauses |
| P4 | the path test runs before the JSON again | 2 clauses |
| P5 | the skill's example made stale again | the example clause |

### Deviation from the Required Fix

**The fixture was not rebuilt; a second one was written.** The Required
Fix says rebuild `interpolated.js`'s, and that fixture is measured by
three other clauses — `LABEL` exactly twice, `alpha` exactly once, one
crossing — each of which a new declaration breaks. `partial_groups.js`
holds the two referencing declarations this path needs and leaves those
counts alone.

The filing's diagnosis was also half right: the old fixture **does**
produce a `None` key (`"None <- lower"` in its JSON). What it cannot
produce is a second key with a real home, and the guard never read
`crossings` at all — so it would have missed the label either way. It
reads it now.

Seen and left: `crossings()` appends per referencing declaration, so
two declarations in one group referencing the same symbol list it twice
(`["SHARED", "SHARED"]`). Cosmetic, outside this row, asserted as a set
so no clause blesses it.

```text
$ make test
7640 passed, 83 skipped, 1 warning in 435.01s (0:07:15)
$ make lint
All checks passed! / clean: 291 finding(s)
```

