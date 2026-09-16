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
| `UX-879` | (filled at close) |

## The verifiers found

(filled at close)

## Agents

(filled at close)

## The gate

(filled at close)

## Standing

(filled at close)
