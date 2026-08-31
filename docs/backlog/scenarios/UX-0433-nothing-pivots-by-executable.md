# UX-433: nothing pivots by executable, because no annotation names one

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 69, running the question library against a two-plane capture | **Serves:** anyone asking which *program* their build spends its time and memory in | **Topic:** viewer

## Motivation

The question a reader wants of Plane 2 is a pivot: **cpu, memory and
wall time per executable, argv stripped** — how much of this build is
`cc`, how much is `ld`, how much is the shell. Nothing in the library
answers it, and no query could today.

The library's nearest is `element-commands`, which groups by `s.name`:

```sql
select s.name as command, sum(s.dur) / 1e6 as ms
from slice s where s.category glob '*native-process*' ...
```

`s.name` is the **whole command line**. On the audited capture that is
14,424 near-unique strings, so grouping by it yields one row per
invocation, not per program. Run against that capture, the top row was:

```text
command                                    ms
/usr/bin/python3 setup.py build_ext --   1584.7
```

one invocation, not the program's share of the build.

There is no other key to group by. `PLANE2_ANNOTATIONS`
(`tools/bga_timeline.py:101-148`) carries `element`, `src`, `cpu_us`,
`max_rss_kb`, `exit_status`, `exec_chain`, `read_bytes`,
`written_bytes`, `major_faults`, `involuntary_switches` — and no
executable path. `debug.cmd` was deliberately removed by `UX-333`, for
a reason that still holds: interning the full argv once as a name cost
+0.6% where keeping both cost +75.1%.

So the gap is not a missing query. **It is a missing annotation**, and
`UX-333`'s measurement is the reason it must be a *new* one rather than
`debug.cmd` restored — an executable path is short, low-cardinality and
interns almost for free, which is exactly what the full argv was not.

Related, from the same run: `which-run-is-this` returned `[NULL]` for
`project`, `cpus` and `builders`, and three Plane 1 questions each
returned a `[NULL]` element row carrying the whole build's duration,
because the `bst build all.bst` wrapper span is emitted with the
element-task category and no element annotation. Both are separate
rows if they survive their own measurement.

## Required Fix

- **Annotate the executable.** `debug.exe`, the program path with argv
  stripped, on every Plane 2 slice — measured for size against
  `UX-333`'s figures before it lands.
- **The pivot questions**, once there is a key to pivot on: time, cpu
  and peak RSS per executable, and per executable within one element.
- **The trace dictionary carries it** (`docs/spec/trace-dictionary.md`)
  and `test_the_questions_ask_what_the_trace_answers.py`'s contract set
  grows with it, in both directions.
- Verify with `tools/dev_perfetto_queries.py` against a capture with
  both planes — the pivot returning rows is the acceptance, and
  `UX-432` exists so that is one command.

## Out of Scope

- **Restoring `debug.cmd`**: `UX-333` measured its cost and the
  decision stands; this adds a short key rather than reinstating a long
  one.
- **The `[NULL]` element rows and the null run identity**: named above
  so the measurement is not lost, but each needs its own item.
- **Deciding the executable's basename versus its full path** — a
  question for the item, since `/usr/bin/cc` and `/usr/lib/gcc/…/cc1`
  are different answers to "which program", and the pivot is only
  useful if that is settled deliberately.

## Acceptance Test

```bash
bga timeline /path/to/snapshot -o /tmp/two.pftrace
python tools/dev_perfetto_queries.py /tmp/two.pftrace
```

The pivot questions answer with one row per program rather than one per
invocation, and the trace's size against the same capture without the
annotation is pasted beside `UX-333`'s +0.6% / +75.1%.

## Outcome (round 70, 2026-08-30) — 🟢 Done

### The key

`debug.exe` on every Plane 2 slice: argv[0], **the path as it was
exec'd**. `s.name` is the whole command line — 14,424 near-unique
strings on the audited capture — so `group by s.name` answers one row
per invocation and never one per program, and nothing else on the slice
named an executable.

**The path, not the basename**, which is the decision the item asked to
be settled deliberately. `/usr/bin/cc` and a compiler's own
`/usr/lib/gcc/x86_64-linux-gnu/12/cc1` are different answers to "which
program"; a query can take a basename from a path (`substr` after the
last `/`) and nothing can recover a path from a basename. Measured, the
distinction costs 3.2 points of trace size and buys a distinction that
cannot be reconstructed.

### What it costs, against `UX-333`'s figures

Rendered twice from the same 1,202-element two-plane snapshot (14,424
process slices), once with the annotation and once without:

```text
                                     trace bytes   over no annotation
  no annotation                          486,336
  debug.exe, basename                    531,322   +9.2%
  debug.exe, the path as exec'd          546,877   +12.4%
```

and, on a fixture whose processes all run **one** program, +1.1% — the
best case, recorded so the 12.4% is not read as the only number.

`UX-333` measured the full argv at **+75.1%** kept beside the interned
name, and +0.6% for the name alone. This sits between them and much
nearer the cheap end, which is the shape the item predicted: an
executable path is short and a build uses tens of them against tens of
thousands of command lines. The trace remains an eighth of
`TRACE_BUDGET_B` at this scale.

### The pivot, run

```console
$ python tools/dev_perfetto_queries.py two.pftrace
  cost-by-executable   Plane 2          6 row(s)
  ...
errors: 0/15  []

$ trace_processor_shell -q cost-by-executable.sql two.pftrace
"exe","runs","wall_seconds","cpu_seconds","peak_rss_kb"
"/usr/lib/gcc/x86_64-linux-gnu/12/cc1",1202,60.099998,24.040000,1024
"/usr/bin/make",1202,60.099998,24.040000,1024
"/usr/bin/ld",1202,60.099998,24.040000,1024
"/bin/sh",1202,60.099998,24.040000,1024
"/usr/bin/cc",1202,60.099998,24.040000,1024
"/usr/bin/as",1202,60.099998,24.040000,1024
```

Six rows from 7,212 process slices. `element-commands` on the same
trace, for contrast, answers per invocation:

```text
"command","ms"
"/usr/bin/ld -c f1.c",50.000128
"/usr/bin/as -c f2.c",50.000128
"/usr/bin/cc -c f5.c",50.000128
```

Fifteen questions, **no errors**, and the two empties explained by the
capture rather than by the query.

### One query shipped, not two — and that is `UX-368`'s rule working

The draft had `executables-in-element` beside it, the same pivot inside
one sandbox. It is **not** in the library, because
`test_every_library_query_is_reachable_from_a_finding` reddened: there
are 22 claims in `bga/provenance.py` and 20 already carry a query, and
neither spare is about what an element ran. A question no finding
points at is a question nobody arrives at.

So it was dropped rather than added unreachable, the SQL is preserved
in **`UX-448`** with the decision it needs, and
`test_the_element_scoped_twin_is_not_in_the_library` holds it dropped
until then.

`cost-by-executable` is reached from `time-concentration` — the claim
that a few elements hold most of the time, whose next question is what
those elements were *running*. "Which elements" is still one click
away: `diagnosis` points at `element-time`, the same query.

### The eight mutations

```text
P1 no exe annotation at all            red: key_is_declared, every_slice_carries_it,
                                            it_is_not_the_slice_name
P2 the basename, not the path          red: argv_is_stripped_and_the_path_is_not,
                                            every_slice_carries_it
P3 an empty command is a program       red: a_record_with_no_command_carries_no_key
P4 argv is not stripped                red: argv_is_stripped, every_slice_carries_it,
                                            it_is_not_the_slice_name
P5 the pivot groups by command again   red: one_row_per_program, runs_and_seconds,
                                            peak_rss_is_a_maximum
P6 peak rss is summed                  red: peak_rss_is_a_maximum_and_not_a_sum
P7 a null executable is a program      red: a_slice_with_no_executable_is_not_a_program
```

All discriminate. **P1 needed a second attempt** and it is worth the
record: removing only the *fill* left the declaration in place, so
`_plane2_annotations` raised `KeyError` and the guard reported two
errors rather than a red. A mutation has to be the coherent change a
round would actually make — declaration and fill together — or it tests
the crash, not the claim.

The clauses that decide run the **shipped SQL** against a SQLite `slice`
table, the instrument `UX-434` built, so the pivot is exercised where CI
can run it. `ROWS` deliberately gives one program two invocations at
different peak RSS, which is what tells `max()` from `sum()`.

### Documents

`docs/spec/trace-dictionary.md` carries `exe` with the path-not-basename
rule; `test_the_questions_ask_what_the_trace_answers.py`'s contract set
grew with it in both directions, which is what kept the two honest.

### Deviation from the Required Fix

One: **one pivot question, not two**, for the reason above. The item's
own fourth bullet — verify with `dev_perfetto_queries.py` against a
two-plane capture — is what surfaced it, since the second query would
have shipped unreachable.

### The suite

```console
$ make lint
All checks passed!

$ make test
5388 passed, 26 skipped, 1 warning in 266.97s (0:04:26)
```

The committed fixture's `analyze.json` was regenerated in the same
commit: the analysis embeds `trace_query` per finding, so re-pointing
`time-concentration` left the fixture asserting the old mapping.
`test_a_finding_reaches_the_timeline.py` caught it, which is the guard
working — a map and a cached copy of it are two places one fact lives.
