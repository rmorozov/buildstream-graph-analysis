# UX-570: the capture workflow document describes a workflow that has moved on

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-381 (the capture directory contract), UX-516 (the CI owner's page) | **Serves:** the CI owner reading how the weekly capture works | **Topic:** docs

## Motivation

`docs/design/capture-workflow.md` against
`.github/workflows/real-project-capture.yml`:

```text
doc L93    "Warm. bst build <target>"          yml L351: bst … artifact pull --deps all "$TARGET"
                                               (yml L332-341: bst build "finished in 7 seconds", replaced)
doc L152   "weekly … and workflow_dispatch, and on nothing else"
                                               yml L163-173: two crons, 0 3 * * 0 and 0 4 1 * * (monthly → cold)
                                               doc L189 itself: "the monthly cron settled it"
doc L298   contents table: 12 files             yml writes 21 under capture/ — 9 absent:
           (filed as 13; re-counted in round 83, the table named 12 —
            and the list to the right was always 9 names, not 8)
                                               bst-element-logs.tar.gz, capture-outcome.txt, doctor.txt,
                                               bwrap-argv.jsonl, invocations.jsonl, native-trace.head.log,
                                               native-trace.log.omitted, build-traced.log, native-report-traced-only.json
yml ~L741  "Cache health trend across the retained refs" (bga baseline -n 8 + cache-trend)
                                               doc: 0 hits for cache-trend / health
```

The two guards on this document check four phrases and one sentence;
neither reads the workflow's file list or its `schedule:` block —
while `test_capture_ref_patterns.py:17` already parses the yml.

## Required Fix

The doc's steps, trigger sentence and contents table corrected, and a
guard that derives the contents table from
`grep -o "capture/[A-Za-z0-9._-]*"` over the yml and the trigger
sentence from its `schedule:` list — the ref-pattern guard's parser,
reused.

## Out of Scope

- The nine-cut list (doc L127-133) — not re-extracted from the yml
  this round; checked or filed when the guard above lands.

## Acceptance Test

Mutation: add a file to the yml's upload list — the table guard
reds; drop a cron — the trigger guard reds.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** held — all four Motivation rows re-measured true on `c6ccb6b`;
two counts inside row 3 were wrong at filing (the table named 12 files, not
13; the list beside it was always 9 names, not 8), corrected above.

### The gap, before the fix

```text
$ grep -o 'capture/[A-Za-z0-9._-]*' .github/workflows/real-project-capture.yml | sort -u | wc -l
22                            # 21 names + the bare `capture/` directory
# the doc's table parsed the way the new guard parses it, against that set:
yml names: 21   doc names: 12   in doc table, absent from yml: []
in yml, absent from doc table: [bst-element-logs.tar.gz, build-traced.log,
  bwrap-argv.jsonl, capture-outcome.txt, doctor.txt, invocations.jsonl,
  native-report-traced-only.json, native-trace.head.log, native-trace.log.omitted]
crons: ['0 3 * * 0', '0 4 1 * *']
```

Doc L93 said `bst build <target>`; yml L351 runs `bst … artifact pull --deps
all "$TARGET"`, its own comment recording `bst build` "finished in 7 seconds".
Doc L152 said "**weekly** … and on nothing else" over two crons — while doc
L189 already said "the monthly cron settled it". `cache-trend`: 0 hits in the
doc, one step (yml L740) in the workflow.

### The close

Same parse after: `doc names: 21`, `yml names: 21`, both crons named. Fixed:
the warm verb, the trigger sentence (both cadences and clocks, and how the mode
follows the cron), 9 table rows, a conditional note, a cache-trend paragraph.

### Mutations verified red and reverted (8)

Each ran `pytest tests/unit/test_the_capture_doc_reads_its_workflow.py -k
<node>`, asserted present in the file first; every one printed `1 failed, 7
deselected`.

| # | mutation | guard reddened |
|---|---|---|
| 1 | yml: `--mutant-log capture/mutant.jsonl` added to the tracer's flags | `test_it_names_every_file_the_workflow_writes` |
| 2 | doc: a `no-such-file.txt` row added to the table | `test_it_names_nothing_the_workflow_does_not_write` |
| 3 | doc: `Sunday 03:00 UTC` → `Sunday 05:00 UTC` | `test_it_names_every_cron` |
| 4 | yml: `- cron: "0 4 1 * *"` commented out | `test_it_claims_no_cadence_the_workflow_lacks` |
| 5 | yml: `push:` added to the `on:` block | `test_it_names_every_trigger_the_workflow_has` |
| 6 | guard: `_cadence` clock built as `(minute, hour)` | `test_a_cron_becomes_the_words_the_sentence_owes` |
| 7 | guard: `CRON` loosened to `r"(\d+ \S+ \S+ \S+ \S+)"` | `test_a_cron_literal_outside_the_schedule_list_is_not_a_trigger` |
| 8 | guard: multi-name cell truncated with `[:1]` | `test_a_multi_name_cell_yields_every_name` |

Mutation 7 was rejected once first: a differently-escaped loose regex still
matched only the schedule list, so the guard stayed green. Redone as above it
reds on the `env:` cron literal — `assert <re.Match … "0 4 1 * *'"> is None`.

### Acceptance Test

> Mutation: add a file to the yml's upload list — the table guard reds; drop
> a cron — the trigger guard reds.

```text
$ sed -i 's|--argv-log capture/bwrap-argv.jsonl \\|&\n            --mutant-log capture/mutant.jsonl \\|' .github/workflows/real-project-capture.yml
$ python3 -m pytest tests/unit/test_the_capture_doc_reads_its_workflow.py -q
E   AssertionError: the workflow writes these under `capture/` and the
    contents table names none of them: ['mutant.jsonl']
1 failed, 7 passed in 0.07s

$ sed -i 's|^    - cron: "0 4 1 \* \*"$|    # cron dropped|' .github/workflows/real-project-capture.yml
$ python3 -m pytest tests/unit/test_the_capture_doc_reads_its_workflow.py -q
E   AssertionError: the trigger sentence claims a monthly run; the
    workflow's schedule has ['0 3 * * 0']
1 failed, 7 passed in 0.07s

$ python3 -m pytest … -q      # both reverted
8 passed in 0.05s
```

**Deviation:** the nine-cut list stayed Out of Scope. One surface beyond the
Decomposition: the yml's stale "Weekly" comment, fixed in the same commit.
`tests/tiers.py` untouched — the new file measures 0.05s, small tier.
Committed with `BGA_SKIP_SELECTOR=1` (`UX-561`): two guards are red at the
base `c6ccb6b` and neither is this track's — an undeclared skip reason from
`UX-588`, and a `UX-589` row landed inside the README's status-legend table.
