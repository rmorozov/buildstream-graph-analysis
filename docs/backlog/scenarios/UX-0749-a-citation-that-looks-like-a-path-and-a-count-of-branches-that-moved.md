# UX-749: a citation that looks like a path, and a count of branches that moved

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-189 (the archive branches), UX-122 (stale refs nothing catches) | **Serves:** the reader who clicks, or counts | **Topic:** docs | **Area:** unassigned | **Shape:** bounded

## Motivation

Two unguarded sentences, both found by running a command against them.

**Nine citations formatted as paths that do not resolve.** `cli.md`
writes `` `docs/backlog/scenarios/UX-01` `` — and `UX-27`, `UX-39`,
`UX-40`, `UX-78`, `UX-87`, `UX-96`, `UX-111` — at lines 1964, 1975,
2002, 2006, 2016, 2410, 2458 and 2463-2465. None is a file:

```console
$ ls docs/backlog/scenarios/UX-01
ls: cannot access 'docs/backlog/scenarios/UX-01': No such file or directory
```

The real names are zero-padded, which `docs/contributing/style-guide.md`
§9 states outright: *"Backlog filenames are zero-padded; identifiers are
not"* — the citable form is bare `UX-27`. `real-project.md` follows it,
linking the bare id to the zero-padded filename; `cli.md` follows it
too at `:357` and `:612`, so the pseudo-path form is inconsistent with
the same file. Neither guard sees it: the link guard reads
only true markdown link syntax, and `_MD_NAME` only admits a backtick span ending
`.md`.

**A count of published branches that has doubled.** `README.md:14` says
*"**eight** `captures/*` branches"*:

```console
$ git ls-remote --heads origin 'captures/*' | wc -l
12
```

`test_a_clone_without_the_archive.py` runs against a synthetic
two-branch repo and checks the *mechanism* — narrow fetches none, wide
fetches all, narrow is smaller. It never reads the live count, and its
docstring dates the eight to round 20. `real-project.md:226` carries
the same eight.

## Required Fix

The citations take the form §9 already states — bare `` `UX-27` ``, or
a real link where the reader is meant to follow it — and the backtick
guard's population widens to a span matching `docs/backlog/scenarios/`
whether or not it ends `.md`, so the next one reds.

For the branch count, decide and record which: the sentence drops the
number (the mechanism is the point, and a capture job may add branches
at any time), or it derives one from `git ls-remote --heads origin
'captures/*'` at the same place the other derived figures are written.
Do not simply retype 12.

## Out of Scope

- The clone guard's mechanism tests (`UX-189`), which are right and
  pass; **declined** as a target here — this row is the count beside
  them, not the check.
- `UX-122`'s ref globs, closed, a different surface.

## Acceptance Test

Every backticked span under `docs/backlog/scenarios/` in every guide
resolves to a file or is not written as a path; the branch sentence
carries no bare count, or one a command reproduces. Mutation: write
`` `docs/backlog/scenarios/UX-02` `` into a guide — red, naming it.

## Outcome

**Gap measured.** `cli.md` cited nine pseudo-paths under
`docs/backlog/scenarios/` — `UX-1`, `UX-3` (×2), `UX-27` (×2, one
inside a working link's text), `UX-39` (×2), `UX-40`, `UX-78`, `UX-87`,
`UX-96`, `UX-111` — at lines 1964, 1975, 2002, 2006, 2016, 2410, 2458,
2463, 2464 (three ids on one line), 2465; all nine resolve to real,
zero-padded files under `docs/backlog/scenarios/`. `README.md:14` and
`real-project.md:226` both said "eight `captures/*` branches";
`git ls-remote --heads origin 'captures/*' | wc -l` said **12** on
2026-09-07.

**Close measured.** All nine pseudo-paths rewritten to the bare form
§9 states (`UX-1`, `UX-3`, `UX-27`, `UX-39`, `UX-40`, `UX-78`, `UX-87`,
`UX-96`, `UX-111`), matching `cli.md`'s own convention at `:357`/`:612`.
Both branch-count sentences now read "twelve as of 2026-09-07" with
the `git ls-remote` command inline, dated per `UX-511`'s pattern — no
guard added, since a guard reading the live remote needs the network.
`test_every_backticked_markdown_name_resolves` widened with
`_SCENARIO_PSEUDO_PATH` (`docs/backlog/scenarios/[\w.+-]+`, applied
only when `_MD_NAME` does not already match) so a bare-prefix pseudo-
path reds; a directory reference (`examples/README.md`,
`.claude/agents/researcher.md`, both citing the bare
`` `docs/backlog/scenarios/` `` with no glob or content after the
slash) and a real, zero-padded full-path citation (`cli.md:357`,
`:612`) both still pass — checked, not silently exempted.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `` `UX-1` `` → `` `docs/backlog/scenarios/UX-02` `` in `cli.md:1964` | `test_every_backticked_markdown_name_resolves` | 1 dangling span reported, naming `docs/guides/cli.md:1964 -> \`docs/backlog/scenarios/UX-02\`` |

Reverted from the pristine copy in the scratchpad (not
`git checkout --`); `test_docs_links_and_commands.py` (56 tests) green
after revert.

### The shape the widened guard still does not reach

`` `docs/backlog/scenarios/UX-01#section` `` — a pseudo-path carrying a
markdown anchor — passes unflagged: `#` is in neither `_MD_NAME`'s nor
`_SCENARIO_PSEUDO_PATH`'s character class. That matches `_MD_NAME`'s own
stated exclusion ("no `#anchor` — links own those"), so it is the prior
design rather than a regression, and the sweep found no such span in the
tree. Recorded as a latent gap, not fixed here.

The verifier's other note was the Register: the new constant's comment
ran six lines against the one-line cap, with its rationale already in
this file. Trimmed to two; `test_the_register_is_terse.py` green.
