# The heaviest element (8 real ~1s translation units) and the root of the
# whole graph - every other compiled element depends on it.
#
# MICRO PROBLEM (deliberate): `notparallel: True` is BuildStream's real
# per-element parallelism control - it forces this element's own native
# build system to a single job (`${JOBS}` -> `-j1` in
# buildstream-plugins' cmake.yaml). Eight ~1s translation units that
# could compile four-at-a-time therefore compile strictly one at a time.
#
# BuildStream's own log records exactly one START/SUCCESS pair for this
# element either way, so `bga`'s Plane 1 cannot tell the difference
# between "this element is legitimately 9s of work" and "this element is
# 2.5s of work stretched to 9s by a one-line misconfiguration". Seeing
# it requires Plane 2 (tools/bst_native_build_tracer.py).
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/core
variables:
  generator: Unix Makefiles
  notparallel: True
