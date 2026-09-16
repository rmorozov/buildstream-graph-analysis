# Round 122 — the auth style the sandbox make refused

Run on 2026-09-16, after round 121 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

The user built a `kind: make` element from a `tar` source on a host
with GNU Make 4.4 and hit
`make: *** internal error: invalid --jobserver-auth string
'fifo:/tmp/.bst-native-trace/jobserver'. Stop`, exit 2. `UX-869` had
already put the FIFO where the sandbox reaches it (the path is right,
no `mkdir parents` error); the *style* was wrong. `jobserver_auth_style`
picks `fifo` from the **host** make, but the element's own `tar` stages
an older make, and that make - the one that actually consumes the
string - rejects `fifo:`. `fd` style every make from 4.0 up accepts, so
the fix is a sandbox-make check that narrows fifo to fd. Two filings.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-874` `UX-875` | disjoint surfaces: the shim's per-element auth downgrade, the snapshot entry point's passthrough |

Two rows filed, two closed.

## What closed

| row | what landed |
|---|---|
| `UX-874` | the shim probes the sandbox's own `make --version` (through the real bwrap, the way `probe_ninja` does) and narrows `fifo` to `fd` for that element when the sandbox make is below 4.4, sharing the 4.4 cutoff with the host-side `jobserver_auth_style`; the probe is cached `make_probe-<element>.json`, per element, so a build whose elements ship different makes each get the style their own make accepts; the global FIFO and UX-849's proxy both follow the downgrade |
| `UX-875` | `bga snapshot` gains `--jobserver-auth {fd,fifo,auto}` (default auto) and forwards it to the tracer, which resolves it as it does for `bga capture run`; the token is appended only when the jobserver is on |

## The verifiers found

- `UX-874`: HOLD - `make lint` was red (PLR0915 on `main()`, S603 on
  `probe_make`) though the Outcome claimed exit 0, and the make probe
  was cached per capture, not per element, so two make-kind elements
  with different sandbox makes would share one answer and the second
  would hit the very defect the row fixes. Both closed on the amend:
  the downgrade factored into a helper, `probe_make` sharing a call
  site so it adds no baseline entry, the cache keyed per element with
  a guard that reds on a shared key. Re-check PASS.
- `UX-875`: PASS; the verifier ran a second mutation of its own to
  prove each of the three new assertions is independently load-bearing.

## Agents

4 runs, every one a row in the ledger: two `implementer` tracks and
two `verifier` reads, all on `sonnet`. The `UX-874` track was resumed
once, and its verifier held and re-checked to PASS.

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| implementer | 2 | 426k | 232 | 55 m |
| verifier | 2 | 212k | 88 | 40 m |

## The gate

| run | head | result |
|---|---|---|
| 0 | `5d763963` (the filings) | red only on the in-progress-round guards (the ledger, Agents table and register fill at close); the changed files were docs-only |
| 1 | the close | the run this commit is pushed under; the pull request carries the figure |

## Standing

The box runs only GNU Make 4.3, so the host-4.4 / sandbox-4.3 split the
row fixes cannot be built here; the guards drive it through a fake-make
sandbox instead. The user's own host is where the live reading belongs:
a `kind: make` element whose `tar` stages an older make should now build
under `bga snapshot --jobserver auto`, and `--jobserver-auth fd` forces
fd everywhere as the escape hatch. `ninja_probe.json`'s own per-capture
cache is the same shape as the bug this round fixed for make, left as a
separate pre-existing matter.
