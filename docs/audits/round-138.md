# Round 138 — eighteen rows, one closing PR, and a chain

Run on 2026-09-23 from `98c387bc`. Eighteen rows closed by twelve fix
PRs — `#271`-`#276` and `#278`-`#283` — and moved in one closing PR,
`#277`, which carries architecture review 26 and this document.

```text
closed   UX-943 UX-936 UX-890 UX-917 UX-944 UX-929 UX-912 UX-935 UX-932
         UX-920 UX-937 UX-942 UX-928 UX-940 UX-941 UX-926 UX-948 UX-956
index    951 scenarios: 19 open, 932 closed      dev_close_task.py --check
filed    UX-975..UX-979 (review 26), UX-945 UX-950 UX-955 UX-990 (tracks)
```

## The cadence guard blocked every `--move`

`MAX_ROWS_BETWEEN_REVIEWS = 25`
(`tests/unit/test_the_review_has_a_cadence.py`). Review 25 stands at
889 closed rows and review 26 at 914 (`architecture-review.md`), so
the first move past 914 would redden it. Review 26 (`55e5e495`) ran
first as the enabler; every fix PR merged with its row still open, and
all eighteen moved here. After the moves: 932 closed, 18 since review
26.

## `--adopt --force` was refused; the growth moved by shape

`dev_sizes.py --adopt --force` moves a cell upward, and the permission
classifier refused it as a CI bypass. Two tracks were over the ratchet
and fixed it by cutting a module, then a plain `--adopt`:

```text
#275  ff70cb1a  tools/_close_task_checks.py   97 lines   dev_close_task.py 1365
#276  35831ad7  tools/_record_readers.py     174 lines   dev_touching.py    459
```

## Concurrent local suites on four cores

`UX-948`'s Motivation, measured by the orchestrator: one `make test`
17.5 min alone and 22-26 min beside other tracks; six concurrent runs
76 min with 43 false reds (`TimeoutExpired`, load average about 400).
A second concurrent run read 46 failures and 77 errors (orchestrator,
not in a task file). Ruslan's ruling, 2026-09-23 08:42-08:43: pushes
gate on fast checks and CI's matrix gates the merge. `make push-check`
(`#281`) is that gate — lint, the selector against the merge-base,
`dev_sizes.py --check`, `dev_close_task.py --check`.

## The chain

Every pair of PRs collides on the derived files (the README counts,
`areas/*.md`, `architecture.md`, the spread), so the last eight were
stacked, each branch merging the one before, and every CI ran at once:

```text
#275 41601fb7 10:32  #276 76f35e80 10:38  #278 ea41041c 11:11
#279 59a23c21 11:11  #280 69d3754f 11:16  #281 e120271c 12:22
#282 ace10807 12:26  #283 9ffa0b6b 12:26          (main, first parent)
```

Each landing was a clean merge, checked first by a trial merge in a
scratch worktree plus `dev_close_task.py --check`. What the chain
found:

- `#278`'s own tip was red: the new register guard was not declared
  census; census 31 -> 32, `HANDFUL` 45 -> 46 (`42a4a352`, `UX-940`).
- `#281`'s guard failed on CI only: the inner `make` inherited
  `MAKELEVEL` and printed `Leaving directory` last (`a65390de`,
  `UX-948`).
- `#283` raised the selection ceiling max 164 -> 167, measured max 165
  of 590 (`89384adf`). A local check read through a pipe without
  `pipefail` passed a red as green until the commit hook caught it.

## CI adopt commits moved main between merges

Eight landed on main's first parent between `#271` (07:45) and `#283`
(12:26) — `git log --first-parent 98c387bc..origin/main`:

```text
flake ledger  2   84277ca1 d51edfc9
tier rows     2   344ff767 6a77ca49
touch map     4   4c3df521 294a9da2 e2b57088 389b8af2
```

All eight are parented after `e458c51e` (`#271`), so each ran under
its green-run condition. The source runs' conclusions are not re-read
here: this container has no `gh`.

## The docs-only lane

This PR's diff against `origin/main` is 33 paths, all under `docs/`:
`git diff --name-only origin/main | tools/dev_docs_only.py` prints
`docs_only=true`. It is the first PR to run `UX-956`'s one-Python
lane.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| general-purpose | opus | `UX-935`/`UX-932`/`UX-920`/`UX-937` | 5343k | 258 | 253.4 m | grew `dev_close_task.py` past the size ratchet; the code moved to `tools/_close_task_checks.py` |
| general-purpose | opus | `UX-936`/`UX-890`/`UX-917` | 1491k | 151 | 86.3 m | none reported |
| general-purpose | opus | `UX-929`/`UX-912` | 1853k | 146 | 99.4 m | none reported |
| general-purpose | opus | `UX-943` | 578k | 66 | 55.6 m | none reported |
| general-purpose | sonnet | `UX-944` | 1616k | 194 | 92.7 m | repointed the shared editable install at its worktree |
| general-purpose | opus | `UX-942` | 2077k | 147 | 293 m | the size ratchet; the readers moved to `tools/_record_readers.py` |
| general-purpose | opus | architecture review 26 | 700k | 138 | 51.7 m | none reported |
| general-purpose | opus | `UX-926` | 2234k | 142 | 190.1 m | found round 96 undocumented |
| general-purpose | opus | `UX-928` | 1074k | 93 | 186 m | push refused by the permission classifier until Ruslan's word |
| general-purpose | opus | `UX-940` | 1276k | 136 | 211.1 m | its own tip was red: the new guard was not declared census |
| general-purpose | opus | `UX-941` | 955k | 125 | 113.3 m | none reported |
| general-purpose | opus | `UX-948` | 496k | 166 | 116.9 m | its guard's inner make inherited MAKELEVEL on CI |
| general-purpose | opus | `UX-956` | 255k | 143 | 46.4 m | none reported |

Thirteen rows, 19,948k fresh tokens and 1,905 tool calls, each derived
by `dev_track_cost.py --ledger`. No transcript repeats a `uuid`, so no
resume double-counts; wall is first to last timestamp and spans the
waits of a resumed track. The closing session's own row is not here:
its transcript is still being written.
