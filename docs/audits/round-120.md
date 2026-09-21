# Round 120 — a 16-core field capture: the pool that never grew, the recipes that never joined, and six things the page got wrong

Run on 2026-09-15, after round 119 merged. Eight rows filed from one
field capture and eight closed, as seven `implementer` tracks behind
seven `verifier` reads on `sonnet`, four `researcher` reads before the
filings, the pull request open from the first green gate.

## The premise

The user ran the merged tool on a 16-core, 32 GB host with `--builders
16 --jobserver auto` on a project where llvm sits on the critical path,
and read eight things off the page. Four `researcher` reads on `sonnet`
ground-truthed each against the code before anything was filed: the
pool opened with a ceiling of 1 and could never grow (`resolve_jobserver_
ceiling` conflates the seed with the ceiling; `_handle_underload` never
passes `pool < ceiling - 1` at 0); manual-kind recipes spending `JOBS`
fall through `kind_job_env` as `unknown_kind`; swap is sampled and
folded into a verdict but never published or found; the capacity
recommendation's CPU constraint is unclamped (the fixture recommends 16
on 8 cores); `main table { display: block }` beats `[hidden]`; the
density strip ticks p50 and p95 only; the section renderer never
classifies an object value; the hook drops relative opens.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-858` `UX-859` `UX-862` `UX-863` `UX-864` `UX-865` | mechanical, disjoint surfaces: the ceiling and seed, the `JOBS` env join, the twin's CSS, the strip's ticks, the map table, the hook's cwd |
| 2 | `UX-860` `UX-861` | judgement: a schema column and a finding each - the session's own |

## What closed

| row | what landed |
|---|---|
| `UX-858` | the ceiling is the host's capacity and the seed is cores minus builders, capped at ceiling minus 1; the pool grows from the seed; `seed` recorded beside `ceiling` |
| `UX-859` | a table-less kind whose sandbox env carries `JOBS` joins under `jobs_env`, and the ninja probe runs for any `JOBS`-carrying sandbox; five guards drive the real gate |
| `UX-860` | `swapped_out` published per overcommitted window; `swap-observed` names the windows' span, the pages and the elements building; UNREACHABLE in the census, no committed capture swaps |
| `UX-861` | a CPU-bound `recommended_builders` clamped to the host's cores at the constraint row, `clamped_from` beside it, the sentence names the bound; the guide's 4-core example rewritten |
| `UX-862` | `main table:not(.twin-table)`, so the twin hides on screen; a Chrome case reads the computed display |
| `UX-863` | the strip ticks every mark its twin lists, labels at p10, p50, p90 and p99 dropped on collision by a character-width gap; NaN ticks and a merged-name selector fixed on the way |
| `UX-864` | `renderSection` classifies an object value and routes a true map to the filter-and-sort table; records stay pairs; `by_binary` reads Binary and Count, `wall_clock_share_us` Task and Duration with element names |
| `UX-865` | the hook joins a relative open to its cwd (an atomic generation, a per-thread cache), counts dirfd opens and join failures, the OPENS header carries both |

## The verifiers found

- `UX-858`: HOLD - the no-builders seed had moved from 2 to 3 on four
  cores without the Outcome owning it, and `--builders 0` seeded the
  pool at the ceiling; capped and owned, re-check PASS.
- `UX-859`: HOLD - the ninja probe still ran for cmake and meson only,
  so a manual `-G Ninja` recipe would have run ninja at cores + 2
  outside the pool, and no test drove the real gate; widened with five
  guards through it, re-check PASS.
- `UX-860`: HOLD - the macro_micro export ran 230 B over its bound;
  measured both sides, raised, re-check PASS.
- `UX-861`: PASS; the guide's illustrative 4-core block read wrong under
  the clamp (CPU binds at 4, not the graph at 6), rewritten at merge.
- `UX-862` and `UX-863`: PASS; a merged edge tick's flush alignment has
  no guard, left for a later row; a pasted size figure did not
  reproduce on the verifier's checkout (path-dependent).
- `UX-864`: PASS; the gate's record clause was dead against every
  shipped section, a case added at merge; the full suite then reached
  three guards the touching sweep never selected (the shape census,
  the 1500-line ceiling, the page's published keys), fixed in a second
  round and re-checked.
- `UX-865`: HOLD - a real-dirfd `openat` joined against the cwd under
  mutation with nothing red, a `getcwd` failure dropped the open
  uncounted, and the cwd cache was a plain global two threads could
  race; all three closed, re-check PASS.

## Agents

19 runs, every one a row in the ledger: four `researcher` reads before
the filings, seven `implementer` tracks and eight `verifier` reads (one
row verified twice, after its second round), all on `sonnet`. Five
tracks were resumed once each (`UX-858`, `UX-859`, `UX-860`, `UX-864`,
`UX-865`); four verifiers held and re-checked to PASS.

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| researcher | 4 | 321k | 165 | 26 m |
| implementer | 7 | 5758k | 2137 | 697 m |
| verifier | 8 | 934k | 430 | 186 m |

`UX-858` and `UX-862`+`UX-863` were over a million tokens each: the
first for two resumes over a three-file causal chain, the second for
two rows in one track and the label-collision derivation.

## The gate

| run | head | result |
|---|---|---|
| 0 | `ede1ce6f` | green, 8753 - pushed; PR #230 opened |
| 1 | `004b377d` | red, 4: `UX-864`'s merge reached the shape census, the 1500-line ceiling and the page's published keys - guards its touching sweep never selected |
| 2 | `95e93540` | red, 2: the capability census enumerates the hook's interposed symbols and `UX-865` added the cwd pair; the capped map table's header relabel had wiped the §3d quantity filter (`UX-864`) - both folded into their rows |
| 3 | the close | see the pull request |

## The pair the round was for

`UX-858`'s acceptance, run by the session on a quiet box after the
tracks finished: `examples/11-serial-giant` with `--builders 4` on four
cores, builders equal to the cores, the user's shape - the command that
opened at ceiling 1 with an empty pool before this round.

```text
Verdict: IMPROVED  (total duration -39.79s, -13.4%, 296.26s -> 256.47s)
  giant.bst: -41.00s (291.30s -> 250.30s)
```

| reading | off | auto |
|---|---|---|
| `jobserver` context | - | ceiling 4, seed 0 |
| ledger | - | 1024 rows, 3 `add`, pool 0 to 3 |
| `giant.bst` `peak_work_concurrency` | 2 | 4 |
| `giant.bst` measured-process span | 76.66 s | 39.08 s |
| `giant.bst` `cc1` CPU | 132.1 s | 130.2 s |
| `giant.bst` wall (Plane 1) | 291.30 s | 250.30 s |
| total | 296.26 s | 256.47 s |

The first `add` came at `busy 1.051 < capacity - 1`: the giant alone
on its implicit token, the other three builder slots idle, and the pool
grew to the three tokens the machine had. The span moved by x 0.51
against the 2/4 the width predicts.

## Standing

- On the user's host the same fix reads: 16 builders on 16 cores opens
  at ceiling 16, seed 0, and llvm alone on the critical path grows into
  the cores the other builders leave idle. That number is still to be
  measured there; this box's scaled reading is above.
- The user's manual-kind recipes that spend `${JOBS}` now join
  (`jobs_env`), and a manual recipe generating Ninja is probed like a
  cmake one.
- Swap is a finding; the capacity figure never exceeds the cores; the
  twin hides; the strip and its table agree; the two big maps are
  tables with filters; a relative include path counts as read.
- Left for a later row: a merged edge tick's flush alignment
  (`UX-863`'s `~=` fix reddens no guard on its own).
- Review 24 came due at the close (28 rows closed since review 23,
  bound 25) and ran on the guides this round moved: `--jobserver-seed`
  and `seed` undocumented in `cli.md` (`UX-866`), the context map's
  stale open label (`UX-867`), and the merged-edge tick gap `UX-863`'s
  verifier named (`UX-868`). Eleven filings this round, eight closed.
- The touching sweep missed three full-suite guards on one merge and
  two more at the close; the gates found them. A track's touching run is a selector, as CLAUDE.md
  says, and the round paid one red gate to relearn it.
