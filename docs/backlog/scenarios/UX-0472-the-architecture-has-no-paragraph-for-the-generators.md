# UX-472: the architecture says one script needs no `bst`, and now three tools do not fit the sentence

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-465`, `UX-466` shipped the tools; nothing blocks the document | **Found by:** architecture review 9, checklist questions 1 and 4 | **Serves:** the round that asks the architecture where fixtures come from and finds one paragraph about one script | **Topic:** docs

## Motivation

`docs/design/architecture.md:91` opens:

> One script in `tools/` is not part of that pipeline and needs no
> `bst` at all: `tools/gen_synthetic_scale_run.py` …

The uniqueness claim was true when it was written and is not now.
Round 72 shipped three tools that the sentence cannot hold:

| tool | needs `bst` | what it produces |
|---|---|---|
| `tools/gen_synthetic_scale_run.py` | no | a synthetic run directory |
| `tools/bga_gen_project.py` | to *build* what it writes, yes | a BuildStream project |
| `tools/dev_finding_coverage.py` | no | which findings a capture produces |
| `tools/dev_trace_coverage.py` | no | which captured field reaches the trace |

```text
$ grep -c "bga_gen_project\|dev_trace_coverage\|dev_finding_coverage" \
      docs/design/architecture.md
0
```

The architecture names none of them. `bga_gen_project.py` is the one
that matters most: it is the first thing in the tree that turns a
*shape* into a project `bst build` accepts, which is a direction the
architecture has a paragraph-shaped hole for — everything else in
`tools/` either wraps a build or reads one.

`UX-463` settled the design (curated fixtures own graph shape, timing
and run mode; a generator owns outcome, sandbox profile and scale) and
that argument lives only in a backlog row. A backlog row is a record of
one decision; the architecture is where a reader looks for the shape.

## Required Fix

A paragraph in `docs/design/architecture.md` for where fixtures come
from, replacing the one-script sentence: the two halves `UX-463`
split, which tool owns which axis, and why the generated half cannot
be synthesised (axis F does not exist above `bst`). Plus the two
censuses in whatever section names the dev instruments —
`dev_js_deps.py` and `dev_perfetto_queries.py` are the precedent.

Whether the fixing guide's §6 context map is enough for the censuses
is a judgement the fix should make explicitly: they are already there,
and a second home is only worth it if the architecture's reader needs
them.

## Out of Scope

- Changing any of the four tools. This is a document that has fallen
  behind code that is correct.
- `CLAUDE.md`'s tree map, which is `UX-471`.
- The spec's Part text — it is ground truth, and a review that finds it
  wrong files against it rather than editing it.

## Acceptance Test

```bash
grep -c "bga_gen_project" docs/design/architecture.md
python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
```

non-zero and green, with the one-script sentence either gone or true.
