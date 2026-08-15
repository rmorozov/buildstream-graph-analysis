# Final real build step - links all four libraries + core into a real
# executable.
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
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/app
variables:
  generator: Unix Makefiles
