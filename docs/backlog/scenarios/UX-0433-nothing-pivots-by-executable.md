# UX-433: nothing pivots by executable, because no annotation names one

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 69, running the question library against a two-plane capture | **Serves:** anyone asking which *program* their build spends its time and memory in | **Topic:** viewer

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

## Outcome

_Not started._
