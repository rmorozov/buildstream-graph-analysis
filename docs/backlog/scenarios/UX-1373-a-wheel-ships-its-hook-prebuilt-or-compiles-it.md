# UX-1373: a wheel ships its hook prebuilt, or compiles it at capture, by choice

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan, 2026-11-02: "two types of bga wheels - one with pre compiled hook and one that builds hook on machine"; `UX-1287` named it out of scope | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_wheel_carries_its_hook_prebuilt_or_compiles_it.py`

## Motivation

The hook and the spine are compiled when a capture starts
(`compile_hook`, `compile_spine`), so every capture host needs `cc`
and, for the spine, a static libc. `UX-1287` made `bga doctor` name
that prerequisite; an agent image built for BuildStream still has to
carry a compiler only for bga. There is one wheel kind, and it is pure.

## Decomposition

Input classes: a wheel built `prebuilt`, `source`, and an unknown kind;
both built in one tree, prebuilt first; at capture, a prebuilt binary
whose stamp matches, whose source changed, built on another machine,
or missing beside its stamp; each with and without `cc` on PATH.
Journey: build the wheel once, install on a host with no compiler,
`bga doctor`, then a capture.

## Required Fix

`setup.py` reads `BGA_HOOK`: `source` (default) builds today's pure
wheel; `prebuilt` compiles both into `native_trace/prebuilt/` with a
stamp (machine, compiler, sha256 of `hook.c` and `spine.c`), and the
wheel is `py3-none-<platform>`. `tools/native_trace/prebuilt.py` holds
the compile argv for both paths and `find()`, which answers only while
the stamp matches the shipped source and the machine. `compile_hook`
and `compile_spine` copy a found binary, else compile as before; doctor
reports `ok` with no compiler while both are found. CI's `packaging`
job builds both kinds; `installed-capture` installs the prebuilt one
and runs with a `cc` and `gcc` that exit 97 first on PATH.

## Out of Scope

A `manylinux` tag and PyPI upload; a prebuilt sdist install path
(`pip install` of an sdist with `BGA_HOOK=prebuilt` builds on the
installing host, which is the same mechanism); checking the sandbox's
glibc against the hook's symbol versions, which bites a hook compiled
at capture time the same way.

## Acceptance Test

Container: both kinds build from one tree, the prebuilt one is
`py3-none-linux_x86_64` with `hook.so`, `spine`, `stamp.json`; installed
into a venv, doctor and both compile functions run under a PATH with no
compiler. CI: `installed-capture` captures twice from the prebuilt wheel
with the poisoned `cc` first on PATH, and the shim ran.

## Outcome

**Premise:** held. The container half is below; the CI half is
`installed-capture` on PR #341 at `fa13338d` (job 125294408188), with a
`cc` and `gcc` that exit 97 first on PATH:

```text
  [ok  ] c-compiler: the wheel's prebuilt hook and spine match their sources (cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0); no C compiler needed
Using the wheel's prebuilt trace hook...
  The bwrap shim ran 9 time(s); 9 rewritten, 0 passed through.
Using the wheel's prebuilt trace hook...
  The bwrap shim ran 9 time(s); 9 rewritten, 0 passed through.
analyze @last resolved from the store, in a foreign venv
```

### The gap, measured

At `6a3a2e2c`, `BGA_HOOK` is not read; the wheel installed into a venv,
doctor run under a PATH holding only `python3`:

```text
$ BGA_HOOK=prebuilt pip wheel -q --no-deps -w gap . && ls gap; unzip -l gap/*.whl | grep -c prebuilt/
bga-0.6.0-py3-none-any.whl
0
fail no C compiler (cc/gcc) found on PATH - required to build the LD_PRELOAD hook
```

### The close, measured

Both kinds from one copied tree, prebuilt first; the prebuilt one
installed, same PATH:

```text
bga-0.6.0-py3-none-linux_x86_64.whl
bga-0.6.0-py3-none-any.whl
    22264  bga/_tools/native_trace/prebuilt/hook.so
   938408  bga/_tools/native_trace/prebuilt/spine
      270  bga/_tools/native_trace/prebuilt/stamp.json
ok the wheel's prebuilt hook and spine match their sources (cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0); no C compiler needed
/tmp/tmpn2pbtc6k/hook.so
/tmp/tmpn2pbtc6k/spine
```

The guard: `15 passed` in 15.13 / 14.69 / 14.07s single-process.

| mutation | reddened | run |
|---|---|---|
| M1 `find` skips the source sha256 | four stale-source tests | 4 failed, 11 passed |
| M2 `find` skips the machine | another machine's binary is not used | 1 failed, 14 passed |
| M3 the source kind compiles binaries too | the source wheel is pure and carries no binary | 1 failed, 14 passed |
| M4 the tag keeps the Python ABI | tagged for this machine and no Python ABI | 1 failed, 14 passed |
| M5 `compile_hook` skips the prebuilt | copied with an empty PATH | 1 failed, 14 passed |
| M6 doctor ignores the prebuilt | doctor needs no compiler while both match | 1 failed, 14 passed |
| M7 the spine left out of the wheel | carries both binaries and their stamp | 1 failed, 14 passed |
| reverted | — | 15 passed |

### Deviation

A first draft cleared `build/lib/.../prebuilt` before a source build, so
a source wheel built after a prebuilt one could not inherit it. Its
mutation stayed green: `has_ext_modules` sends the prebuilt build to
`build/lib.<platform>`, apart from the pure `build/lib`, so the clear
guarded nothing and is gone. `setuptools>=70.1` because
`setuptools.command.bdist_wheel` lands there.
