# UX-120: the eight siblings, merged. Identical work, one staging instead
# of eight - which is exactly what the merge candidate projected.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
- filename: bulk.bst
  type: build
sources:
- kind: local
  path: files/src/tiny-merged
variables:
  generator: Unix Makefiles
