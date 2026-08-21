# UX-192: the elision that reopened the round-trip

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-178 (reopened for long identities), UX-181 (whose sentence one surface resurrects)

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
