# Final element - depends on every library plus core.
kind: cmake
depends:
- filename: core.bst
  type: build
- filename: lib-a.bst
  type: build
- filename: lib-b.bst
  type: build
- filename: lib-c.bst
  type: build
- filename: lib-d.bst
  type: build
- filename: lib-e.bst
  type: build
- filename: lib-f.bst
  type: build
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/app
variables:
  generator: Unix Makefiles
