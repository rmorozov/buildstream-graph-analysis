# Stages a header and a static library that a dependent element can
# genuinely consume. Five staged files in total.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/base
variables:
  generator: Unix Makefiles
