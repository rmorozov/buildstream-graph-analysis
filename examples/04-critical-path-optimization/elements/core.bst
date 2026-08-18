# The single highest-blast-radius element in this project (5 downstream
# elements: lib-a..d + app) and deliberately the slowest (4s) - the
# critical-path bottleneck docs/guides/optimization-walkthrough.md's structural
# optimization step targets directly (optimized/core.bst cuts this to
# 2s, simulating a real "found a faster way to build this" fix).
kind: manual
depends:
- filename: base-generate.bst
  type: build
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 4"
