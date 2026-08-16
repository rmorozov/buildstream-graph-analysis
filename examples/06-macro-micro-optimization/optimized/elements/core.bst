# MICRO FIX: `notparallel: True` removed - this element's eight ~1s
# translation units now compile at the project's real `--max-jobs`
# instead of strictly one at a time.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/core
variables:
  generator: Unix Makefiles
