# UX-576: the question count is stated three ways

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-469 (the seventeenth question), UX-549 (derived figures) | **Serves:** the reader deciding whether to open Perfetto | **Topic:** docs

## Motivation

```text
bga/viewer/questions.js                       17 question ids
docs/guides/what-the-viewer-answers.md:53     "seventeen" (9 + 8)
docs/guides/what-the-viewer-answers.md:93     "turned the count above from thirteen into sixteen"
docs/guides/cli.md:1504                        "Six of the thirteen canned questions… seven are sharper"
.claude/skills/measure/SKILL.md:117            "fourteen questions"
tools/dev_perfetto_queries.py:13               "fourteen"
```

The boundary guard reads only "serves N questions"; the other four
sentences are unread. `resource-queues` landed on 2026-09-01 and the
prose around the count was written before it.

## Required Fix

One derived count: every sentence that counts the questions is
either derived (`UX-549`'s shape from `questions.js`) or names the
question ids it counts, and a guard reads every "N … questions"
phrase across `docs/` and `.claude/` against the file.

## Out of Scope

- The questions themselves — `UX-368` and `UX-469` own their content; this is the count.

## Acceptance Test

Mutation: add an eighteenth question — every counted sentence reds
or derives.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** held, and understated — the count is stated *eight* ways,
not three, and the "seventeen" in the guide was the only right one.

```console
$ node --input-type=module -e 'const q = await import("./bga/viewer/questions.js");
  console.log(q.QUESTIONS.length, q.QUESTIONS.filter(x => q.takesElement(x)).length);'
17 4
```

Seventeen, and the guide's `serves seventeen questions` was the one
right sentence - the only one a guard already read. `cli.md`'s
thirteen, the skill's and the harness's fourteen were the drift; the
sweep found three more the item had not, two of them *subset* counts:

| where | said | is | fix |
|---|---|---|---|
| `cli.md:1494` | thirteen queries | seventeen | derived |
| `cli.md:1504` | six of thirteen / seven | nine / eight | derived off the guide's tables |
| `what-the-viewer-answers.md:82` | nine of seventeen / eight | right | derived, and now swept |
| `measure/SKILL.md:118` | fourteen | seventeen | derived |
| `dev_perfetto_queries.py:13` | fourteen | round 69's figure | kept, dated - and it cited `UX-465` for a run that is in `UX-432` |
| `dev_perfetto_queries.py:121` | three take an element | four | derived off `{element}` |
| `bga_timeline.py:1706` | two of fourteen | two | names its two ids |
| `questions.js:656` | two of fourteen | two | names its two ids |
| `questions.js:1008` | three of thirteen | four of seventeen | derived |

`questions.js:1008` is `takesElement`'s own docstring, one line above
the function that computes the number it gets wrong.

**The guard** (`test_a_counted_figure_is_derived.py`, +270 lines): a
sweep grows every `N … questions|queries` phrase backwards from its
noun through connective words only, over root and `docs/` markdown less
`backlog/` and `audits/`, `.claude/`, `tools/*.py` and `bga/**/*.js`.
It finds 17 phrases; each must be a sentence `_derived_sentences()`
builds from the population, or name the ids it counts, or be a dated
finding in `HISTORICAL` (7 entries, each asserted still present).
`test_the_sweep_reads_the_sentences_it_is_for` is the anti-vacuity
floor.

**Acceptance test** — the eighteenth question, added to `QUESTIONS`:

```console
$ PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest \
    tests/unit/test_a_counted_figure_is_derived.py \
    tests/unit/test_the_viewer_perfetto_boundary.py -q
13 failed, 26 passed in 0.98s
E   AssertionError: these sentences count the question library and nothing derives them:
E     README.md: 'all seventeen canned questions' counts [17]; the library serves 18 …
E     docs/guides/cli.md: 'seventeen paste-ready PerfettoSQL queries' counts [17]; …
E     docs/guides/cli.md: 'Nine of the seventeen canned questions' counts [9, 17]; …
E     …/what-the-viewer-answers.md: 'seventeen questions', 'Nine of the seventeen …'
E     .claude/skills/measure/SKILL.md: 'all seventeen questions' counts [17]; …
E     bga/viewer/questions.js: 'Four of the seventeen questions' counts [4, 17]; …
```

Reverted: `39 passed in 0.92s`.

| # | mutation | reddened | count |
|---|---|---|---|
| 1 | an 18th entry in `QUESTIONS` | 8 derived sentences, the sweep, the floor, both table clauses | 13 failed, 26 passed |
| 2 | `cli.md` back to "thirteen paste-ready" | its clause, the sweep, the floor | 3 failed, 24 passed |
| 3 | `_counted_files()` returns `[]` | the anti-vacuity floor only | 1 failed, 26 passed |
| 4 | drop the two ids from `bga_timeline.py`'s sentence | the sweep | 1 failed, 26 passed |
| 5 | architecture.md's dated "All six" → "All seven" | the historical clause, the sweep, the floor | 3 failed, 24 passed |
| 6 | move `graph-levels` between the guide's two tables | both split sentences, the sweep, the floor | 4 failed, 23 passed |

`make test-touching`: 63 files selected, 1134 passed, 38 skipped, 57.4s.
`make lint`: clean.

**Deviation.** One undeclared surface: `tools/bga_timeline.py`, which
the sweep found stating the count. `docs/design/styleguide.md:811` was
*not* touched — its "thirteen queries" sits in a section headed "(round
58)" whose next clause `UX-369` already fixed, so it is dated, not
drifted, and is in `HISTORICAL` beside `architecture.md:1390`,
`directions.md` and three comments in `questions.js`. No `rules.md` row
was added: the rule is `UX-549`'s, stated in fixing-guide §3.12 and
scoped there to Part 32 — widening it is the orchestrator's line.
