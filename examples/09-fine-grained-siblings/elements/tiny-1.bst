# One of N siblings with the identical build-dependency set, each doing
# sub-second work inside a sandbox that stages the whole C++ toolchain.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
- filename: bulk.bst
  type: build
sources:
- kind: local
  path: files/src/tiny-1
variables:
  generator: Unix Makefiles
