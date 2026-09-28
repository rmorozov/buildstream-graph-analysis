# UX-1062: a bundle exports anonymized, and refuses a leftover name

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1060, UX-1061, UX-1067 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), sections 1, 6 and 7; the owner's review on #298, findings 3 and 4, and its follow-up at `8c3bead1`, findings 1 and 2 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

A capture of a private project cannot leave the company today: every
member names elements, paths and the host.

## Required Fix

`bga/bundle.py` gains an anonymized export that walks every
`CAPTURE_LAYOUT` row by the treatment the design's section 7 table
states (keep, transform or drop) and refuses on a row with none. A
transformed member is rewritten by its UX-1060 policy: identifiers
pseudonymized, hashes re-keyed, time shifted to epoch 0, secrets
dropped; a class F field is rebuilt from its grammar or dropped, never
scanned and forwarded; a class B value off its path's allowlist takes
the path's fallback. The export stays unreleased (no documented or
enabled switch) until UX-1063's guard is green. The residue scan runs over the decoded final
archive as a tripwire; nothing is written until the owner approves the
review screen.

## Out of Scope

Raw logs (UX-1066); public names (UX-1065).

## Acceptance Test

`tests/unit/test_an_anonymized_bundle_trips_on_a_leftover_name.py` on the
golden fixtures: no fixture uid, hostname, source path or target name is
found in the decoded archive, and the bundle loads; a fixture with a
private tool, `acme-codegen`, in `plane2.json`'s `by_binary` and its
toolchain string exports it as a `b-` pseudonym. Mutations: plant a
uid in a kept string, and the residue scan refuses; add a row to
`CAPTURE_LAYOUT` with no treatment, and the export refuses; add `acme-codegen` to the binary allowlist,
and the private-tool fixture reds.

## Outcome

**Gap measured** at `c78f10ed`: `export_anonymized` copied member
bytes verbatim. The acceptance test's own name check, run against that
base's `bga/` over the same 14 fixture captures (`/tmp/<track>/gap.py`):
`14 fixtures, 130 of 130 fixture names found in the decoded archive`.

**Close measured.** `bundle.export_anonymized(snapshot, key, pmap,
output=None, *, approve)` (UX-1067's `include_plane2` dropped: ruff PLR0913): refuses a
`CAPTURE_LAYOUT` row with no `disclosure.TREATMENTS` entry, then any
`disclosure.gaps` path over every transform member; rewrites each
document in place through the policy trie (key and list order kept,
map keys of class A/B renamed); packs in memory with neutral headers;
`residue()` scans the decoded archive per member, headers and manifest
included; `approve(review_screen)` must return true before the archive
or the map is written. Classes: A `anonymize.pseudonymize_identifier`
(the one class-A decision: task key `uid|WORD|n`, `.bst` path, URL
with userinfo dropped, path with extension kept); B kept when admitted,
else `b-` (toolchain: `b-<tool> <version>`); D kept except the hostname
path; E `anonymize.rekey_hash` (HMAC, same length); F three command
paths rebuilt by `anonymize.rebuild_command` (grammar of 6.6), every
other F and all G set to `null` (a key a reader indexes survives); H
shifted per clock (`_TIME_AXES`, 9 paths, wall and monotonic, origin
floored to the µs), an undeclared H path refuses. No command reaches it.

`python -m pytest -q tests/unit/test_an_anonymized_bundle_trips_on_a_leftover_name.py
tests/unit/test_an_anonymized_archive_carries_no_original_metadata.py`:
`25 passed in 0.81s` (14 fixture captures walked, exported, loaded).
The anonymized `macro_micro` bundle, loaded, runs `bga analyze` to
exit 0 with `e-cldn.bst` where the critical path named `core.bst`.
UX-1067's test fixture was reshaped to documents the policy clears,
and passes `approve`.

**Mutations**, each on a copy-backed file (`/tmp/<track>/mutate.py`),
reverted from the copy, 23 green after (24 after the flag fix):

| mutation | reddened | count |
|---|---|---|
| `residue` skips `run-context.json` | `test_a_uid_planted_in_a_kept_string_trips_the_residue_scan` | 1 failed, 22 passed |
| `residue` returns no hits | the same | 1 failed, 22 passed |
| `_untreated()` -> `[]` | `test_a_layout_row_with_no_treatment_refuses` | 1 failed, 22 passed |
| `acme-codegen` on `_BINARIES` | `test_a_private_tool_exports_as_a_b_pseudonym` | 1 failed, 22 passed |
| `approve` ignored | `test_nothing_is_written_until_the_owner_approves` | 1 failed, 22 passed |
| disclosure gaps not refused | `test_an_unnamed_path_refuses_the_whole_export` | 1 failed, 22 passed |
| class A passed through | 7 tests, every fixture capture | 20 failed, 3 passed |
| class F kept, not dropped | residue scan trips on prose naming elements | 5 failed, 18 passed |
| no time shift | both time tests | 2 failed, 21 passed |
| commands kept raw | residue scan trips on `core.bst` in a cmd | 5 failed, 18 passed |
| any `--word` flag kept (verifier's leak) | `test_a_private_long_flag_travels_as_a_pseudonym_on_any_binary` | 1 failed, 23 passed |
| wall origin back to 0 | `test_an_anonymized_analysis_still_has_a_start_at_the_canonical_origin`, host-samples test | 2 failed, 23 passed |

UX-1063's guard found a 0 wall start read as no start (`analyzer._run_instance`
drops `started_at`); the wall clock's earliest instant now lands on
`bundle.CANONICAL_ORIGIN_US["wall"]`, 2000-01-01T00:00:00Z. The monotonic
clock stays at 0: its one reader, `utilisation/envelope.py:57`, tests `is None`.

The verifier found `--word` flag names kept verbatim on any `argv[0]`
(`cc1plus --acme-license-server=foo`); now a named flag (`--x`, `-word`,
`-f`/`-m`/`-W`) keeps its name only from `anonymize.PUBLIC_FLAGS`, else
an `m-` pseudonym behind its dashes. A private name equal to a public
word (`toolchain.bst`) is scanned only as its whole value, so its bare
stem in a kept class D string does not trip the residue scan: accepted,
the stem is a public word and carries nothing private.

In passing: `bga/anonymize.py` added to the fixing guide's context map.

**Session decision.** `export_anonymized` ships with no CLI switch:
unreleased until the owner turns it on.
