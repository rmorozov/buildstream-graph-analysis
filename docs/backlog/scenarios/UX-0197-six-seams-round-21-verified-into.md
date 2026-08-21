# UX-197: six seams round 21 verified into

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-183, UX-185, UX-188 (the landings these trail), UX-190 (whose guard the environment note concerns)

## Motivation

The round-21 review verified all ten field-feedback landings — four
mutations re-run, the pip-through-blast and 68-char paste cases run
live — and collected six seams, none reopening its parent:

1. **UX-183's byte-identity test is progress-off vs progress-off.**
   The log says stdout was compared "with progress forced on and off";
   no force-on mechanism exists (only `BGA_NO_PROGRESS`), and both
   subprocess runs pipe stderr, so both are off — the comparison is
   vacuous about progress. Add the force-on env
   (`BGA_FORCE_PROGRESS=1`, test-only by intent) and make the test
   what its docstring says; annotate the log.
2. **`bga timeline` still prints the doomed path.** The Plane 1
   converter's "Successfully generated trace! Open
   `/tmp/bga-timeline-XXXX/plane1.json`..." names a scratch file
   deleted moments later (`bst_log_to_chrome_trace.py:860`) — the
   sentence the UX-188 log claims was fixed moved streams and kept
   its content. Suppress the inner sentence under timeline (or say
   the *final* path); while in the file: its missing-input path
   prints `Error:` to stdout and returns None → exit 0 (pre-existing,
   now adjacent).
3. **`RunContext.suspended` is a dead field** — never assigned, never
   read (`bga/ingest/models.py:162`); the working accessor reads
   `build_outcome`. Delete it, so a consumer cannot read `None` off a
   suspended run.
4. **Ctrl-C during `bst show` now orphans the child**: the UX-183
   Popen change lost `subprocess.run`'s kill-on-exception
   (`bst_show_to_graph.py:243-247`). A `try/except BaseException:
   kill` restores the old contract — the UX-157/163 lifecycle's own
   rule, one phase over.
5. **Two stale counts**: round-20.md says "twelve items" for ten, in
   the very commit titled "two counts the prose outgrew"; UX-192's
   status-table row says "ten alias commands" where its own log was
   corrected to seventeen.
6. **The UX-190 guard module skips silently without dev extras**:
   `jsonschema` absent made all 25 schema tests `importorskip` with
   no signal (real in CI, zero elsewhere). One collected test that
   *fails* (not skips) when the module's imports are missing while
   `BGA_EXPECT_DEV=1` (set in CI), so an environment drift is loud
   where it matters and silent where it should be.

## Required Fix

As numbered; each is a one-sitting item and the acceptance below is
per-number.

## Out of Scope

- The ten features themselves (all verified holding).

## Acceptance Test

(1) the byte-identity test runs one child with progress genuinely on
(force-env asserted effective by a stderr byte appearing) and stdout
still matches; (2) `bga timeline @last` output contains no path that
does not exist after exit (asserted by walking the printed text for
paths); (3) grep proves the field gone and the accessor test still
passes; (4) SIGINT during a mocked slow `bst show` leaves no child
(the UX-157 process-scan assertion, reused); (5) both counts
corrected with the annotation convention; (6) removing `jsonschema`
from a venv with `BGA_EXPECT_DEV=1` turns the schema module red, not
skipped.
