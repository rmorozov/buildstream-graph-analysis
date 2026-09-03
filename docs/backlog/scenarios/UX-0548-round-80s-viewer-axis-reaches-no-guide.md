# UX-548: five mechanisms round 80 shipped, and no guide names one

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Serves:** anyone who reads a guide to find out what `bga view` does | **Topic:** docs

## Motivation

Architecture review 12. `UX-241` filed the cadence guard because the
viewer axis ran `UX-193`..`UX-226` — 34 closed rows — with no document
noticing. Round 80 shipped eight viewer and export items and the same
thing happened at one round's scale:

```text
mechanism                        shipped in    named in a guide?
bga view --reanalyse             UX-533        NO  (git grep -in reanalyse -- docs
                                                    README.md CHANGELOG.md: only
                                                    the task file and its closed row)
the export's compact data half   UX-529        NO  (cli.md:1302 "the run's JSON
                                                    inlined"; architecture.md:864
                                                    "inlines every served document")
STORE_WINDOW = 12, store-all.json UX-528       NO  (cli.md:1038 and
                                                    what-the-viewer-answers.md:135
                                                    describe an unbounded picker)
PICKER_SHOWN = 8, the search box   UX-527      only docs/design/styleguide.md:607
the timeline degrades, not refuses UX-530      cli.md:1374 yes;
                                                what-the-viewer-answers.md:159 still
                                                says "Above 8,000 tracks it is refused"
```

`--reanalyse` is the worst of the five: the served page *prints a
sentence naming the flag* (`analysis_source`, `tools/bga_view.py:295`),
so a reader is told to run a command that appears in no document —
`UX-326`'s class, a sentence the tool speaks being a contract.

`docs/guides/what-the-viewer-answers.md` was not touched by round 80 at
all (`git diff --name-only origin/main..HEAD -- docs/guides/`), and it
is the document the page's own readers are pointed at.

## Required Fix

Each of the five reaches the guide that owns it: `cli.md` for the
flag, the compact form and the window; `what-the-viewer-answers.md` for
the degradation and the picker; `architecture.md` where its sentence
about `--export` inlining is now wrong. `architecture.md:700` also
still calls the server's table "a fixed document table" and does not
name `store-all.json`.

## Out of Scope

- Re-measuring the export weights — `UX-529`'s Outcome has them.
- A guard that every new flag reaches a document; that is `UX-326`'s
  axis and a separate argument.

## Acceptance Test

`git grep -in "reanalyse" -- docs README.md` names a guide; the
refusal sentence in `what-the-viewer-answers.md` matches
`tools/bga_view.py::_degradation_steps`; `store-all` appears in a
document a reader opens.

## Outcome (round 81, 2026-09-03) — 🟢 Done

### The gap, measured

```text
$ git grep -in reanalyse -- docs README.md CHANGELOG.md | grep -v backlog/scenarios
(nothing, exit 1)
$ git grep -in 'store-all\|STORE_WINDOW' -- docs README.md | grep -v backlog/scenarios
(nothing)
$ git grep -n DATA_COMPACT_MIN_B -- docs
(nothing)
$ git grep -n PICKER_SHOWN -- docs
docs/design/styleguide.md:607     a nodes-budget restatement, not a guide
$ sed -n '159p' docs/guides/what-the-viewer-answers.md
- **Above 8,000 tracks it is refused** (`UX-430`), and that one is not
```

All five reproduced on `ca825c3`. The served page prints
`"reanalyse": "bga view RUN --reanalyse"` (`tools/bga_view.py:329`,
spelled by `app.js:112`) in a sentence telling a reader what to run,
and no document a reader opens named the flag.

### After

```text
$ git grep -in reanalyse -- docs README.md | grep -v backlog/scenarios
docs/guides/cli.md:1133:bga view @last --reanalyse    # analyse with this build…
docs/guides/cli.md:1143:`--reanalyse` is that command. It analyses the run…
$ git grep -n store-all -- docs | grep -v backlog/scenarios
docs/design/architecture.md:702   docs/guides/cli.md:1051
docs/guides/what-the-viewer-answers.md:147
```

The ladder is read, not restated: `_degradation_steps` returns two
steps, the second narrowing with **`--planes 1`, which leaves Plane 2's
process lanes out**, and the guide now names that step verbatim under a
guard that reads the tuple.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | `_degradation_steps`' narrowing reworded to "`--planes 1`, which drops the process lanes" | 1 — `test_the_guide_names_every_narrowing_the_export_tries` |
| A2 | a third step appended to `_degradation_steps` | 2 — that clause, and `test_the_count_of_steps_is_the_count_in_the_prose` |

Reverted: `test_the_viewer_perfetto_boundary.py` 12 passed in 0.57s. No
guard of mine failed to discriminate.

### Deviation from the Required Fix

One addition, one restraint. **Addition:** a guard the fix did not ask
for — two clauses in `test_the_viewer_perfetto_boundary.py` holding the
guide's ladder against `_degradation_steps` — because the sentence this
item replaced drifted for a round with nothing to catch it. It is not
`UX-326`'s every-flag axis, which stays out of scope. **Restraint:**
`UX-545` is rewording what the page says when a timeline is refused
outright, so this guide states the ladder and the degrade step and does
not quote the refusal sentence.

`architecture.md`'s Verification Log was re-grounded (23 ids, 9
superseded, 8 printable, 15 not; `analyze/v5` 56 top-level properties —
every figure unchanged), because editing the document makes the log
stale by `test_the_verification_log_is_true.py`.

```text
dev_touching.py --base ca825c3   34 files · 647 passed, 4 skipped in 62.53s
make lint                         clean (ruff + PyMarkdown)
make test                         the orchestrator's gate; not run in this track
```

Committed with `BGA_SKIP_SELECTOR=1`: this track may not edit
`README.md`, so the row stays 🔴 against a 🟢 file until the
orchestrator's `--move`, and `test_the_table_status_matches_the_task_files`
plus `test_the_loop_stays_fast.py::test_check_reports_a_clean_tree_as_clean`
are red for that reason alone. Both were green before the status line
moved; everything else in the selector passed (332 passed, 3 skipped
before the run stopped at 2 failures).
