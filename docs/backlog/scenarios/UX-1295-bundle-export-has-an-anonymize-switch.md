# UX-1295: `bga bundle --export` has an `--anonymize` switch, so a pilot can share a capture without a Python call

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1062, UX-1063 | **Found by:** the owner, 2026-10-02: "have we introduced bundle anonymize switch? without it pilot maybe is not as smooth" | **Serves:** R4, R5 | **Topic:** cli | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome
