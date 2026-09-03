# UX-590: the context map's non-path claims are unguarded

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-573 (the map that walks the tree git has), UX-274 | **Serves:** every session that reads fixing guide §6 to find where a thing lives | **Topic:** guards

## Motivation

`UX-573` found fixing guide §6 crediting `bga/report/` with a `csv`
renderer it does not have, and dropped the word. Its own Outcome
records why nothing caught it:

```text
UX-0573…md:121   "Dropping `csv` is a doc correction with no guard: the
                  existence direction reads only path-shaped tokens,
                  and a bare `csv` has no path"
```

The guard is `tests/unit/test_the_context_map_is_the_tree.py`. It
holds both directions for anything shaped like a path — every path in
the map exists, every tracked directory reaches the map. A capability
named in prose (`csv`, a flag, a format, a command) is invisible to
it, so §6 can credit the tree with anything that is not spelled with a
slash. That is the class of claim `UX-088` was filed for and the one
`UX-573` found again seventeen rounds later.

## Required Fix

The map's capability nouns derived rather than asserted: a format
named in §6 must appear in the writer's own registry (the
`--format` choices `bga/cli.py` declares), a command named must be a
registered subcommand, and a word in neither is red unless it is on
an explicit prose allowlist with a reason. The `UX-582` shape — the
table is the subject, the guard reads it both ways.

## Out of Scope

- The path directions — they hold and were re-mutated in `UX-573`.
- Prose outside §6 — declined: the map is the claim this item is
  about, and a sweep of every document's capability nouns is a
  different population with a different vacuity floor.

## Acceptance Test

Mutation: re-add `csv` to §6's `bga/report/` row — red naming the
registry it is not in; add a real format to the registry and not to
the map — red the other way.
