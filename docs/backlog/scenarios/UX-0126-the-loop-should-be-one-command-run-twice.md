# UX-126: the loop should be one command, run twice

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-95 (instance identity), UX-78 (refusal semantics), UX-115 (the renderer it feeds)

Post-MVP polish, direction: simplify the user scenarios. This is the
local scenario's remaining friction, measured from the guide's own
commands.

## Motivation

The documented local loop is three commands and five user-invented
paths, with the project path repeated:

```bash
bga capture run --wrapped-log /tmp/plane1.log --trace-opens \
    /path/to/project /tmp/plane2.json -- bst build target.bst
bga extract --format wrapped /path/to/project /tmp/plane1.log /tmp/run
bga analyze /tmp/run --plane2 /tmp/plane2.json
```

Then the loop's whole point — *did my change help?* — needs the user to
have parked the previous run somewhere and type both paths into
`bga compare`. Nothing is hard; everything is clerical, and the
clerical part is exactly what a user gets wrong at 6pm (`/tmp/run` vs
`/tmp/run2`, yesterday's plane2 joined to today's run — mistakes the
refusals catch *after* a 30-minute build). Three audit rounds ran this
loop dozens of times and every path in every invocation was invented by
the operator.

Meanwhile `bga capture run` already holds everything the second and
third commands need: the project path, the wrapped log it just wrote,
the plane 2 report path. The split exists because the pieces shipped in
different rounds, not because a user benefits from it.

## Required Fix

1. **Capture subsumes extract.** `bga capture run` gains
   `--run-dir PATH` (extract the run directory it already has the
   inputs for) and does it by default when the new store (below) is
   active. `bga extract` remains for logs captured elsewhere.
2. **A project-local run store.** `.bga/runs/<UTC-stamp>-<short-id>/`
   under the project (gitignored by a dropped `.bga/.gitignore`),
   holding `run/`, `plane2.json`, the wrapped log, and the capture
   context — the same layout the capture refs already use, so nothing
   downstream learns a second shape. Every command that takes a run
   directory accepts `@last`, `@prev`, `@<stamp-prefix>` resolved
   against the store of the project in cwd (explicit paths keep working
   everywhere; the store is a resolution convenience, not a format).
3. **The loop, spelled as itself:**

   ```bash
   bga snapshot -- bst build target.bst   # capture+extract+analyze into the store
   # …edit…
   bga snapshot -- bst build target.bst   # and compare against @prev automatically
   ```

   `snapshot` = capture run (with the project's stored default flags,
   see 4) + analyze, printing the report; when a previous snapshot of
   the same identity exists it appends the compare verdict (through the
   UX-78 refusals — a cross-mode pair says so instead of comparing).
4. **Sticky capture flags.** `.bga/config` records the trace flags and
   builders/max-jobs the user last passed (or sets explicitly), so
   `--trace-spine=auto --trace-opens` is decided once per project, not
   remembered per invocation. Every report already records what
   actually ran (UX-95/UX-113), so stickiness cannot silently change
   what a capture *claims*.

The guides then teach the two-line loop first and keep the explicit
three-command form as the "plumbing" section — same doc pattern the
CLI already uses for `python3 -m` internals.

## Out of Scope

- Any change to run-directory format, identity, or refusal semantics
  (the store is pure resolution).
- Retention policy beyond "the user deletes `.bga/runs` entries";
  a size warning is enough.
- CI usage (CI has UX-96's refs; the store is the laptop's analogue).

## Acceptance Test

On `examples/06`: two `bga snapshot` invocations around the
macro-fix edit reproduce round 10's numbers with **zero user-invented
paths** — the second prints the analyze report *and* the compare
verdict against `@prev` (IMPROVED, the known −10%). `bga analyze @last`
and `bga compare @prev @last` resolve from inside the project and fail
with a named error outside any project. A cross-mode `@prev`/`@last`
pair refuses exactly as explicit paths do. The guide's quick path
shows the two-line loop, and its commands are the tested ones (the
docs-commands test extended to cover `snapshot`).
