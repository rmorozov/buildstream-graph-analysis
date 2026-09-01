# UX-472: the architecture says one script needs no `bst`, and now three tools do not fit the sentence

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-465`, `UX-466` shipped the tools; nothing blocks the document | **Found by:** architecture review 9, checklist questions 1 and 4 | **Serves:** the round that asks the architecture where fixtures come from and finds one paragraph about one script | **Topic:** docs

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

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

```console
$ grep -c "bga_gen_project\|dev_trace_coverage\|dev_finding_coverage" \
      docs/design/architecture.md
0
```

against a document whose relevant sentence opened *"One script in
`tools/` is not part of that pipeline and needs no `bst` at all"* — a
uniqueness claim that three round-72 tools falsify.

### After

The sentence is gone, replaced by a section — **Where fixtures come
from** — that states the split rather than the exception:

```console
$ grep -c "bga_gen_project" docs/design/architecture.md
2
$ grep -n "One script in .tools/" docs/design/architecture.md
(exit 1)
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
39 passed in 6.89s
```

It carries `UX-463`'s answer as a four-row table — who writes each
half, what it produces, whether it needs `bst`, which axes it owns —
and then the part that is the actual argument rather than the
bookkeeping:

- a curated triple is deterministic to the microsecond, which is the
  only way to build a fixture whose two longest paths are within a few
  percent of each other. A real build cannot be asked for a near-tie
  critical path, and `blast_radius_disagrees_with_horizon` and
  `shared_base_wide`'s `tie_ratio` exist because of it;
- a synthesised trace can only assert what its author already believed,
  so a process storm or inode-count staging — things the hook and the
  spine *observe* — **is an axis that does not exist above `bst`**.

`gen_synthetic_scale_run.py` keeps its paragraph, now positioned as the
curated half at a scale nobody hand-writes rather than as a lone
exception, and its closing sentence about exercising analysis only is
where the generator earns its place: that hedge is exactly what
`bga_gen_project.py` removes.

The section ends with `UX-189` — captures are never committed, so a
clone carries fixtures and no real run — because that is what makes the
two censuses necessary rather than nice.

### The judgement the Required Fix asked for, made explicitly

**The censuses stay in the fixing guide's §6 and get no second home.**
Measured before deciding:

```console
$ grep -n 'dev_js_deps\|dev_perfetto_queries' docs/design/architecture.md
$                                       # nothing: the named precedent is not there either
$ grep -n 'dev_finding_coverage\|dev_trace_coverage' docs/contributing/fixing-guide.md
233:tools/dev_finding_coverage.py  which findings a committed capture really
235:tools/dev_trace_coverage.py  which captured field reaches the emitted
```

The row offered `dev_js_deps.py` and `dev_perfetto_queries.py` as the
precedent for naming them in the architecture, and the precedent is the
opposite one: neither is in that document, both are in §6, and §6
already carries one-liners for all four round-72 tools. So the
architecture names the two censuses in one sentence that says where the
list lives, and does not copy the list. Two homes for one list is how
the homes disagree — `UX-240`'s rule, and `CLAUDE.md` follows it in the
same round.

### Deviation from the Required Fix

None. Both halves done — the fixture paragraph replacing the one-script
sentence, and the censuses' placement decided out loud with the
measurement that decided it.

No guard. The row asked for none, and the two things a guard could hold
here are already held: `test_docs_links_and_commands.py` checks every
path and link the new section names, and the uniqueness claim that went
stale is gone rather than restated in a form that could go stale again.

### One thing this row missed, found one commit later

`test_the_verification_log_is_true.py::test_the_claimed_date_is_not_older_than_the_last_change`
reddened on the **next** commit, not this one:

```text
the Verification Log claims 2026-08-31 (after UX-450), and
architecture.md was last changed 2026-09-01.
```

It reads `git log` for the document, so while the edit was uncommitted
the log still said 2026-08-31 and `make test` was green — the guard can
only speak once the commit exists. Fixing guide §3.10 wanted the
re-grounding in this commit and it went into the next one; the log now
carries a round-73 entry naming what changed and why, with both
grounding figures re-read (**21 ids, 8 superseded**; **56 top-level
properties**) rather than carried forward.

### The runs

```text
make test-touching                            285 passed in 5.74s
make test                                     5627 passed, 27 skipped, 1 warning
                                              in 324.64s (0:05:24)
make lint                                     All checks passed!
```
