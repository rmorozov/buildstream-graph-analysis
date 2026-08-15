# Real build target dependency - stages a real shell (busybox) so
# manual.bst elements below have something to run commands with.
kind: import
sources:
- kind: local
  path: files/runtime
