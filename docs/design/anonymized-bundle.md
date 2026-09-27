# A reversible anonymized bundle: sharing a private capture

Written 2026-09-27, from the owner's brainstorm thread, read against
`main` at `814a2db8`. The owner runs `bga` on an internal project whose
element names, paths, logs and host details cannot leave the company,
and still wants an outside reader (a colleague, an external LLM) to
diagnose the capture, and to map what that reader says back to the
real elements without doing it by hand.

**Serves:** anyone sharing a capture of a private project with a
reader outside it; R1-R8 reach that reader only through this.

**Status:** decided. The owner answered the six questions in section 8
"yes" on 2026-09-27. No code changed; section 9 lists the rows filed
with it.

## 1. The seam already exists

`bga bundle --export` (`bga/bundle.py`, `UX-520`) packs a capture as a
member list **derived from** `run_store.CAPTURE_LAYOUT`, 13 rows under
one snapshot. An anonymized bundle is the same derivation with one more
column per row: keep, transform, or drop. A row added to the layout with
no such column refuses the anonymized export: fail closed, the way the
plain bundle says a member added to the contract "is bundled by existing".

## 2. Why it stays useful

`bga` reasons on **structure and numbers** and uses names **only for
equality**: the element uid is the join key between Plane 1 and
Plane 2, and the loader checks that `graph.json` and `trace.json` agree
on `run_identity_hash`. A pseudonym that preserves equality keeps every
join, the critical path, capacity, cache and redundancy findings.

| A question about the private project | Survives? | Why |
|---|---|---|
| Critical path, serialization, ready-queue starvation | yes | topology and durations |
| Idle cores, memory peak, jobserver width | yes | numbers and host shape |
| Redundant configure, declared-vs-used dependencies | yes | counts; binaries are public names |
| Cache misses, blast radius, rebuild sets | yes | hashes re-keyed, equality kept |
| `bga` misparsing the project | partly | only when the bug lives in shape, not content (6.1) |
| What an element is for | with hints | kinds survive; meaning needs section 5 |

Analogy: witness protection. Each element gets a cover name, always the
same one, and the only register linking cover names to real names stays
in a locked drawer on the owner's machine.

## 3. Classification, by what a value is

A per-file classification misses names embedded inside strings, so the
unit is the **value class**:

| Class | Where it lives in a capture | Treatment |
|---|---|---|
| A. project identifiers | element uids (`graph.json`, every `per_element` key of `plane2.json`, `trace.json` `task_key`), junction and project names, `sources.json` `identity` and `declared`, opened-file paths, URLs, refs | pseudonym: keyed, structure-preserving |
| B. public vocabulary | binary basenames (`cmake`, `cc1plus`, `ld`), `element_kind`, task names, resource names, schema keys, `bga`'s own sentence templates, toolchain versions | kept, from an **allowlist** |
| C. measurements | `cpu_us`, `dur_us`, counts, `max_concurrency`, `peak_memory`, `max_jobs` | kept |
| D. host facts | `run-context.json` `host`; the `host/v2` manifest's `cpu_model`, `cpu_count`, `memory_bytes`, `kernel_release`, `distro_id`, toolchain | hostname pseudonymized; the rest kept |
| E. content hashes | `cache_key`, `manifest_hash`, `run_identity_hash`, source refs | re-keyed by HMAC: equal stays equal, unlinkable to the owner's artifact server |
| F. free text | `plane2.log.gz` `cmd=` lines, `redundant_operations[].example_cmd` and `signature`, `build.log`, `capture-context.txt`, finding prose naming elements | tokenized; raw logs dropped |
| G. secrets | userinfo in remote-cache URLs, tokens in env or `-D` values | dropped, never pseudonymized: a pseudonym would copy the secret into the local map |
| H. time | absolute `ts_us`, wall-clock stamps, the snapshot stamp | shifted to epoch 0, every delta exact |

An allowlist, never a denylist: a denylist fails open on the next field
anyone adds. The class lives **in the schema**, a `disclosure` word on
each leaf of `bga/schemas.py` (the word `sensitivity` is already an
`analyze` section), and a guard reds when a leaf has none.

## 4. Reversibility

**Mechanism.** `pseudonym = prefix + base32(HMAC-SHA256(key, class ‖ value))[:k]`,
with `k` grown on collision so the map stays injective. The map,
`pseudonym → original`, lives under `.bga/anon/` at mode 0600, inside
the store's existing `.gitignore`; the bundle manifest carries only the
key's fingerprint. HMAC plus a map was chosen over format-preserving
encryption: FF3-1 on arbitrary strings is fiddly, and free-text
resolution needs a table anyway.

**One key per project**, reused across captures, so a pseudonym names
the same element in the nightly and the review build and comparison
classes keep working on shared bundles. A fresh key per share is a
switch.

**Shape.** `base.bst:components/gtk/gtk3.bst` becomes
`j-4fne.bst:d-2k7a/d-x9p3/e-q7rk.bst`: `.bst`, junction separators,
directory depth and file extensions kept; a class prefix (`e-` element,
`j-` junction, `d-` directory, `f-` file stem, `s-` source, `h-` host,
`m-` macro, `b-` private binary) so the reader knows what a token is and
a resolver can find it. The result is a valid element name, so the
analyzer and the viewer run on the anonymized bundle unchanged.

**Resolving what the reader says.** A resolve subcommand rewrites every
pseudonym in any text (a reply, a proposed `.bst` patch) back to the
real name, and lists pseudonym-shaped tokens it cannot map rather than
leaving them. The viewer takes the map to show the anonymized page with
real names, locally. A map whose fingerprint differs from the bundle's
is refused.

## 5. Keeping meaning

1. **Public-junction passthrough.** Names under a public junction keep
   their real names. `bga` cannot know offline that a junction is
   public, and must not guess from its source URL: an internal mirror
   hides the origin, and a public origin does not make a fork's contents
   public. So the owner **declares** the junction in the store's config,
   and a name passes only if it is under a declared junction **and** in
   a name list built from a public checkout on the owner's disk at a
   named tag. An element added inside a fork still gets a pseudonym.
   Declaring nothing passes nothing. What remains visible: that the
   project builds on that junction, and roughly at which version.
2. **Kinds and binaries** already survive (`element_kind`, `by_binary`).
3. **Role tags** the owner adds by hand, for one element whose purpose
   the reader needs.

## 6. Corner cases

**6.1 The anonymizer must not hide the bug it exports.** It is a proxy
for the owner's data (fixing guide section 5). A bug triggered by a
name's content vanishes under a plain ASCII pseudonym, so pseudonyms
keep the original's character class and length band, and `bga`'s errors
cite position (file, line, field), not content.

**6.2 Names inside other strings.** Paths, `-D` values, CMake target
names (`LIBFOO`), log lines and finding prose carry element names.
A dictionary pass, longest match first, over every string, with
normalized variants (case-folded, `-`, `_`, `.` stripped). Then a
**residue scan**: the export fails if any original token of four or more
characters still appears anywhere in the bundle.

**6.3 Short names collide with vocabulary.** `core.bst` must not rewrite
"core activity" or "cores": replace at word boundaries, outside
allowlisted phrases, and count substitutions per class in the manifest.

**6.4 Analysis must commute with anonymization.**
`analyze(anon(capture)) == anon(analyze(capture))`. It breaks wherever
an output is sorted or tie-broken by name. Stable cross-run pseudonyms
want HMAC order; order-preserving pseudonyms want per-run ranks, which
break when an element is added. Resolution: keep HMAC and remove
name-dependent tie-breaks from the analysis.

**6.5 The graph is a fingerprint.** Element count, kind mix and graph
shape can identify a project with every name replaced. The export says
so; the only cure removes the structure the reader needs.

**6.6 Command lines.** Keep an allowlisted `argv[0]` basename, flag
names (`-O2`, `-flto`, `-j`) and public macro names (`CMAKE_*`);
pseudonymize path and identifier values, private macro names and values,
and private tool names (`b-`).

**6.7 The map is the secret.** Mode 0600, never bundled, never listed by
the store's listing.

**6.8 A one-screen review before writing.** Substitutions per class,
free-text tokens kept because the allowlist matched, anything the
residue scan found suspicious. The owner approves, then the archive is
written: a dictionary cannot know a codename in a comment.

## 7. Staging

1. The `disclosure` class on every schema leaf.
2. The pseudonym core and the local map.
3. The anonymized export over the structured members (`graph.json`,
   `trace.json`, `run-context.json`, `sources.json`, `plane2.json`,
   `analyze.json`, `host-samples.jsonl`), with the residue scan and the
   review screen; `plane2.log.gz`, `build.log` and `capture-context.txt`
   dropped.
4. The commutation guard.
5. Resolve, and the viewer taking a map.
6. Public-junction passthrough.
7. Tokenized raw logs, only when a real diagnosis needs them.

## 8. Decisions, 2026-09-27

| Question | Decided |
|---|---|
| Keep names under declared public junctions, intersected with a public checkout's name list | yes |
| Keep CPU model, core count, memory and kernel as they are; coarsening on a switch | yes |
| One key per project, pseudonyms stable across captures | yes |
| Drop raw logs from the first stage | yes |
| Shift timestamps to epoch 0 | yes |
| File the stages as backlog rows | yes |

## 9. Rows filed

| Stage | Row |
|---|---|
| 1 | [UX-1060](../backlog/scenarios/UX-1060-every-schema-leaf-declares-what-it-discloses.md) |
| 2 | [UX-1061](../backlog/scenarios/UX-1061-a-pseudonym-is-keyed-stable-and-keeps-the-names-shape.md) |
| 3 | [UX-1062](../backlog/scenarios/UX-1062-a-bundle-exports-anonymized-and-refuses-a-leftover-name.md) |
| 4 | [UX-1063](../backlog/scenarios/UX-1063-analysis-commutes-with-anonymization.md) |
| 5 | [UX-1064](../backlog/scenarios/UX-1064-a-pseudonym-in-any-text-resolves-back-to-the-real-name.md) |
| 6 | [UX-1065](../backlog/scenarios/UX-1065-a-declared-public-junction-keeps-its-public-names.md) |
| 7 | [UX-1066](../backlog/scenarios/UX-1066-raw-logs-travel-tokenized.md) |
