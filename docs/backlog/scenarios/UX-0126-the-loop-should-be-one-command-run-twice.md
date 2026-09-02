# UX-126: the loop should be one command, run twice

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-95 (instance identity), UX-78 (refusal semantics), UX-115 (the renderer it feeds) | **Topic:** store

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


---

## What was built

`bga snapshot` (`tools/bga_snapshot.py`) and a project-local store
(`bga/run_store.py`), plus `bga capture run --run-dir`.

**`snapshot` composes; it does not reimplement.** It builds an argv and
calls `bga capture run`'s own `main()`, then `bga analyze`'s, then
`bga compare`'s. Nothing in it can drift from what the three explicit
commands do, because it is them — which is also why every refusal,
hedge and exit code below is the one those commands already produced.
`capture run` gained an optional `argv` parameter for this; every
existing caller passes nothing.

| item | where |
|---|---|
| 1. Capture subsumes extract | `bga capture run --run-dir PATH`, which implies `--wrapped-log` (to a temp path if unnamed, the same shape `UX-80` gave the invocation record) |
| 2. The store | `.bga/runs/<UTC-stamp>[-NN]/` holding `run/`, `plane2.json`, `build.log`, `capture-context.txt`; `.bga/.gitignore` dropped on first write; `@last`/`@prev`/`@<stamp-prefix>` resolved for every run-directory argument |
| 3. The loop | `bga snapshot -- bst build TARGET`, twice |
| 4. Sticky flags | `.bga/config`, holding `trace_opens` and `trace_spine` |

Alias resolution is threaded once, in `bga.cli.main`, over the
*attribute names* that hold a run directory (`directory`, `baseline`,
`candidate`, `run_dirs`, `baseline_run`, `calibration_dir`) rather than
per command — so
`analyze`, `graph`, `floors`, `replay`, `sweep`, `utilisation`,
`diagnostics`, `correlate`, `cache-trend` and `compare` all take aliases,
and a future command reusing `directory` gets them for free.

## The acceptance run

A copy of `examples/06` (its `optimized/` variant removed so nothing
could be read from it), `--builders 4 --max-jobs 4`, caches dropped
between the two builds, on this 4-core container. **Every path below was
produced by the tool; the operator typed none.**

```text
$ cd <project> && bga snapshot -- bst --builders 4 --max-jobs 4 build all.bst
Capturing into <project>/.bga/runs/20260819T162249Z
...
This is the first snapshot of this project - make your change and run the same
command again, and the comparison against it is automatic.

$ cp optimized/elements/lib-*.bst elements/          # the macro fix, nothing else
$ bga snapshot -- bst --builders 4 --max-jobs 4 build all.bst
Capturing into <project>/.bga/runs/20260819T162326Z
...
$ bga compare @prev @last
Verdict: IMPROVED  (total duration -4.86s, -18.1%, 26.83s -> 21.98s)
  Total Duration           26.83s ->     21.98s   (-4.86s)
  T∞ (observed)            23.70s ->     15.40s   (-8.30s)
  Efficiency Score           1.00 ->       0.84   (-0.16)
  Dispatch Occupancy        27.1% ->      48.3%   (+21.2pp)
```

Then, from a plain shell in the project:

```text
$ bga snapshot --list
4 snapshot(s) in <project>:
  20260819T162249Z
  20260819T162326Z  @prev
  20260819T162455Z  (no run directory - the build produced no elements)
  20260819T162524Z  @last

$ bga analyze @last --format json | head -1
{

$ cd /tmp && bga analyze @last
Error: @last is a snapshot alias, and there is no BuildStream project here to
resolve it against (no project.conf in this directory or any parent). Run it
from inside a project, or pass a path.       # exit 2, same for `compare @prev @last`
```

And the cross-mode refusal, `@prev`/`@last` reaching it exactly as
explicit paths do — here a caches-off snapshot against a warm one:

```text
$ bga compare @prev @last
Refusing to compare these runs (run_mode):
  - baseline is a full run and candidate is a incremental run - their durations
    and floors differ by however much the cache happened to hold ...
exit=6
```

### Where this differs from round 10's numbers, and why

The acceptance asks for "round 10's numbers … IMPROVED, the known −10%".
The **direction and the mechanism reproduce**; the magnitude does not.

| | round 10 (untraced builds) | here (under the Plane 2 capture) |
|---|---|---|
| baseline wall | 27.87s | 26.83s |
| macro-fixed wall | 25.05s (**−10.1%**) | 21.98s (**−18.1%**) |
| Dispatch Occupancy | 29.0% → 59.3% | 27.1% → 48.3% |
| Efficiency Score | 1.00 → 0.86 | 1.00 → 0.84 |

The baselines agree to 3.7% and both signals move the same way by
similar amounts, so this is the same experiment. The delta differs
because these two builds ran **under the tracer** (`--trace-opens` with
`--trace-spine=auto`, the sticky defaults a new project starts at) on a
different machine, and round 10's table came from plain builds. `UX-129`
measured that cost as a range rather than a constant, so a per-run
difference of a few seconds between traced and untraced builds is
expected — it is not evidence that the fix got better. Recorded rather
than reconciled: re-running round 10 untraced would answer it, and
nothing in this item depends on the answer.

## Two bugs the loop found by being run

1. **A fully-cached build crashed the capture.** `load_and_summarize`
   guarded one of its two reads of the invocation record and not the
   other. A build in which no sandbox ran never creates that file — the
   *ordinary* second run of this loop — so the capture died with
   `FileNotFoundError` **after** the build, discarding a report that was
   otherwise complete. Pre-existing in `bga capture run --wrapped-log`;
   invisible until a command made the all-cache-hit case routine.
2. **An incomplete snapshot became `@prev`.** The crash above left a
   directory holding the Plane 2 report and no `run/`, and the next
   comparison failed with *"baseline directory does not exist"* — an
   error about a path the user never typed. `list_runs` now answers what
   `@last`/`@prev` mean; `list_snapshots` still lists everything, and
   `--list` marks the incomplete ones, because the surviving half is the
   expensive half and deleting it is the user's call.

## Deviations, recorded

- **Item 1's "does it by default when the new store is active"** is not
  implemented as a mode switch: `--run-dir` is the flag, and `snapshot`
  always passes it. There is no state in which `capture run` behaves
  differently without being told to — a capture that silently extracts
  depending on where it is run is the kind of implicitness this item
  exists to remove.
- **Item 4's "builders/max-jobs"** are not sticky. They are part of the
  wrapped command (`-- bst --builders 4 …`), which the user retypes
  anyway and which the report already records; storing a second copy in
  `.bga/config` would create two sources of truth for a number
  `bga compare` reads off the run. `--trace-opens` and `--trace-spine`
  are sticky, which is what the item's own example asks for.
- `snapshot` exits with the **wrapped build's** exit code. A compare
  verdict does not change it: the gates live on `bga compare`, which is
  what CI calls, and a regression is not a failure of the snapshot.

## Tests

- `tests/unit/test_run_store.py` — 37: the alias grammar (a bare `@`, and
  a directory really named `@last/run`, stay paths), `@last`/`@prev` by
  stamp and not by mtime, ambiguous and unmatched prefixes, the three
  distinct failure sentences, incomplete captures, and aliases reaching
  `analyze`/`compare`/`cache-trend` with an explicit path still meaning
  itself.
- `tests/unit/test_snapshot.py` — 25, including one `@pytest.mark.bst`
  end-to-end on `examples/01` (~18s) that runs the loop three times: the
  first says what makes a second useful, the second is refused as
  cross-mode, the third compares, and `@prev`/`@last` then resolve from a
  plain shell. Tier pin 36 → 37.
- `tests/unit/test_invocation_correlation.py` — the fully-cached-build
  regression.
- `tests/unit/test_docs_links_and_commands.py` — every `bga <command>`
  the instructional docs tell a reader to type must exist, and the
  guide's quick path must be the two-line loop.

Every guard was falsified: dropping the alias resolution, resolving
against incomplete snapshots, unguarding the invocation-log read,
passing `--trace-spine` as two tokens, and listing the store after the
capture instead of before each turn their tests red.

## Docs

`README.md` and `docs/guides/real-project.md` now teach the two-line
loop first and label the three-command form as the plumbing;
`docs/guides/cli.md` gains a `bga snapshot` section covering the store,
the aliases, the sticky flags and the exit code, and points CI at
`UX-96`'s published refs instead.
