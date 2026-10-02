# UX-1295: `bga bundle --export` has an `--anonymize` switch, so a pilot can share a capture without a Python call

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1062, UX-1063 | **Found by:** the owner, 2026-10-02: "have we introduced bundle anonymize switch? without it pilot maybe is not as smooth" | **Serves:** R4, R5 | **Topic:** cli | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_bundle_export_has_an_anonymize_switch.py

## Motivation

`bundle.export_anonymized` (`bga/bundle.py:803`) and the twelve rows
behind it (UX-1060..1071) are Done, but no command reaches it: UX-1062
shipped it "with no CLI switch: unreleased until the owner turns it
on", gated on UX-1063's commutation guard, which is now green.
`bga bundle --help` offers `--export`, `--load`, `--resolve` and
`--no-plane2` only. A pilot team that wants to send a capture out has
no way to anonymise it short of calling Python.

## Decomposition

Input classes: a TTY (the review screen, then y/N); no TTY and no
approval (refused, nothing written, the review printed); a residue hit
(refused whatever the approval); a project with no key yet (created
under `.bga/anon/`, 0600); `--anonymize` with `--load` or `--resolve`
(usage error). Journey: `bga bundle --export @last --anonymize`, send
the file, `bga bundle --resolve --key-fingerprint FP` on the answer.

## Required Fix

`bga bundle --export STAMP --anonymize [-o FILE]` calls
`export_anonymized` with the project's key and map, shows
`review_screen` and asks on a TTY. Unattended approval follows the
owner's decision on the 2026-10-02 card. `--help`, `cli.md` and the
sharing guide (UX-1291) name the switch.

## Out of Scope

Making anonymised export the default; changing what it covers.

## Acceptance Test

On a fixture snapshot: TTY "y" writes a bundle whose residue scan is
clean and whose `--load` reads; "n" and no-TTY write nothing; a
planted name in a member refuses with exit 2.

## Outcome (round 167, 2026-10-02) — 🟢 Done

**Premise:** held: the engine was done and no command reached it.

### The gap, measured

```text
$ bga bundle --export @last --anonymize      (base f5a8cabd9, macro_micro snapshot)
usage: bga [-h] [--version] COMMAND ...
bga: error: unrecognized arguments: --anonymize
exit=1
$ bga bundle --help
usage: bga bundle --export STAMP [-o FILE] | --load FILE|DIR | --resolve --key-fingerprint FP
```

### After

```text
$ bga bundle --export @last --anonymize -o out.bga-bundle.tar.gz </dev/null
Anonymized bundle …/out.bga-bundle.tar.gz: 4 members
  … (the review, 8 lines)
stdin is not a terminal, so no one can approve the review above.
Error: the owner did not approve the review; nothing was written
exit=2      -> bundles: []; .bga/anon: {'key': '0o600'}
$ (on a pty, answering n)  ... Write this bundle? [y/N] n
exit=2      -> bundles: []; .bga/anon: {'key': '0o600'}
$ (on a pty, answering y)  ... Write this bundle? [y/N] y
Wrote …/out.bga-bundle.tar.gz
  4 members, 43.6K before compression
  read a reply with: bga bundle --resolve --key-fingerprint 4dd12723ed46370a
exit=0      -> bundles: ['out.bga-bundle.tar.gz']; .bga/anon: {'key': '0o600', 'map.json': '0o600'}

$ pytest -v tests/unit/test_bundle_export_has_an_anonymize_switch.py
test_y_on_a_terminal_writes_a_clean_bundle_that_loads PASSED
test_no_approval_writes_nothing[n|eof|no-tty] PASSED ×3
test_a_planted_name_refuses_whatever_the_answer PASSED
test_anonymize_with_another_mode_is_a_usage_error[load|resolve|no-plane2] PASSED ×3
test_the_help_names_the_switch PASSED
9 passed in 1.22s
```

The key and map are `anonymize.load_or_create_key` and
`PseudonymMap.for_project` on `run_store.project_root()`, the pair
`--resolve` reads. The approver is chosen in `cli._review_approver`.

### Mutations verified red and reverted (10)

| # | mutation (`bga/cli.py`) | reddened |
|---|---|---|
| A1 | `_review_approver` always asks, no TTY check | no-tty, 1 failed |
| A2 | any answer approves | n, 1 failed |
| A3 | EOF at the prompt approves | eof, 1 failed |
| A4 | the no-TTY refusal returns true | no-tty, 1 failed |
| A5 | the `--anonymize` branch skipped (plain export) | 5 failed |
| A6 | the usage check dropped | load, resolve, no-plane2: 3 failed |
| A7 | `--no-plane2` allowed with `--anonymize` | no-plane2, 1 failed |
| A8 | map written to `<project>/map.json`, off `.bga/anon/` | y, 1 failed |
| A9 | usage line omits `[--anonymize]` | help, 1 failed |
| A10 | the `--resolve --key-fingerprint` line dropped | y, 1 failed |

Restored: 9 passed. A first residue check in the y test built its
dictionary from every map value and hit `progress`, a word the
engine's own dictionary filters; it now reads the fixture's uids and
stamp, as the engine's scan already gates the export.

### Deviation from the Required Fix

Three. No unattended approval (the owner's decision is open), so no
TTY always refuses. A refused first run still creates `.bga/anon/key`
(0600), since the review needs it; bundle and map are not written. The
sharing guide (UX-1291) does not exist yet, so only `--help` and
`cli.md` name the switch.
