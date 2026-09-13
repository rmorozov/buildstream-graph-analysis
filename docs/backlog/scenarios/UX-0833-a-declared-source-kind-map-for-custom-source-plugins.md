# UX-833: a declared source-kind map for custom source plugins

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-192 (the source kind behind a heuristic), UX-683 (a declaration in project.conf) | **Found by:** round 115, the design review | **Serves:** R2 whose sources come through a custom plugin | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`bga/blast.py:202` names the source kind behind a resource-blast
match by heuristic over the kinds BuildStream ships. A project whose
elements fetch through a custom plugin — a Gerrit source, an internal
mirror — matches nothing, and the blast for a change to that source is
unreported rather than wrong.

## Required Fix

A declaration beside `bga-foundation`: `variables: {bga-source-kinds:
"gerrit=git"}` maps a plugin kind onto the shape the heuristic already
reads (git-like: `url` + `ref`; tar-like: `url` + `sha`), validated at
extraction; an unmapped custom kind is reported as such in
`element_join_coverage`, never silently skipped. Judgement: whether the
map is by kind or by field names is the design question the task
answers first.

## Decomposition

Input classes: a mapped custom kind, an unmapped one, a project with
no declaration (today's behaviour byte for byte); the journey is R2's
resource-blast question in the answer key.

## Out of Scope

- Writing plugin-specific readers — the map is the mechanism; a reader per plugin is what it avoids.
- Resource blast for non-source resources — out of `blast.py`'s question.

## Acceptance Test

A fixture with a `gerrit` kind mapped to `git` produces the same
resource-blast rows as the same element with kind `git`; unmapped, the
coverage block names the kind.

## Outcome

**Gap measured.** Before: `keying_of(kind)` took no map, so a `gerrit`
stanza always resolved `KEYING_BY_KIND.get("gerrit", "unknown")` →
`"unknown"`, and nothing published *which* kind that was - `grep
unknown bga/sources.py` found only the per-row `keying_clause` sentence,
no aggregate list; `resource_blast` (the block the sources inventory
publishes) carried no count or name for it either.

**Close measured.**
`python3 -m pytest tests/unit/test_a_declared_source_kind_maps_onto_a_known_one.py -q`
→ `10 passed in 0.75s`. `dev_refresh_analysis.py --write` moved
nothing in the two committed fixtures - true byte-for-byte. Verifier
hold: the first nine tests called `bga/sources.py` directly, never
`bga/cli.py`'s `_attach_resource_blast` or `bga/report/json.py`'s
publish gate - both mutated clean past a green suite. Added
`TestTheCoverageReachesTheCliOutput`: copies `with_timeline/run`, adds
one `gerrit` element with no shared resource to its `sources.json`,
runs the real `PYTHONPATH=<worktree> python3 -m bga.cli analyze <run>
--format json` subprocess, asserts `resource_blast.rows == []` and
`unmapped_source_kinds == ["gerrit"]` - `0.48s` solo.

**Mutation table** (falsify skill, reverted from
`/tmp/.../scratchpad/r116/agent-a7377fcb68339838a/snap/` and `snap2/`,
re-confirmed green after each):

| mutation | file | reddened | count |
|---|---|---|---|
| `keying_of` drops `kind_map`, reads bare `kind` | `bga/sources.py` | `test_a_mapped_gerrit_element_blasts_like_git`, `test_a_mapped_kind_never_appears_unmapped` | 2 |
| `unmapped_kinds` returns `[]` unconditionally | `bga/sources.py` | `test_the_coverage_block_names_the_unmapped_kind` | 1 |
| both `bga-source-kinds` validations disabled | `tools/bst_extract_run.py` | `test_a_right_side_naming_no_known_kind_raises`, `test_an_entry_with_no_equals_sign_raises` | 2 |
| `unmapped_source_kinds` hardcoded to `[]` | `bga/cli.py` | `test_an_unmapped_kind_with_no_shared_resource_still_publishes` (`resource_blast` absent entirely) | 1 |
| gate reverted to `if blast.get('rows'):` | `bga/report/json.py` | same test - `resource_blast` absent | 1 |

No guard failed to discriminate; each reddened only the assertion its
mutation targeted.

**Deviation from the Decomposition:** two undeclared surfaces moved to
make the coverage reach the reader - `bga/cli.py` and
`bga/report/json.py`'s publish gate (`rows or unmapped_source_kinds`).
`tests/quality_baseline.json` gained one renamed forced-ignore entry
(`resource_of_source`'s pre-existing C901) under reason `UX-833`;
three unrelated findings already `new` on the unmodified base
(`bga/analyzer.py` pyright, `tools/dev_perfetto_queries.py` S105 ×2,
confirmed via `git stash` against `e81cc62f`) were left untouched.
`make test-touching` reddened four pre-existing, confirmed-unrelated
tests (a ledger count, an undocumented `start_offset_us`, two
`TestTheSizeDiscipline` path-length overages) plus this task's own
spread figure, fixed by `dev_touching.py --spread --write`.
