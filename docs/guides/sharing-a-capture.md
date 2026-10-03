# Sharing a capture

Five steps, one command each: keep a capture as a bundle, anonymise it
for an outside reader, load a tree of kept bundles, read the tree in
place, and resolve a reply back to real names. Every flag is in
[`cli.md`](cli.md#carrying-a-capture-to-another-machine-ux-520); the
anonymisation design is
[`anonymized-bundle.md`](../design/anonymized-bundle.md).

## 1. Keep it: export a bundle

On the machine that captured, write the snapshot into the tree CI keeps,
one directory per build number:

```bash
mkdir -p ci/101
bga bundle --export @last -o ci/101/run.bga-bundle.tar.gz
```

The bundle holds every member `capture-layout/v1` names for that
snapshot, Plane 2 included; `--no-plane2` leaves it out and says so.
`-o`'s directory must exist.

**A plain bundle is the capture verbatim.** Element names, the host
manifest, and in `plane2.json` every path and command line the sandboxes
ran. On `tests/fixtures/macro_micro` (2026-10-03): four members, and
`plane2.json` carries 18 distinct absolute paths and each repeated
operation's command, such as `cmake -B_builddir -H. -GUnix Makefiles
-DCMAKE_INSTALL_PREFIX:PATH=/usr`. Send it only where the project's
names may go.

## 2. Anonymise it: a bundle for an outside reader

```bash
bga bundle --export @last --anonymize -o share.bga-bundle.tar.gz
```

Every element name, path, URL, ref and the hostname becomes a keyed
pseudonym, equal names staying equal; content hashes are re-keyed,
credentials dropped, and times shifted to epoch 0 with every delta
exact. Durations, counts, the host's shape and public tool names are
kept, so the joins, the critical path and the findings built on them
still compute. The graph's shape alone can
still identify a project.

**The key stays on this machine.** `.bga/anon/key` is created on first
use and `.bga/anon/map.json` records each pseudonym, both mode 0600;
nothing in the bundle reverses them. The command shows a review screen
and asks `[y/N]`: anything but `y` writes nothing, map included. With
no terminal on stdin it prints the review and refuses, exit 2, and a
real name the residue scan finds refuses whatever the answer.

```console
$ bga bundle --export @last --anonymize -o share.bga-bundle.tar.gz
Anonymized bundle share.bga-bundle.tar.gz: 4 members
  members: run/graph.json, run/trace.json, run/run-context.json, plane2.json
  dropped: none
  values rewritten, per class: A 451 · E 15 · F credential 12 · F dropped 34 · F rebuilt 40 · H 13
  kept verbatim (71): --cyan, --help, --progress-dir, …
  residue scan: clean over 47 dictionary tokens; a tripwire, blind to a name it never held
  the graph's shape alone can identify a project (anonymized-bundle.md 6.5)
  key fingerprint dc47a02e937dab7c; the map stays on this machine
Write this bundle? [y/N] y
Wrote share.bga-bundle.tar.gz
  4 members, 43.6K before compression
  read a reply with: bga bundle --resolve --key-fingerprint dc47a02e937dab7c
```

*Kept, not current* — 2026-10-03, `tests/fixtures/macro_micro` as the
newest snapshot of a scratch project, answered `y` on a terminal; the
key is random per project, so the fingerprint is this run's. Cuts: the
`kept verbatim` list after its third entry.

## 3. Load it: a tree of kept bundles into the store

On the machine that reads, with the tree copied beside a `project.conf`:

```bash
bga bundle --load ci
```

Every file under `ci` named `*bga-bundle.tar.gz` is a bundle, at any
depth. All are checked before any is written, so one bad bundle refuses
the whole tree by name. Loading again is a re-send, not a collision.
A bundle loads under its own stamp; an anonymised one under its
pseudonymised stamp.

**`--load` costs disk.** The store it writes is 1.9x-5.6x the tree
(`UX-900`), and it stays. On the two committed fixtures above
(`same_build_twice_cold` and `macro_micro`, 2026-10-03), the tree is
11,031 bytes and the store 59,479, 5.4x.

## 4. Read it in place: no store kept

```bash
bga snapshot --list --bundles ci
```

`--bundles` goes with `--list`, `--aggregate` and `--capacity`, and with
`bga compare --band-from-class` on a review runner
([`pilot.md`](pilot.md)). The tree is read through a temporary store
deleted on exit, so the disk above is held only while the command runs.

## 5. Resolve a reply: back to real names

A reader quotes pseudonyms. On the machine holding the key, with the
fingerprint the export printed in `FINGERPRINT`:

```bash
cat reply.txt | bga bundle --resolve --key-fingerprint "$FINGERPRINT"
```

Each pseudonym in the reply is printed back as its real name, and every
pseudonym-shaped token the map does not hold is listed rather than
dropped. A fingerprint that does not match this project's key refuses,
exit 2, before stdin is read.
