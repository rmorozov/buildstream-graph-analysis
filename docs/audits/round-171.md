# Round 171 - the memory gate reads the cgroup, and four residue rows

Run on 2026-10-07: six product rows merged, `UX-1338` closed with them,
and three Graviton dispatches read the memory rows. `UX-1339` was filed
mid-round and taken into it at the owner's word.

```text
closed   UX-1282 UX-1283 UX-1284 UX-1310 UX-1314 UX-1338 UX-1339
filed    UX-1339 (closed in-round)
index    dev_close_task.py --counts: 1283 scenarios, 6 open, 1277 closed
spread   dev_touching.py --spread: 35-212 of 851 test files
```

## What closed

- `UX-1282`: the memory gate reads the host's cgroup, not the host.
  Disclosure classes C/B, not the Decision's H; the hybrid-host v2 tree at
  `/sys/fs/cgroup/unified` is not read. Graviton memcap completes under a
  20 GB cap at `mem_lines` 240000 (run 37616908079); at 320000 the
  opening width OOMs, filed `UX-1339`.
- `UX-1283`: the pool seed is handed out after the memory gate. The
  memgiant leg gave no reading (runner lost, `UX-1281`); twomemgiants,
  pairs, cap3 read on run 37606960927.
- `UX-1284`: a late memory peak is reserved. Gate unchanged; on Graviton
  the late step is `as`, not lto1 (ratio 4.39).
- `UX-1310`: the decision log names each element's forced auth style;
  `bga/schemas.py` untouched.
- `UX-1314`: the per-element CPU curve samples the sandbox's processes;
  no live bwrap reading here, `unshare` stood in.
- `UX-1338`: no progress leaks into the next test; no deviation.
- `UX-1339`: the opening seed scales to the cgroup's share of MemTotal
  (8 x 20/31 opens at 4), and an over-width tick reads one unread token
  back. memcap at 320000 completes 3/3, `oom_kill 0`, `start 4 max 5`
  (run 37635876457). The withdraw cannot fire before the first END, and
  its counter reaches no report field.

## Lessons

- A 20 GB cap passes at 240000 `mem_lines` and OOMs at 320000: holding
  adds cannot help once the opening width is over the cap, so the seed,
  not a withdraw, carried `UX-1339`.
- The verifier found a leaf-only cap mutation the guard missed: a
  scripted tree must put the cap where the code is meant to walk to.
- One Graviton runner was lost (`UX-1281`) and its leg has no reading.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 171 | implementer | — | UX-1282 | — | — | — | merged | tokens, calls, wall not in the brief |
| 171 | verifier | sonnet | UX-1282 verifier | — | — | — | complete | tokens, calls, wall not in the brief |
| 171 | implementer | — | UX-1283 | — | — | — | merged | tokens, calls, wall not in the brief |
| 171 | verifier | sonnet | UX-1283 verifier | — | — | — | complete | tokens, calls, wall not in the brief |
| 171 | implementer | — | UX-1284 | — | — | — | merged | tokens, calls, wall not in the brief |
| 171 | verifier | sonnet | UX-1284 verifier | — | — | — | complete | tokens, calls, wall not in the brief |
| 171 | implementer | — | UX-1310 | — | — | — | merged | tokens, calls, wall not in the brief |
| 171 | verifier | sonnet | UX-1310 verifier | — | — | — | complete | tokens, calls, wall not in the brief |
| 171 | implementer | — | UX-1314 | — | — | — | merged | tokens, calls, wall not in the brief |
| 171 | verifier | sonnet | UX-1314 verifier | — | — | — | complete | tokens, calls, wall not in the brief |
| 171 | integrator | — | integrator: merge the five tracks | — | — | — | merged | not in the brief |
| 171 | graviton | — | bga-bench run 37606960927: twomemgiants, pairs, cap3 | — | — | — | complete | memgiant leg lost its runner (UX-1281) |
| 171 | graviton | — | bga-bench run 37616908079: memcap at 240000 under a 20 GB cap, latepeak | — | — | — | complete | memcap 3/3 no OOM; the 320000 OOM (run 37606960927) filed UX-1339 |
| 171 | closer | sonnet | closer: ledger, round document, history | — | — | — | complete | tokens, calls, wall not in the brief |
| 171 | architect | — | UX-1339 | 51k | 13 | 3.5 m | complete | share from MemTotal, not headroom; withdraw cannot pass 320000 alone |
| 171 | implementer | sonnet | UX-1339 | 79k | 62 | 29.5 m | merged | worktree guard refused compound shell; PLR0913 moved the share to capped_width |
| 171 | verifier | sonnet | UX-1339 verifier | 55k | 15 | 16.2 m | complete | leaf-only cap mutation survived; add relabelled withdraw |
| 171 | implementer | sonnet | UX-1339 fix loop | 87k | 15 | 7.5 m | merged | see round-171 |
| 171 | graviton | — | bga-bench run 37635876457: memcap at 320000 under a 20 GB cap | — | — | — | complete | start 4, 3/3, oom_kill 0 |
