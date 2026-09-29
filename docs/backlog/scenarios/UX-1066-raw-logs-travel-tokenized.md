# UX-1066: raw logs travel tokenized

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-1062 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 7 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_raw_log_travels_tokenized.py`

## Motivation

Stage one drops `plane2.log.gz`, `build.log` and `capture-context.txt`.
The owner scheduled it on 2026-09-29.

## Required Fix

`bga/anonymize.py` tokenizes the three raw members: allowlisted
`argv[0]` basenames, flag names and public macro names kept;
path and identifier values, private macros and private tool names
pseudonymized; the residue scan covers them.

## Decision

Route:     move the three raw members in disclosure.TREATMENTS from DROP to TRANSFORM under a line policy. anonymize.py gets a line tokenizer: `cmd=` through the existing `rebuild_command`, element names through `pseudonymize_element_path`, paths and identifiers through `pseudonymize_identifier`, all with the same key and pmap so the planes still join after renaming. bundle._anonymized_members streams text members, inflating and re-deflating `.gz`. `residue()` inflates a gzipped member before scanning (today it reads compressed bytes and sees nothing inside plane2.log.gz).
Rejected:  shipping the logs verbatim (Out of Scope) · keeping them dropped (the owner asked for all open rows) · a separate raw-log pseudonym map (the timeline join needs the same names in every member).
Files:     bga/anonymize.py, bga/disclosure.py, bga/bundle.py (_anonymized_members, residue), docs/design/anonymized-bundle.md (section 7 table row), tests/unit/test_a_raw_log_travels_tokenized.py
Guard:     on `with_timeline`: the timeline renders from the anonymized bundle, and no original token from the dictionary remains in any member, the inflated plane2.log.gz included.
Mutation:  skip tokenizing `cmd=` (the scan refuses); scan plane2.log.gz without inflating it (the planted token gets through).
Class:     product

## Out of Scope

Keeping a log verbatim.

## Acceptance Test

`tests/unit/test_a_raw_log_travels_tokenized.py` on the `with_timeline`
fixture: the timeline renders from the anonymized bundle and no original
token remains. Mutation: skip tokenizing `cmd=`, and the scan refuses.

## Outcome

**Gap measured.** At `b8072cd7`, `disclosure.TREATMENTS` mapped `plane2.log.gz`,
`build.log` and `capture-context.txt` to DROP; `export_anonymized` listed all
three under `dropped:` and `residue()` read compressed bytes of any `.gz`
member, seeing nothing inside.

**Close measured.** `python3 -m pytest tests/unit/test_a_raw_log_travels_tokenized.py -n 0`
on `with_timeline` plus a planted `build.log`, `capture-context.txt` and
`plane2.log.gz` (private dir, file, macro, tool, host token, three uids):
6 passed. The export ships all three; no planted token survives in any decoded
member, the inflated log included; START/END, `pid`, `ppid`, `ts` and `exit`
survive; `render()` on the loaded bundle returns `planes == ["1", "2"]`, so the
uid pseudonym in `plane2.log.gz` equals the one in `build.log` and `graph.json`.

| Mutation | Red |
|---|---|
| `tokenize_line`: `found = None` (skip `cmd=`) | 2 failed: shape test (`" cmd=b-"` absent), rebuilt-command test |
| `residue`: never inflate a `.gz` member | 1 failed: `test_the_residue_scan_reads_inside_a_gzipped_member` |

The first mutation alone leaves the export green under the residue scan: the
word fallback pseudonymizes the same tokens, so the scan never sees them. The
shape assertion is what discriminates it.

**Deviation.** Timestamps in the three logs (`ts=`, `wall=`, the wrapper
stamp) travel verbatim, not shifted to epoch 0 (class H): the Decision names
no time policy. The timeline still renders both planes in the guard (it aligns on an
anchor element); whether a reader wants the stamps shifted is undecided. `disclosure.LINE_MEMBERS` is new and
the existing every-transform-has-a-policy test skips it.
