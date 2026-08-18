# MACRO FIX 1: no dependency on any sibling lib-* - all six fan out off
# core.bst and build concurrently.
# MACRO FIX 2: codegen.bst is declared by lib-f.bst alone rather than by
# every lib. Note the claim is about *where the edge is declared*, not
# about consumption: UX-46 traced a real build and found lib-f opens no
# file staged by codegen.bst either (see ../elements/lib-f.bst, whose
# own comment records the same measurement). An earlier version of this
# line said lib-f was "the one element that actually consumes it",
# which the measurement contradicts. The fix is still the right one -
# one declared edge instead of six is six fewer ordering constraints -
# it just is not justified by consumption.
kind: cmake
depends:
- filename: core.bst
  type: build
- filename: codegen.bst
  type: build
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/lib-f
variables:
  generator: Unix Makefiles
