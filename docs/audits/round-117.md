# Design round 117: the jobserver is a mode

Run on 2026-09-14, after round 116 merged. A design round (§6a). The
user asked for the full jobserver on `UX-679`'s spike and named five
things to consider: a pinned element is never overridden to `-j1`,
because a pin can work around a native build system's defect; a
load-average approach, because `make` sizes its jobs once and never
recomputes; the propagation must not enter BuildStream's cache key nor
split artifacts between modes; multithreaded linkers oversubscribe,
LLVM 22 speaks the jobserver and older toolchains need a safe default;
and the corner cases and killer features missed. One researcher read
the tree and the installed BuildStream; the argument is Direction 20;
the filings are `UX-841` to `UX-852`.

## What exists today

- The spike's mechanism: a FIFO with `N-1` tokens, the shim's
  `--setenv MAKEFLAGS --jobserver-auth=<fd>,<fd>` spliced into `bwrap`'s
  argv after BuildStream's options; two guards on the shim, none on
  the tracer's lifecycle (`UX-679`'s own Outcome).
- The key: BuildStream 2.8.0 composes the element environment at load
  time and folds it minus `environment-nocache` into the key
  (`element.py:2319-2339`); the shim's variable never passes through
  it; the shipped plugins nocache `JOBS` (cmake, meson) and `MAKEFLAGS`
  (autotools, make). No `%{full-key}` comparison exists in the tree.
- The pin the spike broke: `examples/06`'s `core.bst` is `notparallel`
  and capture b ran it at peak concurrency 4.
- The toolchain here: GNU Make 4.3, ninja 1.11.1 with no jobserver
  client, cargo 1.94, cmake 3.28, lld 18.1, gold 1.16, gcc 13.3,
  clang 18, no mold, no `/proc/pressure`.
- The analysis: `pinned_elements`, peak RSS per element, busy cores
  from `/proc/stat` and `load1` in the host sampler, slack and
  criticality per element; `max_jobs_advice` has no pinned rule.

## The six arguments, in one line each

1. A pin is read from BuildStream's own argv (`-j1` in the composed
   `MAKEFLAGS`/`JOBS`) and never joined; the spike's per-kind
   `JOBS: ''` is withdrawn.
2. The load average is the wrong signal and `make -l` the wrong
   mechanism; the pool moves — the server writes and reads its own
   tokens on busy cores at 250 ms and PSI where present.
3. The key is safe by construction, and a guard compares `%{full-key}`
   both ways and reuses an artifact across modes.
4. A tool that will not read the pipe holds `K` tokens through a
   bind-mounted `PATH` wrapper (`--threads=K`); one that does gets the
   auth passed through; the policy table is measured at capture.
5. Leaks are audited against the hook's process exits; the auth style
   follows `make`'s version; `bst --builders` composes with the pool;
   memory is a second resource.
6. The analysis feeds the scheduler: proxies granted by slack, memory
   from the plan's peak RSS, a token ledger in Plane 2 with two shares.

The user's point 2 was challenged on its premise — under a jobserver
`make` re-reads the pipe at every job start — and upheld on its
consequence, a fixed pool is blind. Point 3 was found already true for
the four shipped kinds and unguarded for a custom plugin. The bar is
round 112's: the mode is supported when a compile-bound capture's wall
moves; `examples/06` cannot show it and `UX-848` adds the example that
can.

## Filed

`UX-841` to `UX-852`, twelve rows in three stages: the pin rule, the
environment table, the wrappers, the FIFO and key guards and the
capture option (stage 1); the dynamic pool, the leak audit, the ledger
(stage 2); proxies by slack and memory (stage 3). Shapes derived: eight
mechanical, four judgement.

## Agents

One run — a `researcher` on `sonnet` over the tree, the installed
BuildStream and plugins, and the toolchain on this box. The row is in
the ledger.

| | |
|---|---|
| researcher | 1 run, five answers with citations; 82k tokens, 60 calls, 12.1 m |

## Standing

- Round 116 merged as PR #225; review 23's three filings stay open.
- `bst` refuses a direct invocation in this sandbox (`stdout … O_NONBLOCK`)
  and answers through a subprocess heredoc; the `%{full-key}` guard
  will need that path here and a plain one in CI.
