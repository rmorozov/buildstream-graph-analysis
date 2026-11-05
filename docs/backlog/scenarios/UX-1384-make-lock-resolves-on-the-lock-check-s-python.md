# UX-1384: `make lock` resolves on the Python the lock check compiles on

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** `retro-2026-10-26.md` proposal 2; Ruslan filed it on the decision card, 2026-11-05 19:54 UTC | **Serves:** anyone who regenerates `requirements.lock` | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`make lock` runs `uv pip compile` on the host's Python, while
`quality.yml` compiles on `3.12`. A 3.13 resolve drops referencing's
`typing-extensions` edge, so `#332` needed a second commit (`42f5e878`)
and `#334` needed `--python-version 3.12` by hand. Since `UX-1379` the
floor is 3.11, so "the floor" and "the check's Python" are no longer
one number.

## Required Fix

`make lock` passes `--python-version` read from the one place
`quality.yml`'s lock check takes it, so a lock written on any host
equals what the check compiles.

## Out of Scope

Which Python the check itself runs on.

## Acceptance Test

`make lock` on a 3.13 host leaves `requirements.lock` byte-identical to
the check's compile; a guard reddens when the two versions differ.

## Outcome
