# Round 119 — the jobserver's value: the server's shape, the snapshot switch, and the gaps round 118's verifiers named

Run on 2026-09-14, after round 118 merged. Five rows filed and five
closed, as five `implementer` tracks behind five `verifier` reads on
`sonnet`, the pull request open from the first green gate; the quiet-box
pair the round was for was run by the session at the close.

## The premise

BuildStream caps an element's `max-jobs` at 8 by default. On a 40-core
server an llvm-sized element alone on the critical path builds at
`-j8` with 32 cores idle; under the mode it takes every token the pool
has. Round 118's evaluation could not show it - four elements at `-j4`
on four cores are saturated at `off` - so this round models the server
on this box: one long element under a `max-jobs` below the core count.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-853` `UX-854` `UX-855` `UX-856` | disjoint: the broker's memory sum, the proxies' leak audit, the ninja probe's guard, the snapshot switch |
| 2 | `UX-857` | after the switch: `examples/11-serial-giant`, captured both ways in CI |

## What closed

| row | what landed |
|---|---|
| `UX-853` | the broker's memory gate sums `peak x (1 + held)` over every running element, not the one asking |
| `UX-854` | a proxy token held by a killed job is audited: the broker is the sole auditor when a plan runs, and `poll()` refreshes `pid_to_element` from the live raw log |
| `UX-855` | `probe_ninja` has its own guard, through a fake `bwrap` that prints ninja's help; a help text naming no jobserver reads `jobserver_client: False` (case added at merge) |
| `UX-856` | `bga snapshot --jobserver` (auto, N or off) and `--plan` (@prev, @last or a path), one mode helper shared with `bga capture run`; the compare header names each side's mode |
| `UX-857` | `examples/11-serial-giant`: one cmake element of 256 generated C files at 9800 lines under `max-jobs: 2`, three leaves waiting on it, a CI step capturing both modes cold and asserting `auto` under `off` |

## The verifiers found

- `UX-853`: PASS; a held count carried across ticks by another element
  has no case - noted in the Deviation, not filed.
- `UX-854`: HOLD - the pool's audit and the broker's both refilled one
  proxy leak (a double refill), the poll refresh was unguarded, the
  guide's prose was stale; the track made the broker the sole auditor
  when a plan runs, and the re-check passed.
- `UX-855`: PASS; a help text with no `jobserver` in it had no case -
  the session added one at merge, mutation red.
- `UX-856`: HOLD - the compare header's print was unguarded and the size
  ledger had grown; both closed on the track, re-check PASS.
- `UX-857`: HOLD - an MD032 line, no expected ratio beside the measured
  one, the CI assertion's risk written only in a test docstring, no
  sentence saying the quiet pair was still owed, and a tie boundary
  uncovered; the track closed all five, the session ran the pair.

## Agents

Ten runs, every one a row in the ledger: five `implementer` tracks and
five `verifier` reads, all on `sonnet`. Four tracks were resumed
(`UX-857` twice, `UX-854`, `UX-855` and `UX-856` once each); three
verifiers held (`UX-854`, `UX-856`, `UX-857`), two re-checked to PASS.

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| implementer | 5 | 2252k | 967 | 270 m |
| verifier | 5 | 370k | 200 | 84 m |

`UX-857` alone was 1108k over 99 minutes: three captures of a 4-minute
example per pass, and two resumes.

## The gate, seven times

| run | head | result |
|---|---|---|
| 0 | `b9f64a1e` | red, 7: the five filings had no Decomposition block, an area not in the §6 tree, MD032 lines and an unlinked round |
| 1 | `7a25e1fe` | green, 8708 - pushed; PR #228 opened |
| 2 | `5ec7be91` | green, 8712 - pushed |
| 3 | `75bbd6fc` | red, 2: a pipe inside `UX-856`'s closed row; the selection ceiling at 155 over 154 |
| 4 | `b0970315` | green, 8730 - pushed |
| 5 | `e78b4a84` | red, 4 + 19 errors: the disk at 99 %, `bst` said "Cache too full" - 5.8 GB freed |
| 5b | `e78b4a84` | green, 8737 - pushed |
| 6 | the close | see the pull request |

## The quiet-box pair

The reading the round was for, `examples/11-serial-giant`, this 4-core
box, `/proc/loadavg` 1.58 at the start and 2.83 at the end, no agent or
suite running, fresh caches both times:

```text
bga capture run --run-dir run-off  --jobserver off  examples/11-serial-giant plane2-off.json  -- bst build all.bst
bga capture run --run-dir run-auto --jobserver auto examples/11-serial-giant plane2-auto.json -- bst build all.bst
bga compare run-off run-auto
Verdict: IMPROVED  (total duration -30.47s, -10.6%, 286.53s -> 256.06s)
  giant.bst: -31.05s (281.30s -> 250.25s)
```

| reading | off | auto |
|---|---|---|
| `giant.bst` `peak_work_concurrency` | 2 | 3 |
| `giant.bst` measured-process span | 71.19 s | 47.54 s |
| `giant.bst` `cc1` CPU | 122.6 s | 121.3 s |
| `giant.bst` wall (Plane 1) | 281.30 s | 250.25 s |
| total | 286.53 s | 256.06 s |

The span moved by x 0.668 against the 2/3 the width predicts; the wall
moved by the span's 23.65 s plus 7.4 s. The same pair at load 7-13, run
twice by the track with other agents and a suite on the box, read
REGRESSED +10.9 % both times: the mode's reading follows the box's
load, not the example. The walls are twice the track's because the
sandbox is: plain `bst build all.bst` with no `bga` read 276.3 s in the
same environment (`giant.bst` "Running commands" 4:31), the recipe
standalone 76.1 s (`generate.sh` 8.75 s, `cmake` 0.28 s, `make -j2`
67.06 s), the capture 281.30 s - the hook's share is about 10 s.

## Standing

- Direction 20 has its first positive reading: one long element under a
  cap, 3 jobs against 2 on four cores, -10.6 % on the wall. On the
  40-core server the same shape is 39 tokens against `max-jobs` 8; that
  number is still to be measured on such a box.
- The CI step for `examples/11` asserts `auto < off` on the runner's
  own quiet reading; if it reds there, the reading is the finding and
  the assertion drops in favour of the two printed walls.
- `bst`'s sandbox costs about 200 s on 117 MB of generated sources
  here, 2.6x the recipe; a reading, not a filing - it moved neither
  mode.
- The disk reached 99 % once more (gate 5); 5.8 GB of finished pytest
  and old scratch directories freed, the 19 stale agent worktrees
  (3.1 GB) left where the permission classifier declined the sweep.
