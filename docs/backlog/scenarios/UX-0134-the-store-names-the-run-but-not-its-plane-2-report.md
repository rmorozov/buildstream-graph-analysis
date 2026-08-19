# UX-134: the store names the run, but not its Plane 2 report

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-126 (the store), UX-51 (`bga correlate`)

Filed while revising the docs after `UX-126` landed, from the sentence
the CLI reference could not write without an apology.

## Motivation

`UX-126` made every argument that names a *run directory* accept
`@last`, `@prev` and `@<stamp-prefix>`, and a snapshot holds the run and
its Plane 2 report side by side:

```text
.bga/runs/20260819T162326Z/
  run/            <- @last resolves here
  plane2.json     <- and this has no name
```

But the three arguments that take a Plane 2 report — `bga correlate`'s
positional `native_report`, `bga analyze --plane2`, and
`bga compare --baseline-plane2`/`--candidate-plane2` — are still paths.
So the two-plane join, which is the one place both artifacts are needed
at once, is the one command the store does not finish:

```bash
bga correlate @last .bga/runs/20260819T162326Z/plane2.json
```

That is the exact shape `UX-126` was filed against: half the invocation
is named and half is a path the user has to go and read off a listing.
Worse, it is the invocation where getting it wrong is most expensive —
joining yesterday's report to today's run is `UX-126`'s own headline
example of a mistake the refusals catch only *after* a long build, and
`bga snapshot` already knows which report belongs to which run.

`bga snapshot` itself is unaffected: it passes both `--baseline-plane2`
and `--candidate-plane2` from the store already, because it has them.
This is only about the commands a user types afterwards.

## Required Fix

1. A Plane-2-report argument that is a snapshot alias resolves to that
   snapshot's `plane2.json`, so `bga correlate @last @last` and
   `bga compare @prev @last --baseline-plane2 @prev
   --candidate-plane2 @last` work. Same grammar, same failures — an
   alias naming a snapshot with no `plane2.json` says so by name rather
   than as a missing path, the way an incomplete capture is already
   excluded from `@last` (`UX-126`).
2. Better, for `correlate` specifically: when the run directory came
   from the store and the report argument is omitted, take the sibling
   `plane2.json`. The snapshot knows the pairing; asking the user to
   restate it is the clerical step this whole direction exists to
   remove. Keep the argument required for an explicit path, where there
   is no sibling to infer.
3. The CLI reference's *"Run directories only"* note goes away, rather
   than being reworded.

## Out of Scope

- Any change to what a Plane 2 report is, or to how `correlate` joins
  the planes. This is resolution, exactly as `UX-126` was.
- Aliasing anything that is not a run directory or a Plane 2 report —
  `--cache-logs`, `--graph` and `--history-dir` name artifacts the store
  does not hold.

## Acceptance Test

Inside a project with two snapshots: `bga correlate @last` produces the
same report as `bga correlate <path>/run <path>/plane2.json`, byte for
byte. `bga correlate @prev @last` — a run from one snapshot and a report
from another — is accepted, because it is a legitimate thing to ask for
and the join's own coverage line already says what it measured. An alias
naming a snapshot whose capture produced no `plane2.json` fails by name.
The docs-commands test covers the new form, and the CLI reference's note
about run directories only is deleted.
