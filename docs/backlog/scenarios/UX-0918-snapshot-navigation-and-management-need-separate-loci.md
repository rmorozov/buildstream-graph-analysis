# UX-918: snapshot navigation and management need separate loci

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-394 (move between runs), UX-528 (window the store) | **Found by:** round 130 design review | **Serves:** R4, R5 and R7 readers maintaining a project's capture history | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

On the two-run served fixture at 1440×900, the run picker occupies
`x=64.5..287.5`, `y=114.5..188.1` in the sticky rail. At 100 runs the capped
picker adds one typed-id field but the Store section holding the whole-store
facts is about 6,007px away. Adding destructive controls beside the selector
would make navigation and deletion peers and spend scarce rail height on an
occasional administrative task.

## Required Fix

Keep **choose**, **previous** and **latest** as report navigation inside one
compact Run disclosure in the rail. Add one quiet **Snapshots…** link there,
targeting the Store section. Put whole-store count and bytes, the protected
`@last`/`@prev` explanation, and copyable `--list` and prune `--dry-run`
commands beside that section's trend and window statement. Destructive pruning
stays in the CLI, where its explicit command is the confirmation boundary;
the report remains a read-only explanation rather than gaining a mutation
endpoint. Exports omit the served-store controls.

## Decomposition

Input classes: one, 12 and 100 snapshots; current, previous and older runs;
served, export and narrow layouts; whole-store count/bytes and protected runs.
The journey extends switching the report in the rail into understanding and
copying a safe retention command at the Store evidence.

## Out of Scope

Adding per-row delete buttons, moving the run selector out of the rail,
inventing permanent aliases beyond `@last`/`@prev`, or turning the report into
a general file manager.

## Acceptance Test

In a served 100-run store, the closed Run disclosure occupies one rail row;
opening it adds a fixed control set and the capped 12-run chooser.
**Snapshots…** focuses the Store section, where whole-store count/bytes,
protected-set text and copyable `bga snapshot --list` and `bga snapshot prune
--keep 12 --dry-run` commands agree with the CLI. No HTTP mutation route or
per-row delete control exists. Export and one-run cases contain no management
door. Mutation: place Delete beside every run; the fixed-control-count and
locus clauses redden.

## Outcome

Not started. The placement argument and alternatives are in
[`round-130.md`](../../audits/round-130.md).
