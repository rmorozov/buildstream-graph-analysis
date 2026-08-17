# One of six independent libraries. Nothing in lib-d's sources uses
# any other lib-*'s output, and nothing uses codegen.bst either -
# but this baseline project declares both anyway:
#
#   MACRO PROBLEM 1: a six-deep chain (lib-b after lib-a, lib-c after
#   lib-b, ...) instead of a six-wide fan-out off core.bst.
#   MACRO PROBLEM 2: an unused build dependency on codegen.bst.
#
# Both are declared-only: removing them (see ../optimized/) changes no
# source file and no build command.
#
# UX-46 measured this rather than taking the comment's word for it:
# a real traced build shows this element opens none of the files
# staged by codegen.bst, core.bst, or any sibling lib - only
# toolchain.bst is genuinely read. An earlier version of this
# comment claimed lib-f consumed codegen.bst; it does not.
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
