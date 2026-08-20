# UX-163: the interrupt contract covers the build and not the minutes around it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-157 (the contract this widens), UX-159 (which made the surrounding phases visible)

## Motivation

UX-157's salvage works — round 17 SIGINTed a real capture mid-build
and got exit 130, no traceback, both planes salvaged, partial
analysis. But the conversion to `CaptureInterrupted` happens inside
`run_traced_build`, so it protects only interrupts that land while
`bst` runs. Round 17 also hit the *other* window live: a SIGINT that
arrived after the build, during `Extracting run data (bst show)...`,
produced a raw `KeyboardInterrupt` traceback through
`extract_run → subprocess.communicate` and a snapshot with
`plane2.json` but **no `run/`** — even though `build.log` was complete
on disk and extraction is re-runnable from it, which nothing tells the
user.

On a big project these unprotected windows are precisely the long
ones: the census walk before the build and `bst show` extraction after
it are the phases UX-159 gave announcement lines *because* they take
minutes. A user watching "Extracting run data..." after a three-hour
build is exactly who presses Ctrl-C.

One more edge from the round-17 review, same theme:
`shutdown_build_group` waits 120s after SIGINT before escalating to
SIGTERM (`tools/bst_run_wrapped.py:66`). On a big element bst's
graceful stop can exceed that; the SIGTERM kills bst before it prints
its closing Pipeline Summary, the run loses `queue_summary`, and the
NOT COMPARABLE wording silently drops its "N of M scheduled" clause —
the most useful number, lost on exactly the biggest builds.

## Required Fix

1. **The whole snapshot lifecycle converts interrupts**: pre-build
   phases (compile, census) and post-build phases (analysis,
   extraction, compare) catch `KeyboardInterrupt`, print where things
   stand, and exit 130 — no traceback from any phase.
2. **A post-build interrupt names the resume**: the artifacts already
   on disk (`build.log`, `plane2.json`) and the exact command that
   finishes the job (`bga extract --format wrapped <project>
   <build.log> <run-dir>`), since nothing needs re-building.
3. **The grace window scales or reports**: either make the 120s
   SIGINT grace configurable/longer, or when escalation truncated
   bst's own summary, say so in the run ("interrupted; bst's queue
   summary was lost to escalation") instead of silently dropping the
   clause.

## Out of Scope

- Resuming a capture (unchanged from UX-157).
- Signals other than SIGINT (SIGKILL cannot be caught; SIGTERM may
  follow the same path as SIGINT if cheap, but is not the ask).

## Acceptance Test

Round 17's live shape, re-run: SIGINT during `Extracting run data...`
→ exit 130, no traceback, a notice naming `build.log` and the extract
command; running that command completes `run/` and `analyze` works.
SIGINT during the census → exit 130, no traceback, scratch clean. The
UX-157 mid-build acceptance still passes unchanged.
