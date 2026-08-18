# One element that really runs commands inside the sandbox, so Plane 2
# has processes to attribute.
#
# Only the staged `sh` and `sleep` are used - no coreutils beyond that.
# That is deliberate three times over:
#
#   - the fixture stays under 3 MB;
#   - `LD_PRELOAD` only sees dynamically-linked executables, so a static
#     busybox would produce a trace with zero processes in it (tried
#     first; it does);
#   - `dash` leaves the shell via `_exit()`, which bypasses libc's exit
#     path and so never fires the shim's destructor - a build made only
#     of `sh -c` wrappers yields START lines with no END, no measurable
#     sandbox interval, and nothing for `bga correlate` to match on.
#     `sleep` is an ordinary process that exits normally, so it both
#     closes a record and gives the element a span longer than the log's
#     millisecond resolution.
kind: manual
depends:
- filename: base.bst
  type: build
sources:
- kind: local
  path: files/src
config:
  build-commands:
  - "sleep 1"
  - "sh -c 'sleep 1'"
  install-commands:
  - "sleep 1"
