# UX-189: a clone should not ship the capture archive

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-77 (the capture-branch convention this documents around) | **Topic:** docs

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

---

## What was built

**The numbers first, measured against the real remote rather than
estimated.** Eight `captures/*` refs, confirmed by `git ls-remote`, and
the two clones side by side:

```text
git clone <url>                    .git = 50M    15 remote refs, 8 captures/*
git clone --single-branch <url>    .git = 5.3M    2 remote refs, 0 captures/*
```

A 9.4x difference on first contact, for an archive nothing in the
getting-started path reads. Fetching one capture back costs 8 MiB
(`fdsdk-latest`: 7 files, 8.0 MiB of blobs), paid only by whoever wants
it.

**The clone is documented in both front doors** - README's install
section and `real-project.md`'s Step 0 - each with the sentence saying
what is being skipped and that `bga baseline` fetches on demand.
Neither had a `git clone` line at all before this; both said
`pip install /path/to/bga-checkout`, which quietly left the clone to
the reader.

**The safety check that mattered: is the archive still reachable?**
`bga baseline` discovers with `git ls-remote` and reads through
`FETCH_HEAD`, neither of which depends on the clone's refspec. Run for
real from a `--single-branch` clone against the live remote, it fetched
both captures of the named shape and then refused on a *content*
ground (`NOT COMPARABLE: trace_spine differs across the set`) - the
answer clone shape has nothing to do with.

**A defect this item would have shipped without item 3.** In a
`--single-branch` clone `refs/remotes/origin/captures/*` is never
created, so `capture-workflow.md`'s own line

```text
git show origin/captures/fdsdk-latest:capture.tar.gz > capture.tar.gz
```

fails with `fatal: invalid object name` (exit 128, reproduced).
Documenting the narrow clone without fixing that would have broken the
workflow the narrow clone points people at. Both reads now go through
`FETCH_HEAD`, the `src:dst` refspec is documented for when the ref
should stay, and a guard forbids `git show|checkout|archive
origin/captures/...` in any code fence outside the backlog and audit
directories (which quote the defect deliberately).

Tests: 10 new (`tests/unit/test_a_clone_without_the_archive.py`),
against a local bare repository shaped like the remote - two
`captures/*` branches carrying incompressible payload - so they assert
git's behaviour with no network. The clone flags are **read out of the
docs** rather than hardcoded, so the guard cannot pass against a
command the docs no longer contain. Seven mutations, each red,
including the discriminating one: swapping `--single-branch` for
`--filter=blob:none`, which looks like the same optimization and still
fetches all eight refs.

**Two false greens found by falsifying, both in the fixture:**

1. The payload was an arithmetic sequence, which zlib flattened to
   nothing - the size guard was asserting 35 KiB against 35 KiB.
   Seeded `random.Random(index).randbytes()` instead.
2. Worse: `git clone` of a path on the same filesystem **hardlinks the
   whole object store** and ignores `--single-branch` for the purpose
   of what lands on disk, so both clones measured 828919 B against
   829110 B. `--no-local` forces the negotiation a user actually gets
   over http.

**Deviation from the Required Fix:** the acceptance test runs against a
local mirror rather than the real remote in the packaging job. A
network fetch of the live repository would make a CI job fail on
someone else's push, and the local mirror asserts the same property of
git. The real-remote measurements above were taken by hand and are
recorded here rather than re-run per commit.

