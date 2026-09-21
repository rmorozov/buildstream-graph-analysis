# Round 125 — a per-element switch for the jobserver auth style

Run on 2026-09-16, after round 124 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

Round 124 made `--jobserver auto` scrub the compiler-driving kinds when
the sandbox make is <4.4 — safe against the GCC-13 LTO ICE, but it caps
those elements at their recipe `-jN` (`max-jobs`) instead of the pool
ceiling (the agent's cores). The user's project is mixed-make: some
elements are pinned to GNU Make ≤4.2.1 and cannot move to 4.4 yet, so
a whole-project switch to `fifo:` is impossible. They need to force
`fd` on a named ≤4.2.1 element (so it fills the pool via the fd
jobserver its make accepts) or `off` on a known-LTO one — per element,
while the rest stay `auto` — as they migrate version by version.

Confirmed this round (step 0, a `researcher` read): the pool ceiling is
`os.cpu_count()` (not `max-jobs`), and without `--plan` a lone element
joins the global pool directly and can drain it to the ceiling
(UX-857 measured a `max-jobs: 2` element reaching 3). So the mechanism
to fill the box exists; the scrub is what withholds it on a <4.4 make,
and a per-element override is the lever.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-879` | one override path (capture flag → env → shim resolution) plus a guard |

One row filed. The compiler shim (an `fd`-forced LTO element that still
must not ICE) and the `public:` annotation surface are the next round.

## What closed

| row | what landed |
|---|---|
| `UX-879` | a `bga capture run --jobserver-auth-override 'fd:<glob> fifo:<glob> off:<glob>'` capture flag → a `BST_TRACE_JOBSERVER_AUTH_MAP` env carried into the sandbox → `resolve_auth_override` (pure, fnmatch, first-match-wins) in `bwrap_shim.py`, resolved against the element name in `_jobserver_injection` *before* the UX-878 compiler-safe path. A match forces the style and bypasses the make-probe decision: `fd` keeps the raw `--jobserver-auth=<fd,fd>` (so a pinned ≤4.2.1 element fills the pool via fd even where auto would scrub), `fifo` the path form, `off` scrubs (no auth, no wrapper mount, recipe `-jN` kept). Unmatched elements are unchanged (auto). Documented with the caveat: `fd` on an LTO element ICEs the cross-gcc until the compiler shim (round 126) — use `fd` for non-LTO ≤4.2.1 elements, `off` for LTO ones meanwhile |

## The verifiers found

- `UX-879`: HOLD, then PASS. The HOLD was `make lint` red on three
  PyMarkdown findings (MD031×2/MD040) in the Outcome's own "Close
  measured" fence — fixed at merge (blank lines + a `text` language
  tag). The substance verified clean: the `fd` force emits the raw fd
  pair on a make-4.3 fixture where auto scrubs (non-vacuous), the
  mutation reddens 8 of 11, no UX-874/878 regression (78 passed). The
  implementer had itself caught and fixed a vacuous `off` guard (written
  on make 4.3 where auto already scrubs → rewritten against make 4.4).

## Agents

2 runs priced, one `implementer` track and one `verifier` read, both on
`sonnet`; the track was not resumed, the verifier held once (the lint
fix was the orchestrator's at merge). A `researcher` read (step 0, the
ceiling/proxy verification) ran before the filing — the session's own
context, not a priced track.

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| implementer | 1 | 183k | 127 | 25 m |
| verifier | 1 | 90k | 44 | 11 m |

## The gate

| run | head | result |
|---|---|---|
| 0 | `65adb10f` (the filing) | red only on the round-open bootstrap guards; docs-only |
| 1 | the close | the run this commit is pushed under; the pull request carries the figure |

## Standing

Step 0 confirmed the pool ceiling is `os.cpu_count()` and, without
`--plan`, a lone element joins the global pool directly and can drain it
to the ceiling (UX-857 measured a `max-jobs: 2` element reaching 3) — so
the mechanism to fill the box exists; the sub-4.4-make scrub is what
withholds it, and this override is the per-element lever. The operator
can now force `fd` on a pinned ≤4.2.1 element so it fills the pool while
its make is migrated, `off` on an LTO one, and leave the rest `auto`.
Left standing for round 126: the compiler shim, so an `fd`-forced
element that *does* LTO fills the box without the gcc-13 ICE (today an
`fd`-forced LTO element still crashes — the caveat the guide documents);
the `public: bga.jobserver-auth` annotation as the version-controlled
second surface;
and the note that `main()`'s earlier sandbox-make probe still runs for
an overridden element (harmless, `_forced_auth` ignores the pool style).
