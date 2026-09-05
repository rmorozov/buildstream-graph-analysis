# UX-192: the elision that reopened the round-trip

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-178 (reopened for long identities), UX-181 (whose sentence one surface resurrects) | **Topic:** analysis | **Area:** tools

## Motivation

The round-20 review verified all five round-19 landings (nine
mutations reproduced) and found two live defects shipped in the same
commit that closed their classes:

1. **The table's elision breaks the round-trip UX-178 just fixed, for
   exactly the projects the axis targets.** The renderer truncates
   identities over 43 chars (`"..." + identity[-40:]`,
   `bga/report/text.py:358-359`); `known_identity` has no elision
   handling; pasting the printed cell of a 67-char identity resolves
   as a path and answers "rebuilds nothing here" — the verbatim
   round-19 defect, reproduced live, exit 0. Real forge urls
   routinely exceed 43 chars. The acceptance fixture (31 chars)
   passes by staying under the threshold — the passes-on-the-fixture-
   it-was-built-for shape UX-179 was filed about, one round later.
2. **Blast's keying sentence resurrects the pip wrongness one surface
   over**: `format_blast_text` builds the clause from
   `{'kind': answer['resolved_as']}` — `"url"`, never the source kind
   — so a pip resource queried through `bga blast` prints "keys on
   ref: any commit to this rebuilds all of them" (reproduced live),
   the exact sentence UX-181 shipped to remove from the table.

Smaller, same range: blast's matched-identity direct set ignores the
`(kind, identity)` pairing the table groups by (two kinds sharing one
identity merge in blast, split in the table); a junctioned content
identity (`sub.bst:files/libfoo`) is unreachable from its filesystem
form; the scp-colon rewrite still runs on known-scheme urls' *paths*
(`https://host/a:b/c` mangles — the UX-181 log claims otherwise); pip
identity drops the index entirely (one package on two indexes
collapses — the item's own title case, pointing the other way);
`git+http` is missing from `_KNOWN_SCHEMES` while `git+https` is;
the ~13 UX-67 alias commands sit outside both the help caps and the
new parser-coverage guard; `--no-cost` appears in no document.

## Required Fix

1. Either the table stops eliding (widen the column; identities are
   the join key, not decoration) or `known_identity` suffix-matches an
   elided form and the round-trip test gains a >43-char identity —
   the table-stops-eliding direction preferred: a key you cannot
   paste is not a key.
2. The blast answer carries the resource's real kind; `keying_clause`
   receives it; the pip/tar sentences match the table's.
3. The small list, one line each; the UX-181 log's scp claim
   annotated to what the code does.

## Out of Scope

- New identity semantics (UX-181's model stands; these are its seams).

## Acceptance Test

The round-trip test's fixture gains a 67-char url and passes by
pasting the rendered cell; `bga blast <pip-resource>` prints the
pinned-version sentence (mutation: passing `resolved_as` as kind
reddens it); the kind-pairing, junction-path, path-colon, pip-index
and `git+http` cases each get the one assertion the review's
reproduction script already wrote; the alias commands join the help
guard or their exclusion is stated in the guard with a reason;
`--no-cost` appears in cli.md's blast entry.

## What was built

Both live defects reproduced first, on a 68-character identity (a
GitLab subgroup path on a self-hosted forge - the shape the item names):

```text
  ...platform/subgroup/monorepo-of-everything       2    3/3unmeasured
>>> pasting the printed cell: '...platform/subgroup/monorepo-of-everything'
    resolved_as: path  direct_count: 0
>>> the pip resource through blast:
  keys on ref: any commit to this rebuilds all of them, whatever each one stages
```

**1. The table stops eliding** - the preferred direction, because a key
you cannot paste is not a key. An identity wider than the column takes
its own line and the numbers keep their alignment beneath it. The
`3/3unmeasured` collision visible above (the blast and work columns
running together) went with it. After:

```text
  gitlab.example.com/some-org/platform/subgroup/monorepo-of-everything
                                                    2      3/3 unmeasured
>>> resolved_as: url  kind: git  direct: 2
```

**2. The answer carries the resource's kind**, not the reading. `blast`
records `kind` from the matched resource, or from the elements a
heuristic found when they agree; `keying_clause` receives it, so the
pip resource now prints *"keys on the pinned version: a version bump
rebuilds every element that installs this package"*. Where two kinds
answer one spelling the kind is `None` and the keying-only wording is
used - reported as ambiguous rather than guessed.

**3. The small list**, one line each:

- blast groups by the `(kind, identity)` pair the table groups by
  (`sources.resource_key`, public now for exactly that reason).
- A junctioned content identity (`sub.bst:files/libfoo`) matches the
  filesystem path a developer types; the namespaced form still
  resolves exactly.
- The scp-colon rewrite runs only when no scheme was consumed, so
  `https://host/a:b/c` keeps its colon. `UX-181`'s file is annotated:
  it claimed this was already true.
- `pip` identity keeps the index as a suffix, so one package on two
  indexes is two resources; `declared` stays what the recipe wrote.
- `git+http` joined `_KNOWN_SCHEMES` beside `git+https`.
- The seventeen `UX-67` alias commands joined the help guard - the line cap,
  the terminator check and the bracket check all run over them now,
  and the coverage test reads `TOOL_ALIASES` as well as the parser.
  Five were over the cap and are now under it:

  | command | before | after |
  |---|---|---|
  | `native-to-chrome` | 75 | 20 |
  | `run-context` | 67 | 44 |
  | `gen-synthetic` | 67 | 26 |
  | `rebuild-set` | 55 | 19 |
  | `cross-check` | 55 | 18 |

  Four were module docstrings fed to argparse - the exact `UX-158`
  regression, in the half of the surface its guard could not see - and
  got a short `HELP` beside the docstring, which stays. `run-context`
  was flag-help prose instead: four flags carrying a paragraph each,
  cut to a sentence. Eleven help strings gained the terminator the
  `UX-165` check requires.
- `cli.md` gained a `bga blast` entry (it had a one-line mention and
  nothing else), documenting `--no-cost` with its measured price, the
  resolution order, and the always-exits-0 contract.

Tests: 13 new (`tests/unit/test_identity_survives_the_page.py`), two
more in `test_identity_and_junctions.py` for the pip index, and two
docs guards - one pinning the blast entry's content, one asserting
every `--flag` the blast parser accepts appears in it, so the next
flag cannot ship invisible the way `--no-cost` did. Seven mutations,
each red.

**On the acceptance's own terms:** the fixture that passed by staying
under the threshold now carries a 68-character identity and passes by
pasting the rendered cell.

