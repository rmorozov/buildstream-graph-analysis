# Round 118 — the fifteen open rows: review 23's three and the jobserver's stage 1

Run on 2026-09-14, after round 117 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit (the user's proposal),
and closed with the round.

## Plan

Fifteen rows open: `UX-838` to `UX-840` from review 23 and `UX-841` to
`UX-852` from Direction 20. The dependency order the filings declare:

| wave | rows | why together |
|---|---|---|
| 1 | `UX-838` `UX-839` `UX-840` `UX-841` | disjoint surfaces: the contracts guard, the README, the styleguide guard, the tracer's FIFO |
| 2 | `UX-842` `UX-845` `UX-851` | after `UX-841`: the shim's pin rule, the tracer's pool, the capture option |
| 3 | `UX-843` `UX-846` `UX-852` `UX-844` | after the pin rule: the environment table, the wrappers, the leak audit, the key guard |
| 4 | `UX-847` `UX-848` `UX-849` `UX-850` | after the pool and the wrappers: the ledger, the example, priority, memory |

## What closed

Thirteen of the fifteen at this commit, in the order they merged; every
row a verified track, its Deviation at merge in the task file.

| row | what landed | at merge |
|---|---|---|
| `UX-840` | the §3e summary table follows the bound | - |
| `UX-838` | `fan_in[].direct` has prose and a guard | the p75 sentence corrected |
| `UX-839` | the clone-size claim re-measured (104 and 47 MiB) | - |
| `UX-841` | the tracer's FIFO has a guarded lifecycle; the auth style follows `make` | - |
| `UX-845` | `PoolController` follows busy cores and PSI; the ledger | two verifier edges closed on the track; the guard's PSI path pinned after CI's runner exposed the real file |
| `UX-842` | a pinned element never joins | meson composes a bare `JOBS` integer - the verifier's hold, fixed |
| `UX-851` | `bga capture --jobserver auto` and the snapshot fact | zero and negative ceilings, a stale mode variable |
| `UX-843` | the per-kind environment table, the ninja probe | a failed kinds read made loud |
| `UX-844` | `%{full-key}` equal either way, CI's replay cached 11 of 11 | the bst-tier pin to 51 |
| `UX-848` | `examples/10-jobserver`, two captures in CI | two commits squashed; stage-1 walls REGRESSED +5.6 % |
| `UX-846` | token-holding wrappers for lld, gold, mold, ninja | the mount moved under the trace bind (the sandbox root is read-only, found by CI); the env name unified; three shim cases |
| `UX-847` | the `jobserver` block in `analyze/v6` and the page | two holds closed on the track; the golden export bound to 474,000 |
| `UX-852` | leaked tokens audited against live pids | the audit thread joined before the FIFO closes |

Open: `UX-849` (proxies by slack) and `UX-850` (memory) - see the end.

## The verifiers found

- Meson composes `JOBS` as a bare integer, not `-jN`: the filing, the
  Motivation and the first implementation all said otherwise; a pinned
  meson element joined the jobserver until the verifier built a meson
  project and read `%{env}` (`UX-842`).
- The first wrappers resolved *themselves* as the real tool when reached
  through a symlink and re-ran their own `--help` probe without bound:
  32,000 processes, `Cannot fork` on every hook, a container restart.
  A re-entry guard plus identity checks, and `ulimit -u` does nothing
  for root (`UX-846`).
- A field that is always null is a proxy for the thing it names: the
  per-element held-token figures shipped with no producer (`UX-847`).
- A failed `bst show` for kinds switched the whole mode off silently
  (`UX-843`); zero and negative ceilings passed unvalidated (`UX-851`).

## Agents

Twenty-seven runs at this commit, every one a row in the ledger:
thirteen `implementer` tracks and fourteen `verifier` reads, all on
`sonnet`, one verifier cut off by the session during the fork storm.
Three tracks were resumed three times (`UX-846`, `UX-847`, `UX-841`
once); two verifiers held and re-checked (`UX-842`, `UX-847`).

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| implementer | 13 | 8768k | 4004 | 854 m |
| verifier | 14 | 1330k | 962 | 249 m |

## The gate, ten times

| run | head | result |
|---|---|---|
| 1 | `be72c782` | red: the disk filled mid-run (31 ENOSPC, 83 failed); the failed files alone re-ran green |
| 2 | `be72c782` | killed with the container |
| 3 | `c4366328` | green, 8631 - pushed |
| 4 | `d28f4498` | stopped: CI's runner has `/proc/pressure/cpu`, three pool cases read it |
| 5 | `5b5d7d65` | green, 8632 - pushed |
| 6 | `182c28b8` | red: the Verification Log stale after the wrappers' member line |
| 7 | `ea50b10e` | green, 8673 - pushed |
| 8 | `e027391b` | red: one merge commit body of nine lines |
| 9 | `e55c5474` | red: Direction 20's Status read as wholly closed |
| 10 | `e416e2bc` | green, 8680 - pushed |

CI added what no local run could: the runner's PSI file, and the
read-only sandbox root that refused the wrappers' mount at `/`.

## Standing

- The mode builds `examples/06` end to end on this box after the mount
  fix: exit 0, `core.bst` pinned, eight cmake elements joined on the
  make path (ninja probe: no ninja in that sandbox).
- `examples/10-jobserver` read REGRESSED +5.6 % before the kind table
  and the wrappers merged; Direction 20's Status is decided on the
  post-merge re-run, not on that row.
- The size ledger was adopted three times in one round; `dev_sizes.py
  --check` belongs beside `dev_baseline.py --check` before every gate.
- Disk: 64 stale agent worktrees and old scratch (23 GB) removed at 97 %.
