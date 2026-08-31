# UX-461: example 09 cannot be built, and nothing ever noticed

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 72, building a capture for every example (`UX-459`) | **Serves:** the reader who follows `examples/README.md` to 09 and cannot get past `bst build` | **Topic:** guards

## Motivation

`examples/09-fine-grained-siblings` does not build, on any machine, and
has not for as long as it has existed:

```console
$ cd examples/09-fine-grained-siblings && bst build all.bst
[00:00:00] FAILURE Resolving elements
bulk.bst [line 9 column 8]: Specified path 'files/bulk' does not exist
```

`bulk.bst` is a `kind: import` over a local source at `files/bulk` — the
8k-file sysroot the project's README describes as the whole point of
the example, since BuildStream stages by hardlink and a small tree
stages in `00:00:00`. That directory is not in the repository and no
script creates it:

```console
$ ls examples/*.sh
examples/stage_cpp_toolchain.sh
examples/stage_project3_remote.sh
examples/stage_runtimes.sh
$ grep -c "09-fine-grained" .github/workflows/ci.yml
0
```

Three staging scripts, none for 09, and `bst-examples` never builds it.
So the project has never run anywhere, and the merge criterion it was
written to exercise — `UX-100`'s *"siblings paying more sandbox toll
than they spend building"* — is still tested only on synthetic
unit-test input, which is exactly the gap the example was created to
close.

`UX-459` committed a capture for every other example. 09 is the one
that could not be captured, and the reason is not the capture.

## Required Fix

- **A staging script** beside the other three, generating `files/bulk`
  at whatever size makes the toll measurable, with the size chosen from
  a measurement rather than a guess.
- **`bst-examples` builds 09**, so the project cannot silently stop
  building again.
- **Then a capture**, joining the seven `UX-459` landed, and the
  `sandbox-toll` family checked against real data for the first time.

## Out of Scope

- **Changing `UX-100`'s merge criterion**: it may well be right; it has
  simply never met a real build. Deciding that is what this item
  unblocks, not what it does.
- **The other examples' staging**: 01-07 build here today, six of them
  with a committed capture (`UX-459`).

## Acceptance Test

```bash
examples/stage_09_bulk.sh   # or whatever it is called
cd examples/09-fine-grained-siblings && bst build all.bst
```

succeeds, and `tools/dev_finding_coverage.py` lists
`09-fine-grained-siblings` among the captures.

## Outcome

_Not started._
