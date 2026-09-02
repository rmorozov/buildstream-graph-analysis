# UX-162: small debts of the diagnosability round

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-151, UX-152, UX-153, UX-149, UX-155 (the fixes these debts trail) | **Topic:** capture

## Motivation

The round-16 review verified UX-147..155 as landed and collected the
follow-through each one still owes. None reopens its parent; together
they are one sitting of work:

1. **The fingerprint's `buildbox_run_path` is null on every standard
   install**: `shutil.which("buildbox-run")`
   (`tools/bst_native_build_tracer.py:4136`) — but bst 2.x vendors it
   at `site-packages/buildstream/subprojects/buildbox/buildbox-run`,
   never on PATH. Verified null live while the binary existed. Resolve
   the vendored location (via bst's own module path, or the running
   casd's `--buildbox-run=` argv), keep `which` as fallback — UX-151's
   motivation named this exact field.
2. **`Record: <path> (empty)`** (`:4177, :4200`) prints when the file
   holds the UX-151 fingerprint line — "empty" should mean the file,
   not the invocation count.
3. **`doctor_exit` is dead data**: `real-project-capture.yml` captures
   doctor's exit into `$GITHUB_ENV` and nothing reads it. Surface it
   in the workflow's summary step (or stop recording it).
4. **`element_path()` is a naive line parse**: requires column-0
   `element-path:` and returns YAML quotes verbatim
   (`element-path: "files"` → `"files"` with quotes). Tolerate quoting
   and leading whitespace; and `:4407` still prints "no elements/
   directory" when the declared path is something else — name the path
   it actually looked for.
5. **Four claims with no test**, each named by its round's acceptance:
   the `--diagnose` hint on a failed capture; `doctor --capture`'s
   FAIL branches (the three live failure reproductions UX-149's
   acceptance lists — fake bwrap, non-executable shim dir, PATH
   bypass); the selftest seam absent from the shim's injected env
   (claimed in UX-152's log, pinned nowhere); the census on an
   `element-path:` project (UX-153's acceptance, tracer side).
6. **UX-152's impossibility claim over-reaches**: the orphaned-group
   `SIGHUP+SIGCONT` reasoning is right for the shape tried, but a
   discriminating probe is constructible — fork the survivor into its
   own process group while a live same-session process in another
   group keeps the group non-orphaned; state `T` then survives on the
   fixed binary. Either write that probe or annotate the log from
   "cannot be written as specified" to "not writable in the shape
   tried" (the UX-132/144 convention, applied to a mechanism claim).
7. **One sentence in `real-project.md`**: a `local` source (or open
   workspace) spanning the project root stages `.bga` — live scratch
   included — into cache keys and sandboxes; bst has no ignore
   mechanism, so scope sources below the root or expect key churn
   every capture. Cheap doctor warning when a root-spanning local
   source is declared, if the census's source walk already knows.

## Out of Scope

- The census recursion (UX-160), stale-casd detection (UX-161), and
  everything UX-156..159 carry.

## Acceptance Test

The fingerprint from a live capture on this container shows a real
`buildbox_run_path`; the zero-invocation summary no longer says
"(empty)" beside a fingerprint-bearing record; each of item 5's four
claims has a red-on-mutation test; UX-152's log carries either the
probe or the annotation; the docs-commands test covers the
`real-project.md` sentence; `real-project-capture.yml`'s summary
prints the doctor exit it records.

---

## What was built

1. `buildbox_run_path` resolves BuildStream's vendored binary and falls
   back to `PATH`. Live, it was `null`; it is now
   `/usr/local/lib/python3.11/dist-packages/buildstream/subprojects/buildbox/buildbox-run`.
2. `Record: <path>` says `(empty)` only when the file is - verified on a
   zero-invocation capture whose record holds 361 bytes of fingerprint.
3. `real-project-capture.yml` prints the `doctor_exit` it records, into
   the run summary. It was written to `$GITHUB_ENV` and read by nothing.
4. `element_path()` tolerates indentation, quoting and trailing comments
   (`element-path: "files"` used to resolve to a directory literally
   named `"files"`), and the "no elements/ directory" error names the
   declared path.
5. Four claims gained tests: the `--diagnose` hint on a failed capture,
   the selftest seam's absence from the shim's injected environment,
   the census on an `element-path:` project, and doctor's chain FAIL
   branches.
6. `UX-152`'s impossibility claim is annotated rather than rewritten.
7. `bga doctor` warns when an element's `local` source spans the project
   root, and `real-project.md` gains the sentence.

### Deviation, recorded

Item 6 offered "write the probe or annotate". The annotation was taken:
the log now says the *orphaned-group* shape cannot discriminate, which is
what was measured, rather than "cannot be written as specified", which
generalised from one shape to all. The constructible probe the review
describes is named in the annotation and has not been written.

### Falsified

Four mutations - `which`-only resolution, unconditional `(empty)`,
quote-stripping removed, and the root-spanning check disabled - each red.
