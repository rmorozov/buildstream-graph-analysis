# UX-410: a `--project` that is not a project builds one anyway

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-324 (the refuse-before-writing precedent) | **Serves:** R1, on a mistyped path | **Topic:** capture

## Motivation

Found through the round-64 walker's own mistyped relative path: with
cwd already inside example 06,

```text
$ bga snapshot --project examples/06-macro-micro-optimization -- bst build all.bst
```

pointed `--project` at a directory that exists (the phantom
`examples/06-.../examples/06-...` does not — but path resolution
made one) — snapshot created `.bga` under the phantom directory, ran
`bst` with that cwd, and **bst walked up to the real project.conf
and built the parent project**. Green snapshot, store in a directory
the user never meant, measuring a build of a project the flag never
named. `bga doctor` checks for `project.conf`; `bga snapshot` does
not.

## Required Fix

`snapshot` (and `capture`) verify `--project` contains a
`project.conf` before writing anything — the `UX-324` rule applied
to the flag: refuse with the sentence naming the path checked and
the nearest ancestor that *does* hold a `project.conf`, and create
no directory on the refusal path.

## Out of Scope

- Following bst's walk-up semantics on purpose — if someone wants
  the enclosing project they can name it; silently measuring a
  different project than the flag names is the defect.
- The relative-path Plane 2 forfeiture — same walk, different
  mechanism: that is `UX-405`.

## Acceptance Test

- The invocation above refuses, names the checked path, and leaves
  no `.bga` behind (byte-for-byte directory listing, `UX-324`'s
  clause).
- Falsification: skip the check — the refuse-and-write-nothing
  guard goes RED.
