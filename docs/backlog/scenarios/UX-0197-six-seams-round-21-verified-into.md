# UX-197: six seams round 21 verified into

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-183, UX-185, UX-188 (the landings these trail), UX-190 (whose guard the environment note concerns) | **Topic:** guards

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

---

## What was built

All six, each reproduced before it was touched. Four were defects in
round-20 code, and the class they share is worth naming: every one is a
claim that was **written down and not checked**.

**1. The byte-identity test was vacuous — and worse than the item
says.** Measured: the "progress on" child and the "progress off" child
both emitted **0 stderr bytes**, so the two runs were identical in
stderr as well and the assertion could not have failed. The proof is
direct — routing the ticker to stdout (the exact regression the test
exists to prevent) leaves the *original* test **passing**:

```text
--- the ORIGINAL UX-183 test, against progress-writes-to-stdout ---
1 passed
--- the CORRECTED UX-197 test, same mutation ---
2 failures
```

Two things were wrong, not one. `BGA_FORCE_PROGRESS` now lets a piped
child draw at all — but the *command* was also wrong: `bga analyze` on
a three-element fixture has no long phase, so even forced it emits
nothing. The test drives `bga snapshot --list`, which walks the store
where `UX-183` actually put a ticker: **102 stderr bytes on, 0 off,
stdout byte-identical**. A precondition test asserts the force switch
is effective, so the comparison can never go quiet again, and
`BGA_NO_PROGRESS` still beats it — the documented off-switch stays
absolute. The force env is deliberately undocumented: it would write
control characters into `2>file`, which is the one thing `UX-183` is
about.

**2. `bga timeline` printed a path that was already gone.** Reproduced
verbatim:

```text
Successfully generated trace! Open /tmp/bga-timeline-umfcn7q8/plane1.json in ...
```

`UX-188` moved that sentence to stderr and left a comment saying a
timeline user must not see it. The stream changed; the sentence did
not. `main(argv, quiet=False)` now, with the composing caller passing
`quiet=True` and printing the final path itself — every path in the
output exists after exit, and `bga log-to-chrome` still tells its own
user where the file went. The adjacent pre-existing bug went too: both
`FileNotFoundError` paths printed to **stdout** and returned `None`,
which `sys.exit(None)` renders as **exit 0**, so a missing input was a
silent success to every caller checking status — including this file's
own composing caller.

**3. `RunContext.suspended` deleted.** Never assigned, never read, and
one letter from the `suspension` property that does the work — so the
obvious name answered `None` for a run that really had slept. The
comment explaining where the data lives moved onto the property that
reads it.

**4. Ctrl-C no longer orphans `bst show`.** Reproduced with a 120s
child: after the parent took the `KeyboardInterrupt`, `kill -0` found
the child alive. `UX-183` swapped `subprocess.run` for `Popen` plus a
poll loop to draw a ticker and lost `run`'s kill-on-exception
contract. `except BaseException: kill; wait; raise` restores it —
`BaseException` because `KeyboardInterrupt` and `SystemExit` are
exactly the two this is about.

**5. Both counts corrected, with the annotation rather than silently.**
`UX-183..UX-192` is ten items, not twelve.

The alias half took two attempts, and the second is the lesson. The
row was corrected from "ten" to "seventeen" and guarded against
`len(TOOL_ALIASES)` — and `UX-194` broke that an hour later by adding
an eighteenth alias (`bga view`). A row that must be edited whenever a
command is added is a row that will be stale again, which is seam 5
itself. It reads "every alias command" now, and the guard asserts it
names **no** number; the coverage is checked where it belongs, in
`test_help_is_short.py`, which reads the mapping directly.

**6. The schema guards cannot vanish quietly.** Reproduced in a clean
venv:

```text
$ python -m pytest tests/unit/test_output_schemas.py -q
collected 0 items / 1 skipped
```

25 guards, one skip line. The module now always collects; the
per-class `needs_jsonschema` marker gives a contributor's bare venv an
honest skip, and one canary test **fails** wherever `BGA_EXPECT_DEV` is
set. CI sets it workflow-wide. Driven both ways for real:

```text
no jsonschema, BGA_EXPECT_DEV unset  -> 26 skipped
no jsonschema, BGA_EXPECT_DEV=1      -> 1 failed, 25 skipped
```

Tests: 12 new (`tests/unit/test_six_seams_round_21_found.py`) plus
three rewritten in the progress suite, and a
`tests/support/_hide_jsonschema.py` plugin so seam 6's guard runs in
the environment it describes rather than asserting about it. Ten
mutations, each red — including two over-fixing directions (deleting
the converter's sentence outright, and letting the canary skip).

**Deviation from the Required Fix:** none. Item 2's parenthetical
("or say the *final* path") was resolved the other way — suppress
under `timeline`, keep it for the direct caller — because
`log-to-chrome`'s own user does want that path, and the composing
caller already prints the final one.

