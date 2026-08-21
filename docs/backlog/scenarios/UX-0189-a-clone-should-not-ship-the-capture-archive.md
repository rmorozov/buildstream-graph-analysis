# UX-189: a clone should not ship the capture archive

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-77 (the capture-branch convention this documents around)

## Motivation

Field feedback: *"it's not very comfortable to clone our repo and get
binary data from captures — maybe we need to fix doc to clone only
main branch."* Measured, round 20: eight `captures/*` branches on the
remote, the `fdsdk-latest` pointer alone carrying ~7.8 MiB of objects
— a default `git clone` fetches all of them, so the first-contact
experience pays for an archive it did not ask for.

The branches are load-bearing (the band's baseline sets resolve
against them; the round-18 review re-ran the −25% verdict from those
refs) — the fix is at the clone, not the archive.

## Required Fix

1. README's install section clones shallow-and-single:
   `git clone --single-branch https://…` (the branch default is the
   remote HEAD, so no `--branch` needed), with one sentence saying
   why — the `captures/*` branches hold published capture data that
   analysis can fetch on demand.
2. `real-project.md`'s prerequisites say the same where they name the
   checkout.
3. One line in the capture workflow's docs on fetching a specific
   ref when needed:
   `git fetch origin captures/fdsdk-latest:captures/fdsdk-latest`.

## Out of Scope

- Moving captures to a separate repository or LFS (a maintainer
  decision with CI implications; the docs fix removes the pain
  today).
- Shrinking the existing branches (history rewrite, same reason).

## Acceptance Test

The documented clone command, run against the real remote in the
packaging job (or a local mirror in tests), fetches no `captures/*`
refs (`git branch -r` asserted); the docs-commands test covers the
new lines; the fetch-on-demand line works against the mirror.
