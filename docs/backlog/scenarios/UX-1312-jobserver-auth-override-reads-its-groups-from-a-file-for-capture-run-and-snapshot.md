# UX-1312: `--jobserver-auth-override` takes only inline groups, and real element names are long junction-relative paths

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1302 | **Found by:** the owner's request (Ruslan, 2026-10-03): "let's also teach bga snapshot to support jobserver-auth-override as well. take into consideration length of path, so maybe we are to teach it to read overrides from file" | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_auth_override_reads_a_file.py`

## Motivation

`bga snapshot` already forwards the flag (`UX-1302`, `bga.cli.apply_capture_env_flags`).
What it takes is inline `style:glob[,glob]` groups, and a build with
dozens of long element paths makes that line unmanageable.

## Decomposition

Input classes: an inline group; an `@PATH` word; `@PATH` mixed with inline and repeated; a file with comments and blank lines; globs comma- vs whitespace-separated; a missing file; a bad style (with its line); `capture run` vs `bga snapshot`. Journey: `bga snapshot --jobserver auto --jobserver-auth-override @overrides.conf -- bst build all.bst`.

## Required Fix

**Decision:** `--jobserver-auth-override` words starting `@` are read
as files by `_auth_override_groups`, which the one translator calls, so
`capture run` and `snapshot` share it.

- One `style:glob[,glob ...]` group per line; globs may be comma- or
  whitespace-separated after the `style:` (a long list wraps on spaces
  as readily as on commas); blank and `#` lines are skipped.
- `@PATH` mixes with inline words and repeats; it is relative to the cwd.
- A missing or unreadable file, a style outside `{fd,fifo,off,flto}`
  (`cli.AUTH_OVERRIDE_STYLES`, held equal to the shim's by the guard) or
  a style with no glob prints `bga: error: ... PATH:LINE` and exits 2.
  The shim still ignores a bad style in the inline form; that is unchanged.
- Sticky: `bga snapshot`'s `.bga/config` holds only `trace_opens` and
  `trace_spine` (`_sticky_config`); the override is per capture, as
  `--jobserver` is, and stays unstored.
- Help: `CAPTURE_RUN_BGA_FLAGS` line, the `capture run --help` epilog
  line, `bga snapshot --help`; docs: cli.md entry, jobserver.md example,
  which `test_the_jobserver_guide_names_every_per_element_switch.py` now
  also runs through the parser.

## Out of Scope

A config key or an environment variable carrying the file; `@PATH` for
`--lto-cap` or `--wrapper-dir`; making the shim reject a bad inline style.

## Acceptance Test

`bga snapshot --jobserver auto --jobserver-auth-override @o.conf -- true`
sets `BST_TRACE_JOBSERVER_AUTH_MAP` from the file; a missing file exits 2.

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held — `@PATH` was taken as a literal group, silently.

### The gap, measured

```text
$ (HEAD edcd878f) _translate_capture_jobserver_auth_override(['capture','run','--jobserver-auth-override','@nope.conf','--','true'])
BST_TRACE_JOBSERVER_AUTH_MAP=@nope.conf      # no error, no override applied
```

### After

```text
$ bga capture run --jobserver-auth-override @nope.conf -- true; echo "exit $?"
bga: error: --jobserver-auth-override: cannot read nope.conf: [Errno 2] No such file or directory: 'nope.conf'
exit 2
$ printf 'off:a.bst\nbogus:b.bst\n' > o.conf; bga capture run --jobserver-auth-override @o.conf -- true
bga: error: --jobserver-auth-override: o.conf:2: expected fd|fifo|flto|off:GLOB[,GLOB], got 'bogus:b.bst'
$ PYTEST_XDIST= pytest -q tests/unit/test_the_auth_override_reads_a_file.py tests/unit/test_the_jobserver_guide_names_every_per_element_switch.py
24 passed
```

### Mutations verified red and reverted (11)

| # | mutation | reddened |
|---|---|---|
| M1 | `#` lines not skipped | 3 failed 21 passed |
| M2 | style not checked | 1 failed 23 passed |
| M3 | empty glob list accepted | 1 failed 23 passed |
| M4 | error omits the line number | 2 failed 22 passed |
| M5 | unreadable file read as empty | 1 failed 23 passed |
| M6 | globs split on `,` only | 2 failed 22 passed |
| M7 | spaced form never reads a file | 9 failed 15 passed |
| M8 | `=` form never reads a file | 1 failed 23 passed |
| M9 | `flto` dropped from the styles | 3 failed 21 passed |
| M10 | an inline `# comment` kept as globs (the verifier's finding, fixed after) | 3 of 12 |
| M11 | a value naming a file with a space split on whitespace (the verifier's finding, fixed after) | 1 of 12 |

Reverted from a copy: 10 passed (guard alone).

### Deviation from the Required Fix

None. Sticky: `.bga/config` holds `trace_opens` and `trace_spine` only,
so the override is per capture and unstored; no config key added.
