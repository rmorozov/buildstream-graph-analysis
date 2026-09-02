# UX-111: the reports were each checked alone, never against each other

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — (a cross-cutting audit, not a feature) | **Topic:** analysis

## Motivation

`bga` prints six report surfaces across three planes — `analyze` (and
its five section subcommands), `correlate`, `compare`, `cache-trend`,
`cache-logs`, and `capture report`. Each was written by its own task,
reviewed against its own acceptance test, and never read beside the
others.

Rendered side by side against one real freedesktop-sdk build, they do not
read as one tool. Some of the differences are cosmetic; four of them are
numbers or instructions a reader can act on wrongly.

## Required Fix

Render every report against the same real capture, read them together,
and fix what a reader could misread. Specifically:

1. **A number in one unit must not be labelled with another.** The
   attribution block prints `Execution On Chain Us` beside a value in
   seconds; the occupancy block prints slot-seconds with the same bare
   `s` as wall-clock, so a 3261s build reports `8626.73s` of idle.
2. **An instruction printed to a stuck user has to run.** The
   missing-file hint names `tools/<script>.py` paths that are not on
   `PATH` and carry no `+x` bit.
3. **Every report says which run it is** (`UX-95`'s rule, applied to
   Plane 1 only) and **which report it is** (Plane 2's has no banner).
4. **The same sentence is not printed four times.**
5. Smaller consistency: one banner width, one plural convention, task
   citations in trailing parentheses, no column that truncates a name
   without saying so, no share that renders a nonzero quantity as `0%`,
   no column a reader cannot decode from the report itself.

## Out of Scope

- Changing what any report *concludes*. This is about how the same
  conclusions are rendered.
- The JSON schema. Every fix below either leaves it alone or adds a
  field; nothing published is removed or renamed.

## Acceptance Test

All six surfaces rendered from one real capture read as one tool: same
banner, same identity discipline, no label naming a unit the value is not
in, and no instruction that fails when pasted. The properties are held by
tests rather than by having been looked at once.

---

## Fix Implemented

Ten fixes, from rendering all six surfaces against the freedesktop-sdk
capture published as run `32223468993`.

### Four a reader could act on wrongly

**`Execution On Chain Us  3257.85s`.** The attribution categories carry
the `_us` suffix of their schema field, and titling them naively put
"microseconds" in the label of a value printed in seconds. Dropped in the
renderer, not the model, where the suffix is part of the contract.

**`Idle No Tasks  8626.73s` in a 3261-second build.** Correct — the
buckets are slot-time, and four builders spend four slot-seconds per
second — but printed with the same bare `s` as every wall-clock figure in
the report, so the honest number reads as an impossible one. Now:

```text
  Buckets below are task slot-time (occupancy), not CPU time, and are measured
  in slot-seconds - a build of H seconds on N builders has N*H of them to spend:
  Useful                4418.15 slot-s
  Idle No Tasks         8626.73 slot-s
```

**A hint that does not run.** A user with a partial run directory got:

```text
  graph.json: tools/bst_show_to_graph.py <project_dir> <targets...> graph.json
```

which fails with `Permission denied` — the scripts are not executable and
not on `PATH`. `bga` has had front-door aliases for all of them since
`UX-67`. The hint now names those, and its test asserts against the alias
table rather than against a string, so a renamed alias fails the test
instead of shipping a broken instruction.

**`1.0s toll of 594.0s (0%)`.** A share under 1% rounded to `0%` beside a
toll that was visibly paid. Now `<1%`, and `0%` means zero.

### Two about identity

`UX-95` established that a report names the identity of the run it
describes, and it reached Plane 1 and `bga compare` only. `bga correlate`
had no `Run:` line at all, so a join could not be filed or compared a
week later — even though Plane 1's analysis, its own input, carries both
halves. It now prints them, and prints *nothing* when its inputs carry no
identity rather than inventing one.

Plane 2's report had **no banner at all** — it opened on `Processes
traced:`, so a native report pasted into an issue was unidentifiable as
one. It now opens `Native Build Trace (Plane 2)` and closes with the same
rule as every other report, so a truncated paste is visibly truncated. It
claims no run id: that hash is computed from Plane 1's declared graph and
a native report has no access to it.

### One about repetition

`bga correlate` printed four `split-candidate` findings, each ending in
the identical three-sentence caveat — **1300 characters saying one
thing**:

```text
[info] split-candidate: components/openssl.bst holds 18% … Evidence, not a
recommendation: a split's shape is a human decision, and this run's history
carries no invalidation blast for it …
[info] split-candidate: components/_private/cmake-stage1.bst holds 43% … Evidence,
not a recommendation: a split's shape is a human decision, and this run's history
carries no invalidation blast for it …
    (twice more)
```

The caveat moved to its own `rationale` field and the renderer groups
findings that share one:

```text
[info] split-candidate: components/openssl.bst holds 18% of the critical path and
runs 5.52 concurrent work processes inside one element (6157 of them)
  ...and components/_private/cmake-stage1.bst holds 43% … (4586 of them)
  ...and components/python3.bst holds 18% … (3885 of them)
  ...and components/doxygen.bst holds 14% … (402 of them)
  That is work BuildStream could have scheduled as separate cacheable elements.
  Evidence, not a recommendation: a split's shape is a human decision, …
```

The **JSON is unchanged in shape**: still one entry per element, because
that is what a CI consumer keys on. Only the text groups.

### Three about consistency

- **One banner width.** `cache-trend` was 78 columns where every other
  report is 60 — two reports in one issue looked like two tools.
- **`components/_private/cmake-st`.** The developer-tax column truncated
  element names at a fixed 28 characters, from the *head*, so
  `components/_private/cmake-stage1.bst` and
  `components/_private/git-minimal.bst` became two names that differ only
  past the cut with nothing saying they were cut. The tail is the half
  that identifies an element, so the head gives way: `…s/_private/cmake-stage1.bst`.
- **A citation mid-sentence.** Every note in this tool cites its task in
  trailing parentheses; one line put `UX-61:` in the middle of the
  primary sentence a reader has to understand before any number below
  means anything.

### Two about a reader who cannot decode the output

`cache-trend`'s `churn` column printed `0+25r` and defined it nowhere in
its own output. It now carries a legend, and only when the `+Nr` form
actually appears.

`cache-logs`'s developer-tax table printed a `cause` header with an empty
column on every run — the cause needs `--graph` *and* an element that
rebuilt more than once, and an empty column reads as "no cause found"
rather than "no cause could be looked for". The column now appears only
when it has something in it.

And `bga --help` filed `capture`, `cache-logs` and `baseline` — two whole
analysis planes and a band-comparison — under a heading that called them
"capture & conversion", so a reader scanning for Plane 3 skipped the
section that has it.

### The one item the first pass did not finish

Required Fix item 3 says **every** report names the run it is about. The
first pass gave that to `bga correlate` and to the Plane 2 report and
stopped, and the omission was not recorded either — so this is a
follow-through on the same task rather than a new one.

`bga cache-trend` identifies its runs by directory basename, and — unlike
both of its siblings — checks nothing about whether they belong in one
series. `bga compare` refuses a mismatched pair with exit 6; `bga
baseline` refuses a set that is not homogeneous before it even fetches.
The third multi-run command accepted anything:

```text
run                             hit  built  cached     xfer  /artifact   churn
03-32064333551/run              72%     25      65        -          -       -
02-32113933158/run              72%     25      65        -          -   0+25r
u110/run06                       0%     11       0        -          -       -
00-32177690506/run              72%     25      65        -          -       -

Every trended metric on the newest run sits inside the band its trailing window describes.
```

Three freedesktop-sdk runs with one `examples/06` run among them — a
different project, 0% hit ratio, 11 elements against 25 — and a clean,
confident verdict computed over a band containing it. Exit 0.

**The obvious key was the wrong one.** The other two commands key on the
run-identity hash, and reaching for it here would have been consistent
and wrong: that hash includes `project_git_commit`, so it changes on
every commit, and a cache-health trend *is* a series across commits.
Keying on identity would have refused the only kind of trend this
command exists to produce — which is the sort of thing that only shows up
when the manifest is read rather than assumed.

The subject of a series is what does **not** vary along it: the project
and its targets. That is what `_subject` compares, and the commit is
explicitly excluded with a test that says so.

Now:

```text
NOT COMPARABLE: 2 different projects or target sets in this series - these are not
repeated readings of one thing, so no band over them describes anything. The rows
above are each real readings of their own run.
  03-32064333551/run           . components/libxml2.bst
  02-32113933158/run           . components/libxml2.bst
  u110/run06                   examples/06-macro-micro-optimization all.bst
  00-32177690506/run           . components/libxml2.bst
```

Exit **6**, the same code `bga compare` uses for a pair it will not
compare, so a CI job cannot read a refused verdict as a healthy cache.

Two deliberate differences from `compare`, both because the reports are
not the same shape:

- **The rows still print.** `compare` refuses *before* printing, because
  its numbers are derived from the mismatched pair and are arithmetically
  correct and meaningless. Here every row is a reading of its own run and
  stands alone; only the band was cross-run, and only the band is
  withheld.
- **One reason is given, not two.** A heterogeneous series shorter than
  the window would otherwise report both "no verdict: too few runs" and
  "not comparable", which invites fixing the wrong one.

### What was checked and left alone

- **Positional `directory` vs a flag.** Every subcommand takes the run
  directory positionally; `-r`/`-d` on `analyze` are `--replay` and
  `--diagnostics`. Consistent already; it read as an inconsistency only
  until the `--help` was checked.
- **`Capacity: 4.0 (source: detected_host_cpu_count)` in the occupancy
  block, against the floors block certifying on `builders`.** Two
  genuinely different quantities, each with a note saying which it is.
  Renaming either would make one of them wrong.

Tests: 8 in `tests/unit/test_cache_trend_series_subject.py` for the
follow-through above, including the one that pins the commit *out* of the
subject, and 11 in `tests/unit/test_report_consistency.py`, which is a
*cross-report* test file by design — the properties it holds are about
consistency between surfaces, which is exactly what having one test file
per report could not check. Three existing tests asserted the old
wording; each was updated to assert the property rather than the string
(the hint test now checks the alias table, the occupancy test checks the
slot-second unit, the granularity test checks the hedge is carried).
Suite: 1409 → 1420 → 1428.

## Verification Log

Done 2026-08-19. Every defect above was found by rendering the real
thing: `analyze`, `graph`, `floors`, `replay`, `utilisation`,
`diagnostics`, `correlate`, `compare`, `cache-trend`, `cache-logs` and
`capture report`, all against the freedesktop-sdk capture from run
`32223468993` and its Plane 3 log tree, read side by side rather than one
at a time.
