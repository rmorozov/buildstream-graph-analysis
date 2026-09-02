# UX-178: the tool's own printed identity does not round-trip through blast

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-171/UX-172 (the surfaces), UX-164 (the paste-and-go precedent) | **Topic:** analysis

## Motivation

Round 19, live, on the monorepo fixture. The report prints:

```text
resource                                     direct  blast      work
gitlab.example.com/org/monorepo                   6   8/11       25s
```

and the query one command later:

```text
$ bga blast gitlab.example.com/org/monorepo /tmp/r19-run
  Resolved as a path
  Nothing in this run sources it. Touching it rebuilds nothing here.
```

The table prints the **normalized, scheme-less identity**; the query's
url detector requires a scheme — so the tool's own output, pasted as
its own input, silently resolves as a path and returns a confident
false "rebuilds nothing" **on the exact monorepo question the feature
exists to answer**. With `https://.../monorepo.git` it works and even
names the ambiguity. This is UX-164's paste-and-go class, shipped in
the same range that fixed it elsewhere.

Adjacent edges of the same query, from the round-19 review:

- `bga blast TARGET <dir>` on an **existing directory that is not a
  run** (the likeliest slip: `<snapshot>/` instead of
  `<snapshot>/run`) is a raw `FileNotFoundError` traceback, exit 1 —
  while `analyze` on the same directory prints a clean `Error:` line,
  and UX-172's log claims exit 2 for exactly this.
- A deleted **top-level** file (no `/` in the name) misses the
  path-without-existence heuristic and answers "rebuilds nothing
  here"; and `classify_target`'s comment promises a "no element of
  that name" sentence no code prints.
- "Resolved as **an url**".

## Required Fix

1. **Exact inventory match wins**: before the url/path/element
   heuristics, a target that equals (or normalizes to) a known
   resource identity in the run's inventory resolves as that resource
   — the printed form round-trips by construction, tested by pasting
   the table's own string.
2. The not-a-run directory gets `analyze`'s clean error and exit 2;
   the no-element sentence gets printed or the comment goes; the
   top-level deleted file resolves as a path when the inventory stages
   anything at the root (or the answer says why it cannot tell);
   "a url".

## Out of Scope

- Identity *normalization* correctness (UX-181 carries the mangling
  cases).

## Acceptance Test

A test renders the Shared Sources table on the fixture, extracts the
resource cell verbatim, passes it to `bga blast`, and asserts the same
direct/blast/work numbers — the round-trip, by construction. The
not-a-run directory exits 2 with the clean sentence (mutation:
removing the guard reproduces the traceback). Help and docs lines
unchanged.

## What was built

`known_identity(inventory, target)` in `bga/blast.py`, consulted
*before* the url/path/element heuristics: a target that equals the raw
identity, its stripped form, or `normalize_url(target)` resolves as
that resource. The printed form round-trips by construction rather
than by two heuristics happening to agree. The other readings are
still reported, so an exact match decides the answer without hiding
that the name was ambiguous.

The adjacent edges, all four:

- A directory that is not a run gets `analyze`'s clean sentence and
  exit 2: `Error: <dir> is not a run directory (...). A snapshot's run
  directory is `<snapshot>/run`.` — verified at the shell, `exit=2`.
- `format_blast_text` prints *No element of that name is in this run*
  when the element reading was used and the uid is unknown; the
  comment that promised it no longer promises alone.
- A top-level deleted file reads as a path when the inventory stages
  the project root (`_stages_at_project_root`), and not otherwise —
  the only case where a bare name could be one.
- "a url", from `_ARTICLES`.

Tests: 10 new (`tests/unit/test_printed_identity_round_trips.py`),
including the acceptance's own construction — render the Shared
Sources table on the fixture, extract the resource cell verbatim, feed
it back to `blast`, and assert the same direct/blast/work numbers.
Mutations: dropping the `known_identity` call reddens the round-trip;
removing the not-a-run guard reproduces the raw traceback.
