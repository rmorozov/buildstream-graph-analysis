# UX-875: bga snapshot forwards the jobserver auth style

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-856, UX-841 | **Found by:** round 122, the user (a make-kind element from a tar source, GNU Make 4.4 on the host) | **Serves:** R4 (the snapshot entry point can force the auth style capture run already can) | **Topic:** capture | **Area:** tools | **Shape:** bounded

## Motivation

`bga capture run` exposes `--jobserver-auth {fd,fifo,auto}`
(`UX-841`), but `bga snapshot` (`UX-856`) exposes only `--jobserver
MODE`; there is no way to force the style from the snapshot entry
point. Until `UX-874` lands, `auto` is the only choice a snapshot user
has, and on a host whose make is 4.4 over a sandbox make below it that
choice fails the build (`UX-874`'s motivation). Even with `UX-874` an
operator wants the escape hatch `capture run` already gives.

## Required Fix

`tools/bga_snapshot.py`: a `--jobserver-auth {fd,fifo,auto}`
argument (default `auto`, matching `capture run`) forwarded to the
tracer's own `--jobserver-auth` in the composed argv, beside the
`--jobserver <int>`/`--jobserver-seed` it already appends; the
`snapshot()` signature carries it the way it carries `jobserver`.

## Decomposition

Input classes: auth unset (default auto), fd, fifo; each with
jobserver off (no auth token appended) and on. Surfaces:
`tools/bga_snapshot.py` (the argument, the signature, the argv
compose) · `tests/unit/test_the_snapshot_records_the_jobserver.py` or
the snapshot's own test file. Parallel with UX-874 (disjoint
surfaces).

## Out of Scope

The auth style's own meaning (`UX-841`, `UX-874`) - this only
forwards the flag. Any new resolution logic; `snapshot` composes the
tracer argv and the tracer resolves as it does for `capture run`.

## Acceptance Test

The snapshot test asserts `--jobserver-auth fifo` on the command
line reaches the tracer argv as `--jobserver-auth fifo`, and that with
the jobserver off no auth token is appended. Mutation: drop the
forward - the flag is accepted and silently dropped, red.

## Outcome

**Gap measured.** Pre-fix, `create_parser()` had no `--jobserver-auth`
argument; an operator's only lever was `--jobserver`, and
`take_snapshot`'s composed argv never carried `--jobserver-auth` to
the tracer, so every snapshot ran the tracer's own `auto` resolution
regardless of what a user might type.

**Close measured.** `take_snapshot` now takes `jobserver_auth: str =
"auto"` and, inside the existing `if mode and mode != "off":` block
(beside `--jobserver`/`--jobserver-seed`), appends `["--jobserver-auth",
jobserver_auth]`; off appends nothing, matching the existing posture.
`create_parser` gained `--jobserver-auth {fd,fifo,auto}` (default
`auto`), wired to `main`'s `take_snapshot(...)` call. `pytest -q
tests/unit/test_the_snapshot_takes_the_jobserver_switch.py`: `13
passed in 0.36s`. `make test-touching`: `80 file(s) selected (27
census + 53 naming the change) - 2145 passed, 31 skipped in 77.50s`.
`ruff check tools/bga_snapshot.py
tests/unit/test_the_snapshot_takes_the_jobserver_switch.py`: `All
checks passed!`. `python3 tools/dev_sizes.py --check` (post `--adopt
--force`, 2 cells changed - `tools/bga_snapshot.py` `longest_function`
195 -> 196, `file_lines` 1629 -> 1641): `sizes ok`. `python3
tools/dev_baseline.py --check`: exit 0, unchanged findings list.
`python3 -m pymarkdown --config .pymarkdown.json scan` on this file:
clean. `make check-clean`: `OK: no ignored files are tracked`.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| drop `argv += ["--jobserver-auth", jobserver_auth]` (flag stays accepted, silently dropped) | `test_fifo_reaches_the_tracer_argv`, `test_the_cli_flag_reaches_take_snapshot` | 2 failed, 11 passed -> reverted, 13/13 |

**Deviation (merge):** none. The verifier replayed the drop-forward
mutation (2 red) and a second of its own - moving the append outside
the `mode != "off"` guard reds the third test - so each of the three
new assertions is independently load-bearing. The tracer accepts the
forwarded `--jobserver-auth` and resolves it there; snapshot adds no
resolution. Nothing added at merge.
