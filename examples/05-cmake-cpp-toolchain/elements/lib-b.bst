# One of four independent libraries depending on core.bst - a genuine
# 4-way fan-out (mirrors examples/04's lib-a..d.bst design intent), now
# real gcc/g++ compilation instead of sleep.
kind: cmake
depends:
- filename: core.bst
  type: build
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/lib-b
variables:
  generator: Unix Makefiles
