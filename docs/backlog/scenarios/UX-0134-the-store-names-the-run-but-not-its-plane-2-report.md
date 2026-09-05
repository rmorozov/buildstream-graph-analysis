# UX-134: the store names the run, but not its Plane 2 report

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-126 (the store), UX-51 (`bga correlate`) | **Topic:** store | **Area:** bga

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


---

## What was built

One lookup, three artifacts. `resolve_snapshot(token)` does the work
`resolve` used to do inline and returns the *snapshot*; `resolve` then
names its `run/` and `resolve_plane2` its `plane2.json`. That split is
the whole safety property: **one alias is one snapshot whichever file is
being asked for**, so `bga correlate @last @last` cannot pair one
capture's run directory with another's report — which was the accident
worth preventing.

| argument | command |
|---|---|
| `native_report` (positional) | `bga correlate` |
| `--plane2` | `bga analyze`, and every subcommand sharing its argument set |
| `--baseline-plane2` / `--candidate-plane2` | `bga compare` |
| `--native-report` | `bga cache-logs` |

The first three are threaded in `bga.cli._resolve_run_aliases`, beside
the run-directory arguments. The fourth is not: `bga cache-logs` is
dispatched straight to `tools/` and never reaches that parser, so it
resolves its own — **before** it reads a log tree, so an argument that
cannot be honoured is reported as itself rather than behind whatever the
log-tree lookup happens to say first. Found by a test that expected the
Plane 2 error and got "no element logs found" instead.

### The report is optional when the capture kept the pair together

```bash
bga correlate @last          # not `bga correlate @last @last`
```

Read off the filesystem — is there a `plane2.json` beside a directory
named `run`? — and not off whether an alias was used. So an explicit path
to a snapshot's `run/` behaves exactly as `@last` does, which makes this
a fact about the capture rather than a reward for using the store. The
inferred path is printed to stderr, because a join that silently chose
its own second input would be worse than one that asked.

Where there is nothing to infer the argument is still required:

```text
Error: no Plane 2 report given, and none beside /tmp/bare/run. Pass one, or
point this at a snapshot (`bga correlate @last`), which keeps the run and its
report together.        # exit 2
```

## The acceptance run

Two snapshots of `examples/06` around the macro fix, then, from inside
the project:

| clause | result |
|---|---|
| `bga correlate @last` ≡ `bga correlate <path>/run <path>/plane2.json` | **byte-identical** (see below) |
| `bga correlate @prev @last` — run from one snapshot, report from another | accepted, exit 0 |
| an alias whose snapshot has no `plane2.json` | *"@prev resolves to 20260819T183424Z, which has no plane2.json"*, exit 2 |
| `bga compare @prev @last --baseline-plane2 @prev --candidate-plane2 @last` | `IMPROVED (-10.1%)`, with the memory-envelope note both reports feed |
| `bga analyze @last --plane2 @last` | exit 0 |
| `bga cache-logs . --native-report @last` | exit 0 |
| explicit run directory with no sibling, report omitted | exit 2, named |
| explicit path to a snapshot's `run/`, report omitted | byte-identical to the explicit pair |

**On "byte for byte", precisely.** The two reports are identical when the
paths are spelled the same way. Comparing `bga correlate @last` against
`bga correlate .bga/runs/<stamp>/run .bga/runs/<stamp>/plane2.json`
differs on exactly one line — `Instance:`, which echoes the path as
given, absolute in the first case and relative in the second. That is
`UX-95`'s instance line doing its job, and it separates two explicit
invocations spelled differently just as readily. Against the absolute
spelling `@last` resolves to, `cmp` reports no difference at all.

## Deviations, recorded

- **Item 2 says "when the run directory came from the store"**; this
  infers from the filesystem instead, which is a strictly wider rule —
  the item's own qualifier *"where there is no sibling to infer"* is the
  reading implemented. A user who types the full path gets the same
  convenience, which is more consistent, not less.
- **`bga cache-logs --native-report` was not named in the item**, either
  as required or as out of scope. Included: it is a Plane 2 report
  argument, and leaving one command out would have reproduced this
  item's own complaint one command over.
- The Out of Scope list holds. `--cache-logs` (Plane 3), `--graph` and
  `--history-dir` name artifacts the store does not hold, and take no
  aliases.

## Tests

- `tests/unit/test_run_store.py` — one alias is one snapshot across all
  three resolvers; a snapshot without a report fails by name while its
  run half still resolves; `sibling_plane2` finds, declines, and is not
  fooled by a directory that is not called `run`; every Plane 2 argument
  resolves through the CLI, and a report alias with no report stops
  before any analysis runs.
- `tests/unit/test_correlate.py` — the optional report, end to end
  through `bga.cli`: inferring the sibling produces the same bytes as
  naming it, nothing beside the run says what to pass, and a run
  directory that is not from a capture is not guessed about.
- `tests/unit/test_cache_logs.py` — the alias, the named failure, and an
  explicit path unchanged.
- `tests/unit/test_docs_links_and_commands.py` — the reference no longer
  carries the *"Run directories only"* note, and does document the short
  form it stood in for.

Six falsifications, each red: dropping the CLI resolution, dropping the
file-exists check, resolving the report against a different snapshot than
the run, dropping `correlate`'s inference, inferring from any directory
rather than a `run` one, and dropping `cache-logs`' own resolution.
