# Round 135 — the sysroot was the host's, and nothing said which host

Run on 2026-09-22 from `74fb2712`. One row closed (`UX-914`), one filed
(`UX-925`), and one waiver carried byte-identically from #254 so the
round could commit at all: `main` was red on round 130's dateline with
no branch applied, and the pre-commit hook runs `make test-touching`.
No track ran; the session did the work itself.

```text
closed   UX-914   the examples' sysroot is the host's, so the examples measure the host
filed    UX-925   the toolchain axis is this host's gcc, because gcc is not relocatable
probes   23 over 21 staged names, one per binary, two verdicts
```

## The base was never the question

`UX-914` offered four candidates and asked which to adopt. All four
need a mirror this environment refuses at CONNECT:

```text
deb.debian.org 000  dl-cdn.alpinelinux.org 000  ftp.gnu.org 000
cdn.registry.gitlab-static.net 000  cache.nixos.org 200  channels.nixos.org 200
```

The last two rows dissolve the pick rather than deciding it. `UX-915`
proved a Nix store path fetches and unpacks with no Nix, daemon or
root, so a *component* can be pinned without a base distro and without
touching libc — which is what would have made A3 cost every recorded
figure. The base stays host-staged; a component becomes a pin when its
version is shown to decide a reading. `make` is the first and still
the only one. What makes that a choice rather than a continuation of
the silence is the declaration: `tools/sysroot_manifest.py` names one
row per package — axis, origin, declared version — and probes the
staged copy.

## A package-level probe is a proxy for its own members

The round wrote the proxy twice and the rule (fixing guide §5) caught
it twice.

The first draft asked `env` for all of coreutils and the 4.4 alias for
`make-4.4`. Staging the host's `/usr/bin/make` over the pin then left
the manifest reading `4.4.1` and exiting 0 — the pin had not taken and
the instrument said it had. Per-binary probing reads `4.3, 4.4.1` and
exits 1.

The second draft kept the stager's own `startswith("/")` filter, which
drops `$(gcc -print-prog-name=cc1)` and its two siblings. So `cc1`,
`cc1plus` and `collect2` were staged with **no owner and no probe**
while the guard asserted every staged path had one. `rmorozov` found
that in review on `#257`: a host GCC can resolve a `cc1plus` that
disagrees with the `gcc` beside it. They are owned by *name* — their
staged path carries the host's triple and gcc major — and located by
globbing the staged tree, because re-deriving them from this host's
`gcc -print-prog-name` reads the proxy again one level down.

Probing them turned up two more. `collect2` prints its own version to
stderr and then execs `ld --version` to stdout, so a `(stdout or
stderr)` heuristic reports binutils' `2.42` as gcc's; each helper now
declares its flag *and* its stream. And `cc1`'s line ends in the
triple — `GNU C17 (Ubuntu 13.3.0-...) version 13.3.0
(x86_64-linux-gnu)` — which broke a last-token version rule that had
read the other seven formats correctly.

## The mutation table

Each applied, reddened, reverted, re-run green:

```text
M1  declare gcc 13.2.0                      1 failed (staged), check warns, exit 0
M2  drop /usr/bin/cat from the declaration  2 failed (claim + axis)
M3  coreutils onto the toolchain axis       1 failed (axis)
M4  probe one binary per package            1 failed (probed-rather-than-sibling)
M5  host /usr/bin/make over the pin         1 failed, check exit=1
M6  fuse the axes back into one BINARIES    13 failed (the wrapper guard)
M7  drop cc1plus from the declaration       1 failed (helper-claimed)
M8  a cc1plus reporting 12.3.0 in the tree  1 failed, gcc reads "12.3.0, 13.3.0"
M9  read collect2 off stdout, not stderr    1 failed, collect2 reads 2.42
M10 stage a fourth helper, undeclared       1 failed (helper-claimed)
```

M6 is the one worth keeping: `test_a_wrapper_runs_where_coreutils_do_not`
builds its sandbox `PATH` from the script's array, so a regex left
matching only the composed `BINARIES=(...)` reads zero paths and passes
whatever the wrappers did.

M9 also cost a wrong verdict before it cost a right one: the first run
recorded it as not reddening, because a `sed` inside a nested heredoc
never applied. A mutation's verdict is only worth what the check that
it landed is worth.

## What the round did not do, and why that was invisible

This document is late, and rounds 132, 133 and 134 have none at all.
All three are named by task files on `main` — `UX-891`..`UX-894`,
`UX-913` and `UX-915`/`UX-916` carry them in their Outcomes and
`Found by` lines — and none has a `docs/audits/round-N.md`. The round
register ends at 131, because it derives from documents plus the
ledger's round column and three rounds appear in neither.

`make test` is green through all of it: 9180 passed on `8bdef467` with
four rounds undocumented. Step 5 of the close ritual has a guard that
prices a document's agents, and step 6 has one that reads the history
table against the directory in both directions — but nothing reads
whether the document was written. A ritual `CLAUDE.md` names and no
guard reads is the shape this repository keeps rediscovering, so it is
filed rather than fixed here.

## Agents

There were **no agents launched** in this round. `UX-914`'s shape
derives `judgement` and the session took it in context: the
decomposition was the two axes, and the declaration and its guard are
small enough that briefing a track would have cost more than writing
them, so the ledger has no row to carry.
