# Round 171 - the memory gate reads the cgroup, and four residue rows

Run on 2026-10-07: five product rows merged, `UX-1338` closed with them,
and two Graviton dispatches read the memory rows.

```text
closed   UX-1282 UX-1283 UX-1284 UX-1310 UX-1314 UX-1338
filed    UX-1339
index    dev_close_task.py --counts: 1283 scenarios, 7 open, 1276 closed
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

## Lessons

- A 20 GB cap passes at 240000 `mem_lines` and OOMs at 320000: the
  opening width is the next row (`UX-1339`).
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
| 171 | graviton | — | bga-bench run 37616908079: memcap under a 20 GB cap | — | — | — | complete | OOM at mem_lines 320000, filed UX-1339 |
| 171 | closer | sonnet | closer: ledger, round document, history | — | — | — | complete | tokens, calls, wall not in the brief |
