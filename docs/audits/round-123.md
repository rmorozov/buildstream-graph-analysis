# Round 123 — the auth style autodetect finally picks the safe one

Run on 2026-09-16, after round 122 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

The user ran `--jobserver auto` on the latest bga and hit the fifo
rejection again, now on a `kind: cmake` element whose sandbox-built
cmake runs `/usr/sysroot/bin/make` (below 4.4) by absolute path:
`make: *** internal error: invalid --jobserver-auth string
'fifo:/tmp/.bst-native-trace/jobserver'. Stop`, exit 2. Round 122's
`UX-874` probe covers only `make`/`autotools` and reads bare `make` on
`PATH`, so it never saw cmake's own make. `auto` cannot know, ahead of
the build, every make a recipe will invoke, and `fd`-style auth every
make from 4.2 up accepts. Two fixes: `auto` picks `fd` (`UX-876`), and
the sandbox-make downgrade covers every kind that injects `MAKEFLAGS`
for anyone who still forces `fifo` (`UX-877`).

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-876` `UX-877` | disjoint files: the host-side auto default in the tracer, the sandbox-side downgrade scope in the shim |

Two rows filed, two closed.

## What closed

| row | what landed |
|---|---|
| `UX-876` | `jobserver_auth_style("auto")` returns `fd` unconditionally, dropping the host `make --version` probe; `fd`-style auth is accepted by every GNU Make from 4.2 up, so a mixed toolchain builds under `--jobserver auto`. `fifo` is the explicit opt-in for a uniformly 4.4-or-newer toolchain, on both `bga capture run` and `bga snapshot`. The guide's `--jobserver-auth` row says so |
| `UX-877` | for an explicit `fifo`, the sandbox-make downgrade now covers every kind whose `kind_job_env` injects a make-consumed `MAKEFLAGS` (`make`, `cargo`, `cmake_meson`, `jobs_env`), derived from the injection's own policy tag rather than a hand-kept kind list; `ninja_client`/`ninja_wrapper` (ninja reads the auth, not a foreign make) and `ninja_static`/`unknown_kind` (no `MAKEFLAGS`) stay unnarrowed |

## The verifiers found

- `UX-876`: PASS. The one argv test that used `auto`+4.4 as a shortcut
  to obtain `fifo` was switched to an explicit `fifo` request (it tests
  shim argv, not auto selection); removing the host subprocess left a
  stale `UX-841` ruff S603 forced entry, dropped with
  `dev_baseline.py --shrink`. The Outcome's touching count re-measured
  higher on the verifier's worktree, the map having grown, 0 failed.
- `UX-877`: PASS. The covered set matches `kind_job_env`'s own
  `MAKEFLAGS`-emitting policy tags exactly, and the ninja cases are
  rightly left alone. The guard's `makeflags_injected` half has no
  reddening mutation - every make-consumer policy pairs a `MAKEFLAGS`
  today, so it is derived-safety against a future policy, not
  load-bearing now.

## Agents

4 runs, every one a row in the ledger: two `implementer` tracks and
two `verifier` reads, all on `sonnet`. Neither track was resumed and
neither verifier held.

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| implementer | 2 | 186k | 143 | 29 m |
| verifier | 2 | 105k | 66 | 13 m |

## The gate

| run | head | result |
|---|---|---|
| 0 | `1b663fa8` (the filings) | red only on the in-progress-round guards (Agents table, register, dateline settle at close); the changed files were docs-only |
| 1 | the close | the run this commit is pushed under; the pull request carries the figure |

## Standing

The box runs only GNU Make 4.3, so neither the host-4.4/sandbox-old
split nor a real cmake element could be built here; the guards drive
both through a fake-make sandbox. On the user's host, `bga snapshot
--jobserver auto` now hands every sandbox `fd`-style auth, which the
`/usr/sysroot/bin/make` a cmake recipe invokes accepts whatever its
version - the failure that opened this round. `--jobserver-auth fifo`
stays available and is now narrowed per element for every make-consuming
kind. The one nag left: `_MAKE_CONSUMER_POLICIES` is a hand-kept set of
policy names, so a future `kind_job_env` policy that injects a
make-consumed `MAKEFLAGS` must be added to it or the same class of
defect recurs one level down.
