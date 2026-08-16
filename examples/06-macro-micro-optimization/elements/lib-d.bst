# One of six independent libraries. Nothing in lib-d's sources uses
# any other lib-*'s output, and nothing but lib-f uses codegen.bst -
# but this baseline project declares both anyway:
#
#   MACRO PROBLEM 1: a six-deep chain (lib-b after lib-a, lib-c after
#   lib-b, ...) instead of a six-wide fan-out off core.bst.
#   MACRO PROBLEM 2: an unused build dependency on codegen.bst.
#
# Both are declared-only: removing them (see ../optimized/) changes no
# source file and no build command.
kind: cmake
depends:
- filename: lib-c.bst
  type: build
- filename: core.bst
  type: build
- filename: codegen.bst
  type: build
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/lib-d
variables:
  generator: Unix Makefiles
