# Walk, seed 3 — round 114

`UX-685`'s third seeded walk: the process storm, spine on, cold then
incremental, real Chrome. Base `5bcd026d`, 2026-09-12. Driven on the
reporters' model (174k tokens, 59 calls, 8.4 m); judged here.

```text
$ python3 tools/dev_scenario.py --seed 3
area tools · role R1 (the local optimizer) · Plane 2 spine on · cold ·
current contract · population 0 · reader real Chrome
```

```text
seed         3
capture      20260912T114117Z (cold) then 20260912T114132Z (incremental),
             examples/08-process-storm all.bst · 3 elements · cold 2003
             processes traced (2003 matched), incremental 0 · Plane 1 and
             Plane 2 present on the cold run; incremental Plane 1 only
             (0 rebuilt, "Session: 2"). Recipe deviation: bst's default
             disk reserve exceeds this box's free space, so the isolated
             cache is a `bst --config` with a 3G quota, not XDG_CACHE_HOME.
answer key   1. storm.bst is execution-bound: one sandbox runs 2000
                sequential `cat /dev/null` execs — a process storm, not a
                compile
             2. Plane 2 should see ~2000 dynamically linked cat/sh
                processes, the cost in exec overhead, no heavy binary
             3. the cached rebuild: 0 rebuilt, 100 % hit, no invented
                findings
per plane    1 cold | "This build is chain-bound ... the top 1 are worth
             3.5s (55% of the build)" | match (1) | yes | none
             2 cold | "storm.bst: holds 100% of the critical path ... runs
             at only 0.75 cores busy ... 91% of its measured CPU is one
             binary, `cat` (2000 process(es), 3 CPU s)" | match (1, 2) |
             yes | none
             1 incr | "Cache hit ratio: 100% (2 cached, 0 rebuilt) - the
             cache did most of the work" | match (3) | nothing to fix | none
             2 incr | "NO USABLE JOIN: Plane 2's element attribution is
             unreliable. no process carried an element tag at all ...
             Nothing is recommended" | partial (3) | honest refusal | the
             wrong absence named — UX-817
page         headline right on both (`chain_bound` storm.bst cold;
             `inconclusive` incremental) · the macro findable: storm.bst
             leads the findings and the whatif · cold 595 controls in 27
             classes over 60 sections, incremental 302 in 24 over 41 · one
             instance per class driven, 2 differ from their label: the
             Copy buttons (clipboard refused under CDP: "Document is not
             focused" — a driving artefact, not filed) and "Open timeline
             in Perfetto" (below)
perfetto     `bga timeline` refuses a run dir and names the snapshot dir
             (correct; the recipe's `<run>` shorthand invites it). On the
             snapshot: 2011 slices, 2002 flows, 1971 counters on 2019
             tracks. 16 of 18 canned queries answered with `--element
             storm.bst` (2 legitimately empty); `process-storm` returned
             {storm.bst, 2003 processes, 11.0 s} — the count-and-duration
             pairing no other surface publishes; `element-commands` gave
             40 untruncated argv rows. 2 errored — UX-818.
findings     1. `bga correlate` on the 0-rebuilt run names attribution as
                the absence: "no process carried an element tag at all",
                when nothing was built to carry one. Nearest row UX-66;
                UX-388's rule has not reached the join → UX-817
             2. `concurrency-curve` and `were-the-cores-busy` error
                "syntax error near '{'" with `--element` — the library
                UX-432 ran, two questions of it broken by the fill → UX-818
             3. the export's "Open timeline in Perfetto" fetched
                `file:///…/%22data:application/gzip;base64,…%22`: the
                `#bga-trace` node holds a JSON string and `traceUrl()`
                returns it unparsed, quotes and all (bga_view.py:1348,
                sections.js:611); nearest row UX-299 → UX-819
rows added   1 — `test_the_journey_has_an_answer_key.py` gains the join's
             half of UX-388's rule as a recorded case: the warm run's
             `correlate` recommends nothing, and the row names UX-817's
             sentence as the gap it will flip to
friction     pinning finding 3 took three driver scripts — mocking
             `window.open`, then reading a 196 KB observe result in full —
             before the quoted URL was visible; the disk-tight bst config
             worked first time.
```

## Judging

Three deviations are the tool's and are filed; two are the walk's own
and are not. The join's refusal (1) is `UX-388`'s class one surface
further — the page and the text report say which absence it is, the
join does not. The query errors (2) and the quoted data: URI (3) are
defects behind guards that never read the case: `UX-432` ran the
library without `--element`, and `UX-314`'s served test never saw an
export's node as a URL. All three are carried, named, into 0.4.1's
release row. `bga timeline`'s refusal and the clipboard error are the
recipe's shorthand and CDP's focus, not the tool.
