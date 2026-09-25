# One of 24 narrow elements (see the others narrow-*.bst) - real,
# independent work ready alongside giant.bst from the start (no
# dependency on it), so bst's own `--builders` is what bounds how
# many of these 24 plus the giant run at once.
#
# `notparallel: True` is BuildStream's real per-element parallelism
# control (examples/06-macro-micro-optimization's core.bst): it forces
# this element's own `make` to `-j1`, and an explicit `-j1` on the
# command line takes GNU make out of jobserver mode entirely - neither
# `--builders` nor `--jobserver auto` can widen it. This models a real
# single-threaded recipe (autotools' `configure`, a `python setup.py`
# step, a hand-written serial `make`), not a proxy for one.
#
# 24 generated C files at 1800 lines each - examples/11-serial-giant's
# README measured this host's single-core rate at roughly 1s per
# 1800-line unit, so ~24s of real, single-core `cc1` work per element.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
  notparallel: True
config:
  configure-commands:
  - sh generate.sh narrow_24 24 1800
  - |
    %{cmake}
