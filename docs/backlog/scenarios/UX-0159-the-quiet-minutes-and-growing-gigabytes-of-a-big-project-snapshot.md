# UX-159: the quiet minutes and growing gigabytes of a big-project snapshot

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-126 (snapshot), UX-113 (the census), UX-155 (scratch, whose store this sizes) | **Topic:** capture | **Area:** tools

## Motivation

The first real deployment is a project big enough that one capture is
a multi-hour session, and two small-project comforts stop holding:

1. **The quiet minutes.** Between `Capturing into <dir>` and
   BuildStream's first line, snapshot compiles the hook and spine and
   — under the default `--trace-spine=auto` — runs the census: a walk
   of every element's local sources plus the declared-deps resolution
   (`census_spine_verdicts`, `tools/bst_native_build_tracer.py:1916`),
   all of it silent, all of it scaling with project size. After the
   build, extraction shells out to `bst show` and analysis runs — also
   silent. On `examples/06` these are sub-second and invisible; on a
   big project the user watches nothing happen for however long they
   take, twice per session, with no way to tell "working" from
   "hung". (This is not the build's own progress — bst streams that
   fine — it is bga's *own* phases.)
2. **The growing gigabytes.** A run directory scales with process
   count (`plane2.json` is ~5 KB/process measured on `examples/06`;
   opens multiply it), and every snapshot keeps one forever. The only
   management is `_warn_if_large` at 2 GB
   (`tools/bga_snapshot.py:315`): a note advising the user to delete
   directories by hand. `--list` does not show sizes, so they cannot
   even see which snapshot is the 1.8 GB one, and there is no command
   that deletes anything.

## Required Fix

1. **One line per bga phase, when it starts**: `Assessing N elements
   for static binaries...`, `Extracting run data (bst show)...`,
   `Analyzing...` — stderr, one line each, no progress bars. The rule:
   any bga-owned step that can plausibly take >5s on a big project
   announces itself, so silence always means "the build is running".
2. **`bga snapshot --list` shows per-snapshot size** (`du`-style,
   humanized) and the total, replacing the bare listing.
3. **`bga snapshot prune`**: `--keep N` (newest) and
   `--older-than DAYS`, refusing to delete `@last`/`@prev` and
   anything a `.bga/config`-recorded baseline points at; prints what
   it deleted and how much space it freed. `_warn_if_large` then names
   the command instead of advising hand-deletion.

## Out of Scope

- Compressing or trimming `plane2.json` itself (a format change; the
  win here is visibility and a delete button, not a smaller byte).
- Build-progress reporting (BuildStream already streams its own).

## Acceptance Test

On `examples/06`: the phase lines appear in order in a live snapshot's
stderr; `--list` shows a size per snapshot and a total matching `du`
within rounding; `prune --keep 2` on a store of five deletes three,
never the two aliased ones, and reports the freed bytes; the
`_warn_if_large` text names `bga snapshot prune`. The docs-commands
test covers the new `--list`/`prune` lines in `real-project.md`.

---

## What was built

**The quiet minutes.** Each bga-owned phase announces itself on stderr,
one line, no progress bars:

```text
Capturing into /tmp/p/.bga/runs/20260820T124201Z
Compiling the trace hook...
Assessing 11 element(s) for static binaries...
Census: 11 of 11 element(s) assessed, 0 with static binaries (spine traced)
...
Analyzing the captured trace...
Extracting run data (bst show)...
```

The rule: any step that can plausibly take >5s on a big project says so,
so silence always means the build is running.

**The growing gigabytes.** `--list` shows a size per snapshot and a
total; `bga snapshot prune` takes `--keep N`, `--older-than DAYS` and
`--dry-run`. It never deletes `@last`, `@prev`, or a recorded baseline -
a prune that removes the baseline turns the next comparison into a
first-snapshot message. The 2 GB warning names the command.

Measured on a five-snapshot store: `--list` totals 3.1M against
`du --apparent-size` 3.2M (bga sums file bytes; `du` also counts
directory entries), and `prune --keep 2` deleted three, kept the two
aliased ones, and reported 1.9M freed.

### Deviation, recorded

The task's example lists "Extracting..." before "Analyzing...". The code
runs them the other way round - the Plane 2 analysis precedes the Plane 1
extraction - so the lines print in the order the work happens rather than
in the order the example wrote them.

`prune`'s own flags needed their own parser: `cmd` is
`argparse.REMAINDER`, so everything after the first positional is
swallowed verbatim. `--keep` reached `_prune` as `None` before that was
handled, and a test pins it.
