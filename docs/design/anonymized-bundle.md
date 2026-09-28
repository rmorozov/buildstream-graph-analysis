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
"yes" on 2026-09-27, and his design review on #298 the same day revised
sections 3, 6 and 7 (section 8 lists the five findings). No code
changed; section 9 lists the rows filed with it.

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
| B. public vocabulary | binary basenames (`cmake`, `cc1plus`, `ld`), `element_kind`, task names, resource names, schema keys, `bga`'s own sentence templates, toolchain versions | kept only when the **value** is on the path's allowlist (6.11) |
| C. measurements | `cpu_us`, `dur_us`, counts, `max_concurrency`, `peak_memory`, `max_jobs` | kept |
| D. host facts | `run-context.json` `host`; the `host/v2` manifest's `cpu_model`, `cpu_count`, `memory_bytes`, `kernel_release`, `distro_id`, toolchain | hostname pseudonymized; the rest kept |
| E. content hashes | `cache_key`, `manifest_hash`, `run_identity_hash`, source refs | re-keyed by HMAC: equal stays equal, unlinkable to the owner's artifact server |
| F. free text | `plane2.log.gz` `cmd=` lines, `redundant_operations[].example_cmd` and `signature`, `build.log`, `capture-context.txt`, finding prose naming elements | tokenized; raw logs dropped |
| G. secrets | userinfo in remote-cache URLs, tokens in env or `-D` values | dropped, never pseudonymized: a pseudonym would copy the secret into the local map |
| H. time | absolute `ts_us`, wall-clock stamps, the snapshot stamp | shifted to epoch 0, every delta exact |

An allowlist, never a denylist: a denylist fails open on the next field
anyone adds. The class does **not** live in `bga/schemas.py`: that module
pins the top-level keys of the *output* documents and sets
`additionalProperties` true, and it is not the schema of `graph.json`,
`trace.json`, `run-context.json` or any other captured input. A guard over
it could pass beside an unclassified private field.

So the class lives in a **disclosure policy per exported member**,
versioned by that member's contract (`graph/v9`, `trace/v9`,
`run-context/v9`, `plane2/v3`, `sources/v1`, `host-samples/v1`, and the
uncontracted members by name). The policy names every value path,
including map keys that are data (every `per_element` key of
`plane2.json` is class A, whatever its value) and array items. The
export walks each member and **refuses on any path the policy does not
name**, so an unknown field fails the export instead of travelling. A
contract version the policy has no entry for refuses the whole member.

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
Free text is **never scanned and forwarded**: a field of class F is
either rebuilt from a constrained grammar (a command line becomes an
allowlisted `argv[0]` plus flag names, every value slot a pseudonym) or
dropped. A dictionary pass, longest match first, with normalized
variants (case-folded, `-`, `_`, `.` stripped), then covers what the
grammar keeps.

The **residue scan** is a tripwire, not a proof: the export fails if any
dictionary token of four or more characters still appears anywhere in
the decoded archive. It cannot find a codename, address, URL, credential
or short identifier the dictionary never held, so a clean scan is never
described as "no original name or secret"; what closes that gap is the
policy's allowlist and the owner's review (6.8).

**6.3 Short names collide with vocabulary.** `core.bst` must not rewrite
"core activity" or "cores": replace at word boundaries, outside
allowlisted phrases, and count substitutions per class in the manifest.

**6.4 Analysis must commute with anonymization**, up to ties (6.10):
`analyze(anon(capture)) ≈ anon(analyze(capture))`. It breaks wherever
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

**6.8 An explicit owner review before writing.** Substitutions per
class, every string kept verbatim because the allowlist matched, anything
the residue scan found suspicious. Nothing is written until the owner
approves: a dictionary cannot know a codename in a comment.

**6.9 The archive's own metadata.** `bundle.export()` calls
`tarfile.add()` on the source files, so each header carries the file's
mtime, uid, gid, user and group name; `bundle.json` carries the
snapshot's `stamp` and `packed_at`; the default file name is
`<stamp>.bga-bundle.tar.gz`. The anonymized export builds every tar
header explicitly (mtime 0, uid and gid 0, empty user and group names,
normalized mode), writes a transformed manifest (the stamp pseudonymized,
`packed_at` dropped), names the file without the stamp, and runs the
residue scan over the **decoded final archive**, headers and manifest
included, before it is published.

**6.10 Ties have no name-independent order.** Symmetric nodes can tie
with no order that survives renaming, so exact equality in 6.4 is
stronger than the property wanted. The commutation guard compares
invariant measurements exactly and, where a choice is tied, the *set* of
equally valid choices rather than the representative, and treats display
order as out of scope. Findings whose single representative cannot be
preserved are listed by name in the guard.

**6.11 A public path does not make a public value.** Classing a path
B says what the field is for, not that every value in it is public:
`by_binary` or a toolchain string can name a private tool. So each class
B path carries a **value allowlist** and a fallback. A binary basename
not on the list becomes a `b-` pseudonym; a toolchain string must parse
as an allowlisted tool plus a version, else the tool name is
pseudonymized the same way; a class B path with no pseudonym class
refuses the export on an unknown value. The same rule holds for every
other kept string whose contents vary by project.

## 7. Staging

1. The disclosure policy per exported member, exhaustive and versioned.
2. The pseudonym core and the local map.
3. Neutral archive and manifest metadata (6.9).
4. The anonymized export, with the residue scan and the owner review.
   Every `CAPTURE_LAYOUT` row states its treatment, and a row added
   without one refuses the export:

   | Row | Treatment |
   |---|---|
   | `.bga/.gitignore`, `.bga/config`, `.bga/tmp/` | drop |
   | `.bga/runs/<stamp>/` | renamed by a pseudonymized stamp |
   | `run/graph.json`, `run/trace.json`, `run/run-context.json`, `run/sources.json` | transform |
   | `run/chrome_trace.json` | drop (derived) |
   | `plane2.json`, `plane2-resource.json`, `host-samples.jsonl` | transform |
   | `element-slice.json` | transform: its target names are class A |
   | `analyze.json` | drop: its prose is free text, and the far side re-derives it |
   | `plane2.log.gz`, `build.log`, `capture-context.txt` | drop |
   | `.size` | drop (derived) |

5. The commutation guard.
6. Resolve, and the viewer taking a map.
7. Public-junction passthrough.
8. Tokenized raw logs, only when a real diagnosis needs them.

Stages 1, 3 and 5 are **release criteria** for the first anonymized
export, though each is its own task: stage 4 drops `analyze.json` and
the receiving side re-derives it, so until stage 5's equivalence guard
is green a change in diagnosis would travel undetected. Stage 4 may land
first, but its export stays unreleased (no documented or enabled switch)
until then.

## 8. Decisions, 2026-09-27

| Question | Decided |
|---|---|
| Keep names under declared public junctions, intersected with a public checkout's name list | yes |
| Keep CPU model, core count, memory and kernel as they are; coarsening on a switch | yes |
| One key per project, pseudonyms stable across captures | yes |
| Drop raw logs from the first stage | yes |
| Shift timestamps to epoch 0 | yes |
| File the stages as backlog rows | yes |

The owner's design review on #298 (head `2672784c`) added five findings,
all taken: the classification moves from `bga/schemas.py` to a policy per
exported member (blocker); archive and manifest metadata are anonymized
and scanned (blocker, UX-1067); the residue scan is a tripwire and free
text is rebuilt from a grammar or dropped (high); every layout row is
enumerated in stage 4 (medium); commutation compares ties as sets
(medium). The follow-up review at `8c3bead1` added two, both taken:
class B is checked by value, not only by path (6.11), and the
equivalence guard is a release criterion for the first export (stage
list, section 7).

## 9. Rows filed

| Stage | Row |
|---|---|
| 1 | [UX-1060](../backlog/scenarios/UX-1060-every-exported-value-path-declares-what-it-discloses.md) |
| 2 | [UX-1061](../backlog/scenarios/UX-1061-a-pseudonym-is-keyed-stable-and-keeps-the-names-shape.md) |
| 3 | [UX-1067](../backlog/scenarios/UX-1067-the-archive-and-its-manifest-carry-no-original-metadata.md) |
| 4 | [UX-1062](../backlog/scenarios/UX-1062-a-bundle-exports-anonymized-and-refuses-a-leftover-name.md) |
| 5 | [UX-1063](../backlog/scenarios/UX-1063-analysis-commutes-with-anonymization.md) |
| 6 | [UX-1064](../backlog/scenarios/UX-1064-a-pseudonym-in-any-text-resolves-back-to-the-real-name.md) |
| 7 | [UX-1065](../backlog/scenarios/UX-1065-a-declared-public-junction-keeps-its-public-names.md) |
| 8 | [UX-1066](../backlog/scenarios/UX-1066-raw-logs-travel-tokenized.md) |
