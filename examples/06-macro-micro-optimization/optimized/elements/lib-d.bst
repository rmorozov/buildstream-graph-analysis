# MACRO FIX 1: no dependency on any sibling lib-* - all six fan out off
# core.bst and build concurrently.
# MACRO FIX 2: codegen.bst is declared only by lib-f.bst, the one
# element that actually consumes it.
kind: cmake
depends:
- filename: core.bst
  type: build
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/lib-d
variables:
  generator: Unix Makefiles
