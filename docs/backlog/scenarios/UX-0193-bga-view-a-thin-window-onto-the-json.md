# UX-193: `bga view` — a thin window onto the JSON

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** Direction 7 (the argument), UX-190 (the schemas this renders)

## Motivation

The user's request, round 21: the reports have outgrown the terminal —
*"we are on the verge of necessity for making a viewer"* — and the
design constraint that keeps a viewer maintainable is argued in
Direction 7: **the published JSON is the entire interface**. The
viewer renders the schema, not the report; anything it should show
must first exist in `analyze/v1`/`compare/v1`/`blast/v1`, which is
also what lets any external TypeScript library chart the same data
without bga blessing a frontend stack.

## Required Fix

1. **`bga view [RUN]`** (`@last` default, the alias grammar):
   `http.server` on `127.0.0.1`, ephemeral port, `webbrowser.open`,
   `--port`/`--no-browser`. Serves the static page, the run's JSON
   payloads (produced through the same `main()`s the CLI uses, cached
   beside the run), and the chrome trace. Path allowlist — the run's
   own files only; no listing; nothing writable.
2. **The page**: vanilla ES modules checked into the repo, **no node
   toolchain, no build step**. Sections render generically from the
   schema: arrays with column hints → sortable tables; `findings[]` →
   the findings list with severity styling; deltas with direction
   semantics → signed, colored numbers. The verdict banner gives
   refusals (`NOT COMPARABLE`, interrupted, suspended) visual weight.
   A new report field renders with zero viewer changes — that
   property is the acceptance's core.
3. **View-hints v1 in the schemas**: `bga:quantity`
   (duration_us / bytes / share / count), `bga:severity` on findings,
   column order hints — a small vocabulary documented beside Part
   32's output schemas, versioned with them (UX-190's rules apply).
4. Help under the UX-158 cap; one docs section in `cli.md`; the
   README's real-project flow gains one line (`bga view @last` after
   the first snapshot).

## Out of Scope

- The Perfetto handoff (UX-194), export mode (UX-195), comparative
  views (UX-196).
- Any bundler, framework, or npm dependency (Direction 7's rule; a
  richer TS app would be a *consumer* of the schema, not part of
  this).

## Acceptance Test

`bga view @last` on `examples/06` serves a page whose findings,
tables and verdict match `--format json` field-for-field (asserted by
a headless fetch of the served JSON and a DOM-free parse of the
rendered data attributes — no browser dependency in CI). The
zero-viewer-changes property is the discriminating test: add a
synthetic field with hints to a fixture payload and assert it renders
(appears in the served page's generic section) with no viewer-code
change. The server refuses a path outside the run (asserted), binds
localhost only, and `--no-browser` prints the url instead of opening
it. Schemas with hints still validate the golden runs (UX-190's
guard unchanged).
