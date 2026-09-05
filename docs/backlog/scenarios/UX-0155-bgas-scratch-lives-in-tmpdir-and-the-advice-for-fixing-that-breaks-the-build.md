# UX-155: bga's scratch lives in TMPDIR, and the advice for fixing that breaks the build

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-147 (`probe_bwrap_shim`, which produces the advice), UX-11 (the shim, which is what needs somewhere executable to live) | **Topic:** capture | **Area:** tools

Filed from a real user report on Ubuntu 24.04, and this one is a
two-step failure where **bga supplied the second step**:

1. `bga snapshot` failed on temp-directory permissions. The shim, the
   compiled hook and the spine are written with
   `tempfile.TemporaryDirectory()`, so they land wherever `TMPDIR`
   points, and the shim has to be *executed* from there.
2. `probe_bwrap_shim`'s error says **"Set TMPDIR to a directory you can
   execute from and re-run."** The user did exactly that —
   `TMPDIR=.bga_tmp bga snapshot -- bst build my_cmake_element.bst` —
   and the build died deeper down with
   `buildboxcasd.m.cpp std::system_error ... error in mkdtemp, errno: no such file or directory`.

## Motivation

Step 2 is the interesting half, because the remedy came from us.

`TMPDIR=.bga_tmp` is *relative*, and the two languages in this stack
disagree about what that means:

- **Python's `tempfile`** treats `TMPDIR` as a candidate and silently
  **falls back** when it is unusable from the current directory. bga
  therefore accepted the setting and appeared to work.
- **`buildbox-casd`'s C++ `mkdtemp`** takes it literally, after the
  daemon has already `chdir`'d away from the project. Measured:

  ```text
  mkdtemp FAILED on ".bga_tmp/casd-763kd3": errno 2 (No such file or directory)
  ```

  which is the user's error, verbatim.

So `TMPDIR` is the wrong knob for bga to reach for at all. It is a
process-wide setting inherited by every service `bst` starts —
`buildbox-casd`, `buildbox-run`, the sandbox — and bga changing it, or
telling a user to change it, reconfigures all of them to fix a problem
that belongs to one directory bga owns.

bga already has a project-local place for its own state: `.bga/`. The
run store lives there. Scratch should too.

## Required Fix

1. **bga's scratch is `.bga/tmp/`**, not `TMPDIR`: the shim directory,
   the bind directory holding `hook.so` and the spine, and the
   unnamed intermediate logs. Removed on the way out, as now.
2. **`probe_bwrap_shim` stops advising `TMPDIR`.** It names the
   directory that actually failed and the remedies that do not
   reconfigure the rest of the build.
3. **A relative `TMPDIR` in the inherited environment is made absolute**
   for the child build, because BuildStream's C++ layers hard-fail
   where Python quietly recovers. Silently passing it through is how
   this report happened.
4. **`bga doctor` checks it**, so the answer arrives before the build
   rather than thirty minutes into it.

## Out of Scope

- The path *inside* the sandbox (`/tmp/.bst-native-trace`). Different
  namespace, unaffected by any of this.
- Making `.bga/tmp` survive a run for post-mortems. `UX-148` is where
  keeping a failed sandbox's evidence belongs.

## Acceptance Test

A capture on a project whose `TMPDIR` points at a `noexec` mount
completes, because nothing bga executes lives there any more. A capture
with `TMPDIR` set to a relative path completes, and `buildbox-casd` does
not see the relative value. `bga doctor` names both conditions.


---

## What was built

`.bga/tmp/` is where bga's scratch goes: the shim directory that lands
on `$PATH`, the bind directory holding `hook.so` and the spine, and
`run`'s unnamed intermediates. `capture_scratch` for the ones scoped to
a build, `scratch_mkdtemp` for the ones that have to outlive it — those
had been going to `tempfile.mkdtemp()` and were never removed at all,
so they sat in `TMPDIR` indefinitely. A project bga cannot write to
falls back to `TMPDIR` and says so; a `.bga/` created only for scratch
still gets the store's `.gitignore`.

`probe_bwrap_shim` no longer says "Set TMPDIR". It names `.bga/tmp` and
says outright that `TMPDIR` is not the knob, because that sentence is
what produced step 2 of the report.

### The half that moving files could not fix

`TMPDIR` still had to be normalized, and the first attempt at that was
wrong in an instructive way. Rewriting only the child `env` dict passed
to the traced `bst` left the capture still failing. A wrapper on
`buildbox-casd` recording its own environment showed why — **two** casd
starts per capture:

```text
casd TMPDIR=/tmp/ux155/p6/.bga_tmp cwd=/tmp/ux155/p6
casd TMPDIR=/tmp/ux155/p6/.bga_tmp cwd=/root/.cache/buildstream
casd TMPDIR=.bga_tmp               cwd=/tmp/ux155/p6
casd TMPDIR=.bga_tmp               cwd=/root/.cache/buildstream
```

The traced build got the corrected value; a second `bst` did not,
because it spawns from `os.environ`. Measured, that one is `bst show`,
run by `extract_run` after the build — the capture traced all nine
sandboxes and *then* died at extraction, which is exactly why fixing
only the build's environment looked like it had worked. The census and
the `--diagnose` fingerprint probe shell out the same way.

So `normalize_tmpdir()` fixes `os.environ` itself. Assigning through
`os.environ` calls `putenv`, so every child inherits it however it is
spawned. The `cwd` column above is the mechanism the whole item turns
on: casd really does run from the cache directory, so a relative path
that was only ever meaningful in the project directory is gone by the
time it resolves.

`bga doctor` gained `tmpdir-absolute` and `scratch-executable`.

### Measured

| condition | before | after |
| --- | --- | --- |
| `TMPDIR` on a real `noexec` bind mount | rc=1, shim probe refuses | **rc=0**, 9 shim invocations |
| `TMPDIR=.bga_tmp` (relative), cold build | rc=1, casd `mkdtemp` ENOENT | **rc=0**, 9 rewritten |

Both on `examples/06-macro-micro-optimization`. The `noexec` mount was
a real `mount -o remount,bind,noexec`, verified to refuse `./p.sh`
before it was used, not a `chmod`.

The relative-`TMPDIR` failure was reproduced from first principles
before anything was changed — a C `mkdtemp` after `chdir("/")`:

```text
mkdtemp FAILED on ".bga_tmp/casd-763kd3": errno 2 (No such file or directory)
```

which is the user's error verbatim, while the same thing in Python
succeeds by silently falling back to `/tmp`. That asymmetry is the
whole reason bga appeared to accept a setting that killed the build.

### Falsified

Five mutations, each red on its own test and nothing else: scratch back
to `TMPDIR`; `absolute_tmpdir_env` not resolving; the probe advising
`TMPDIR` again; doctor losing the relative-`TMPDIR` check; doctor
probing a path that is not a directory. Plus the end-to-end one —
removing the `normalize_tmpdir()` call and re-running the cold capture
with a relative `TMPDIR`: rc=0 → **rc=1**.

One test initially passed for the wrong reason: `chmod 0o500` on the
project directory does not stop root, and this suite runs as root here
and in CI. The unwritable-project case is now obstructed with a regular
file where `.bga` should be, which no uid can write through.
