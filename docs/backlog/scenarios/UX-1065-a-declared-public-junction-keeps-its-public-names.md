# UX-1065: a declared public junction keeps its public names

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1062 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 5 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

**Guard:** test_a_public_junction_keeps_only_public_names.py

## Motivation

Knowing an element is freedesktop-sdk's `gcc.bst` is worth more than
hiding a public name, but `bga` offline cannot tell a public junction
from an internal fork of one.

## Required Fix

The store's config names public junctions; a name list is built from a
public checkout on disk at a named tag; a name passes through only when
it is under a declared junction **and** in that list. Nothing declared,
nothing passes. The export says which junctions passed.

## Out of Scope

Guessing publicness from a source URL.

## Acceptance Test

`tests/unit/test_a_public_junction_keeps_only_public_names.py`: a
fixture with a declared junction and one element added "in a fork" -
the public element keeps its name, the added one is pseudonymized.
Mutation: drop the list intersection, and the fork's element leaks.

## Decision

Route:     `.bga/config` (JSON, run_store.read_config bga/run_store.py:461; tools/bga_snapshot.py:735 _sticky_config keeps unknown keys) gains `"public_junctions": {"<junction>.bst": {"checkout": "<dir>", "tag": "<tag>"}}`.
Route:     new bga/public_names.py builds the list offline: `git -C <checkout> rev-parse <tag>^{commit}` (refuse if absent); element-path from `git show <tag>:project.conf` by read_scalar_key's rule (tools/bst_native_build_tracer.py:484, via tools_dispatch._import_tool), default `elements`; `git ls-tree -r --name-only <tag> -- <element-path>`, `*.bst`, prefixed `<junction>:`. The tag's tree, never the working tree.
Route:     anonymize passes a class-A element name through only when it carries a declared junction's prefix and is in that list; kept out of the map and residue dictionary; paths, URLs, refs under it still pseudonymized; manifest lists {junction, tag, names_passed}.
Rejected:  guessing from the source URL; reading the working tree; a YAML parser for project.conf; a CLI flag (config is hand-edited; a later row).
Files:     bga/public_names.py · bga/run_store.py (`public_junctions(project)`) · bga/anonymize.py · bga/bundle.py · tests/unit/test_a_public_junction_keeps_only_public_names.py
Guard:     tests/unit/test_a_public_junction_keeps_only_public_names.py: git init + tag a copy of tests/fixtures/bst_show_project/subproj in tmp_path, add forked.bst to the working tree and a later commit; capture holds subproj-junction.bst:libfoo.bst and :forked.bst; libfoo keeps its name, forked gets e-, nothing declared pseudonymizes both, manifest names junction and tag.
Mutation:  drop the list intersection, forked leaks; list the working tree instead of ls-tree <tag>, it leaks.
Class:     product
Split:     one track after UX-1061 and UX-1062.

## Outcome

Gap measured: before this task no `.bst` name ever survived export -
`test_an_anonymized_bundle_trips_on_a_leftover_name.py` packs 14+
fixtures and every element uid comes back a pseudonym; a fork of a
public subproject looked identical to the subproject itself.

Close measured: `pytest tests/unit/test_a_public_junction_keeps_only_public_names.py
-q` → `2 passed in 0.76s`. `libfoo.bst` (tagged) survives verbatim under
`subproj-junction.bst:`; `forked.bst` (added after the tag) comes back
`subproj-junction.bst:e-....bst` - the junction name stays (it is the
declared-public fact), the fork's own element name does not. With
nothing declared both are pseudonymized (`test_nothing_declared_pseudonymizes_both`).
`python3 tools/dev_touching.py --base 7bd141a2 --loud`: 2372 passed, 12
skipped. `python3 tools/dev_sizes.py --check`: `sizes ok: 154 file(s)
measured`. `python3 tools/dev_close_task.py --check`: `0 problem(s)
over 8 propert(y/ies), 1027 backlog row(s)`.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `bga/bundle.py`: `if value in self.public:` → `if True:` (drop the list intersection) | both guard tests | 2 failed / 2 |
| `bga/public_names.py`: `ls-tree ... tag` → `ls-tree ... HEAD` (working tree, not the tag) | `test_the_tagged_name_passes_and_the_forked_one_does_not` | 1 failed / 2 |

Deviation: the Decision's Files line named `bga/anonymize.py` as
touched; the pass-through and the junction-only-literal case were both
put in `bundle.py`'s `_Anonymizer._element_name` (its one caller, per
the Decision's own parenthetical) instead, so `anonymize.py` is
unchanged. The Decision did not say whether an unlisted element under a
declared junction keeps the junction name literal or gets a fresh `j-`
pseudonym for it too; the literal case was necessary - pseudonymizing
it collided the residue scanner against the same junction name kept
verbatim by a listed sibling - and matches the Motivation ("knowing an
element is freedesktop-sdk's `gcc.bst`... ").

**Session decision.** A public name whose stem equals a private
element's stem elsewhere in the same capture makes the residue scan
refuse the whole export, with a generic message: fails closed.
