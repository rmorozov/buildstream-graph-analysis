# Round 141 — the jobserver batch, and a real project's LTO hang

Run on 2026-09-24 off main at `ad27b616` (`#286`, round 140), from Ruslan's ask
for every jobserver row plus a freedesktop-sdk build with the jobserver
on. The rows the batch found (`UX-1001` to `UX-1008`) joined it at his
word.

```text
closed   UX-978 UX-906 UX-901 UX-1001 UX-1002 UX-1003 UX-1004 UX-1006 UX-884
filed    UX-1005 (architect-shaped, open) UX-1007 UX-1008
open     UX-905 (needs a quiet box), UX-895 (needs a 16-core host)
index    dev_close_task.py --counts: 969 scenarios, 14 open, 955 closed
spread   dev_touching.py --spread: 33-167 of 607 test files
```

## The fdsdk auto arm hung, and the cause was one level down

The first auto arm (run 35965495279) went quiet on `git-minimal`'s LTO
links. The hang witness showed gcc's `lto1` in `anon_pipe_read` on the
pool's fds with unreaped workers. ninja 1.13.2 names no jobserver in its
help, so the shim wrapped it (`UX-1001`). A local reproduction on gcc
16.2 and 13.3 then placed the cause:

```text
fifo:PATH, 0 tokens                exit 0
--jobserver-auth=3,9 blocking      HANG with 0 or 3 tokens
make 4.3 / 4.4.1 as client         sets the read fd O_NONBLOCK within 4s
```

Every compiler-facing policy now hands gcc `fifo:` (`UX-1006`); make
elements are safe by make's own behaviour (`UX-884`, measured, no guard).

## A shared build root hid the kind

fdsdk's `build-root: /buildstream-build` names no element, so 21 of 25
sandboxes read `unknown_kind`. A recipe `MAKEFLAGS=-jN` is now a promise
(`UX-1003`): 0 to 12 make sandboxes joined, and the build was green.

## No wall reading is possible on these runners

```text
giant.bst      cpu: 4 logical, 2 cores; effective 1.23 at width 2, flat to 8
               pinned --builders 2 x max-jobs 2 vs auto: 235s -> 233s
fdsdk off      EPYC 7763  11592 CPU s  wall 3573   (run 35994560797)
fdsdk auto     EPYC 9V74   8383 CPU s  wall 2978   (run 35994562807)
earlier arms   8964 / 9048 / 11104 CPU s on the same work
```

The runner is two SMT cores (`UX-1002`, `UX-1004`), and two arms started
together landed on different CPU generations. The structural readings
hold (equal work, 12 make and 4 ninja joins, no leaks); the wall verdict
waits on one quiet box (`UX-905`, `UX-895`).

## The census

Four projects, about 2,450 elements: width promised through `MAXJOBS`,
`MAX_JOBS`, project-wide `GOMAXPROCS`/`CARGO_BUILD_JOBS` (`UX-1007`),
and a `go build` with no promise at all (`UX-1008`).

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| architect | opus | architect: shape UX-901 and UX-906 | 70k | 32 | 5.7 m | two rows shaped; lint re-run after the report |
| implementer | sonnet | UX-901 the jobserver behind an import boundary (bounded) | 379k | 294 | 62.7 m | PoolController and Broker read tracer-owned modules; bind vs import left to the session |
| implementer | sonnet | UX-906 the corner cases become a register (bounded) | 84k | 66 | 11.8 m | the policy set derived from the shim's ast |
| verifier | sonnet | UX-901 verifier, UX-906 verifier | 64k | 53 | 10.6 m | full suite plus dev_sizes --check |
| researcher | sonnet | BuildStream sandbox deadlines and bwrap count | 31k | 15 | 1.3 m | claimed several bwrap per element; REAPI batching refutes it, 25 for 23 |
| general-purpose | opus | reproduce the gcc 16 LTO jobserver deadlock | 227k | 40 | 42.3 m | staging gcc 16.2 from the nix cache; the blocking fd pair, not tokens, is the cause |
| architect | opus | architect: shape UX-1005 builders and pool | 55k | 22 | 2.6 m | admission in the shim chosen over an upstream change |
| researcher | sonnet | census of four BuildStream projects for jobserver corner cases | 65k | 24 | 3.4 m | cloning four projects; MAXJOBS and GOMAXPROCS promises found |

The verifier guard paired only a row's first id; one run reading two
tracks is now paired for both (`UX-761`'s guard).
