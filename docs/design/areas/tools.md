# The tools area

Moved from [`docs/design/architecture.md`](../architecture.md)'s
Plane 3 chapter (`UX-810`); no line inside it is read by a guard, so
nothing else stays behind. Later chapters on `tools/` join this page
as they are filed.

## Plane 3: BuildStream's own persisted logs (`UX-91`)

BuildStream writes a per-element log for every task it runs, and keeps
them: `$XDG_CACHE_HOME/buildstream/logs/<project>/<element>/<key>-<action>.<timestamp>.log`.
They were sitting on every developer's machine, unread by anything.

`bga cache-logs PROJECT_DIR` reads them. It is the only
part of this tool that needs **no capture, no flags and no foresight** —
the evidence is a by-product of builds that already happened, including
builds nobody thought to instrument.

What that buys, and what it costs:

- **Per-element phase breakdown.** Each log carries BuildStream's own
  timed activities — `Staging dependencies`, `Integrating sandbox`,
  `Running commands`, `Caching artifact` — at one-second resolution.
- **The sandbox tax** (`UX-99`): how much of each element's time went to
  staging, integrating and caching rather than to the build itself. On
  freedesktop-sdk it is **13.0s of 4409.0s (0.3%)** — and the answer
  being *small* is the point: the toll is what the merge half of the
  granularity advice is computed from (`UX-100`), and a project where it
  is 0.3% has no elements that are too small to be worth their own
  sandbox.
- **The configure tax** (`UX-102`): what the build tools themselves say
  they spent answering configure questions. Counted only where the build
  tool reports it — cmake does, autotools' `configure` and meson do not
  — so on an autotools project this is a floor of zero rather than a
  measurement, and the report says so and points at Plane 2's traced
  view instead. With `--native-report`, both figures are shown per
  element, side by side and **never summed**: one is wall-clock the tool
  self-reported, the other is CPU seconds traced, and adding them would
  invent a quantity.
- **The developer tax** (`UX-101`): which elements this project has spent
  the most time rebuilding, across every build in the tree. With
  `--graph` it can separate a rebuild caused by an upstream key change
  from one whose own definition changed — the logs alone carry no
  dependency edges.

The costs are stated in the report itself, every time: one-second
resolution, no `--builders`, no `--max-jobs`, no scheduler context, no
timestamps inside `Running commands`, and **no session id** — a log's
header is its own task's start, not its build's, so the number of builds
is a lower bound taken from the most-rebuilt element, never a count.
Nothing in Plane 3 may feed a certified floor, and the report says that
too.
