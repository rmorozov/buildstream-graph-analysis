# A "code generator" module. Only lib-f.bst genuinely consumes its
# output - but in this baseline project every lib-*.bst declares a build
# dependency on it (MACRO PROBLEM 2), putting it on the critical path of
# five elements that don't need it.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/codegen
variables:
  generator: Unix Makefiles
