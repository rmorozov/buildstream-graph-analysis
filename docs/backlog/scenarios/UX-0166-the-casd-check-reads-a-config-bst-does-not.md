# UX-166: the casd check reads a config bst does not

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-161 (the detection this corrects) | **Topic:** capture

## Motivation

UX-161's detection works — round 17 verified the positive and negative
cases live against a manually started daemon. But its answer to "which
cache directory does this build use" diverges from BuildStream's own:

- `buildstream_cache_dir` reads only
  `$XDG_CONFIG_HOME/buildstream.conf`
  (`tools/bst_native_build_tracer.py:452-468`), while installed
  bst 2.7 tries **`buildstream2.conf` first**
  (`buildstream/_context.py:279`). A user with `cachedir` in
  `buildstream2.conf` — the file bst's own docs lead with — gets the
  check pointed at the wrong directory: a silent false negative on
  the real daemon, or a false positive against one on the XDG default.
- The `cachedir:` parse is the same naive top-level `startswith` that
  UX-162 item 4 just fixed for `element-path:` — no indent, quote or
  trailing-comment tolerance. Same lesson, next key.
- `os.path.abspath(arg)` on the daemon's argv resolves relative paths
  against *bga's* cwd, not the daemon's.

## Required Fix

Resolve the config the way bst does (`buildstream2.conf` then
`buildstream.conf`, same precedence), parse `cachedir:` with the
UX-162 tolerant parser (shared function, not a second copy), and skip
relative argv entries rather than mis-resolving them (a daemon started
with a relative cache path is unmatchable evidence, not a guess).

## Out of Scope

- The detection mechanics and wording (verified live, unchanged).

## Acceptance Test

A `cachedir` set only in `buildstream2.conf`: the check matches a
daemon on that directory and ignores one on the XDG default (both
asserted through the `proc_root` seam). Quoted/indented `cachedir:`
parses. The UX-161 tests pass unchanged.

## What was built

`buildstream_cache_dir()` now follows bst 2.7's own precedence —
`buildstream2.conf` first, then `buildstream.conf`
(`buildstream/_context.py:279`) — so a `cachedir` set in the file bst
actually reads is the one the stale-casd check uses. Reading only
`buildstream.conf` meant the check could miss the real daemon entirely,
or alarm about a directory nothing was using.

The `cachedir:` parse moved onto `read_scalar_key`, the shared scalar
reader UX-162 wrote for `element-path:` — same quoting, same comment
handling, one implementation instead of two `startswith` guesses.

`detect_stale_casd` normalises the cache directory taken from casd's
last positional argv: an absolute path is `normpath`ed so
`/x/./cache` and `/x/cache` compare equal, and a *relative* one is
skipped rather than resolved, because it was relative to casd's cwd and
not bga's — resolving it against bga's cwd is how a check invents a
daemon that is not there.

Guards in `tests/unit/test_stale_casd.py`; each mutation red.
