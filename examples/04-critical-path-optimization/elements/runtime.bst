# Provides /bin/sh (and other applets) for every manual.bst element in this
# project to actually run commands in. The sandbox is built purely from
# staged dependencies (no host binding), so something has to provide a
# shell - populated by examples/stage_runtimes.sh at build time, not
# committed. See project.conf's own header comment.
kind: import
sources:
- kind: local
  path: files/runtime
