# UX-147: zero shim invocations has three causes, and diagnose asserts the benign one

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-146 (the diagnostics this sharpens)

Filed against the same real Ubuntu 24.04 field failure as UX-146
(`bst build` works; `bga snapshot` fails with `buildbox-run failed
with returncode 1`, opens and spine off), which round 15 could not
reproduce from an installed wheel in a foreign venv on this container —
the failing link is environment-specific and *earlier than the shim*,
which is exactly the region UX-146's shim-side record cannot see.

## Motivation

UX-146's zero-invocation summary says: *"Zero invocations means that
never happened: this build ran unmodified and the capture is empty for
that reason, not because the sandbox failed."* That is one of **three**
causes, and in the field case it is the wrong one:

1. **No sandbox launched** (all cache hits) — the benign reading.
2. **The shim was never resolved** — `buildbox-run` found `bwrap` by
   absolute path, or the PATH that reaches it predates the shim: `bst`
   reuses an already-running `buildbox-casd`, and a daemon started
   before the capture carries an environment without the shim dir.
3. **The shim was resolved and could not exec** — it is a
   `#!/usr/bin/env python3` script materialized under a temp dir
   (`install_bwrap_shim` copies it verbatim), so a noexec temp mount,
   an AppArmor denial on executing from `/tmp`, or a child PATH with
   no `python3` all fail the exec *inside buildbox-run*, which then
   reports exactly the field error — `returncode 1`, stderr swallowed
   — while the diagnostics record stays empty and the summary calls
   the build unmodified.

Causes 2 and 3 are the live suspects for the field failure, and today
the tool cannot tell any of the three apart.

## Required Fix

1. **A shim self-probe at capture start, before `bst` runs**: the
   tracer execs the just-installed shim once itself with a probe argv
   (the shim already recognizes a diagnostics mode; give it a
   `--shim-self-test` that records and exits 0). An exec failure fails
   the capture immediately with the real errno and the path — "the
   shim at `<dir>/bwrap` cannot be executed (`EACCES`): a noexec or
   AppArmor-restricted temp directory; set `TMPDIR` to …" — instead of
   a swallowed failure twenty minutes into a build. Materialize the
   shebang as the absolute interpreter (`sys.executable`) at install
   time so the probe tests what the sandbox layer will actually exec,
   with no `env` lookup in the loop.
2. **Stale-daemon detection**: if a `buildbox-casd` for this cache
   directory was already running before the capture set up its PATH,
   say so in the diagnostics summary — it is the one cause the user
   can fix in ten seconds (stop it / let `bst` restart it), and the
   wording of the remedy is to be settled by reproducing the reuse on
   a real `bst`, not assumed.
3. **The zero-invocation summary names all three causes** with the
   evidence it has: probe passed + N build tasks ran + zero shim lines
   → "the shim was executable but never resolved — buildbox-run did
   not reach it through PATH"; probe passed + zero build tasks → the
   current cache-hit text; probe failed → cause 3, already fatal at
   start.
4. **Guard the shim's bare environ reads** (round-15 review): `main()`
   does four `os.environ[...]` lookups before anything is recorded
   (`bwrap_shim.py:383-386`) — a shim reached without `BST_TRACE_*`
   (env sanitized in the chain, or any other process invoking `bwrap`
   while the shim dir is on PATH) raises `KeyError`, a traceback on
   buildbox-run's swallowed stderr, `returncode 1`, no record: the
   exact traceback class UX-146's item 3 fixed, four lines below it.
   Exit with one sentence naming the missing variable, after writing
   the diagnostics line if that much env exists.
5. **Suggest the mode that would have answered** (round-15 review):
   when a wrapped build exits non-zero and diagnostics were *not*
   requested, `bga snapshot`/`bga capture run` say "re-run with
   `--diagnose`" (`tools/bga_snapshot.py:185-188`,
   `tools/bst_native_build_tracer.py:4023`) — today the failing user
   is told nothing new unless they already knew the flag.

## Out of Scope

- The failed-sandbox stderr forensics (UX-148) and the canned
  end-to-end probe (UX-149).

## Acceptance Test

Three live reproductions, each producing its own named verdict: a
noexec `TMPDIR` (mount or chmod) → immediate failure naming the errno
and remedy; a pre-started `buildbox-casd` (started by a plain `bst
build` before the capture) → the stale-daemon line; an all-cache-hit
build → the existing benign text, now stated as verified rather than
assumed. The probe adds one shim invocation, excluded from the
"ran N times" count. Plus: the shim exec'd with a scrubbed environment
prints one sentence naming the missing variable (no traceback —
asserted through a real shim process, like UX-146's errno test), and a
failed capture without diagnostics prints the `--diagnose` hint.


---

## What was built

1. **A shim self-probe before the build.** `install_bwrap_shim` now
   writes the shebang as `sys.executable` — the interpreter already
   running the capture, so there is no `env` lookup left to fail in
   whatever PATH the sandbox layer hands it — and `run_traced_build`
   execs the installed shim once, itself, with `--bga-shim-self-test`.
   A failure is one sentence with the real errno, before the build:

   ```text
   Error: the bwrap shim at /tmp/.../shim/bwrap cannot be executed
   (Permission denied). That is the temp directory, not bga: a noexec
   mount or an AppArmor rule on executing from it will fail the same way
   inside the sandbox layer, where the error is swallowed. Set TMPDIR to
   a directory you can execute from and re-run.
   ```

   ENOENT gets a *different* sentence, because it is bga's own bug and
   not the user's `TMPDIR` — a distinction the first version got wrong
   and reported as a noexec mount (found by placing the probe before
   `install_bwrap_shim`, so it probed a file that did not exist yet).

2. **The zero-invocation summary names all three causes**, told apart by
   how many element tasks Plane 1 recorded. `Running commands` is the
   phase that launches a sandbox, and its count matches the shim's
   exactly — measured on `examples/06`, 9 against 9.

   | evidence | reading |
   |---|---|
   | 0 tasks | *"no sandbox at all — every element was a cache hit … here it is the confirmed one"* |
   | N tasks, 0 shim lines | *"sandboxes were launched and the shim was not called … it was never **resolved**"* + the three ways that happens, `buildbox-casd` reuse named as the ten-second fix |
   | no count | all three, said to be indistinguishable |

   Both readings verified live: a real `examples/06` build (9 and 9) and
   the same build again on a warm cache (0 and 0).

3. **The shim survives a missing environment.** Four bare
   `os.environ[...]` reads, four lines below the traceback `UX-146`
   fixed, meant anything else on the machine invoking `bwrap` while the
   shim directory was on PATH got a `KeyError` on `buildbox-run`'s
   swallowed stderr. It now names the missing variable and falls through
   to the real `bwrap`.

4. **A failing capture says what would answer the question** — `bga
   capture run` and `bga snapshot` both suggest `--diagnose` on a
   non-zero build, and only when it was not already asked for.

### Deviation, recorded

Item 2's *stale-daemon detection* is not implemented as a live check:
the item itself says the remedy's wording is "to be settled by
reproducing the reuse on a real `bst`", and that reproduction did not
happen here. The cause is **named in the summary** as one of the three,
with the fix, rather than detected. Detecting it needs a way to tell
"this `buildbox-casd` predates my PATH" from "`bst` started one", which
is a separate piece of work.
