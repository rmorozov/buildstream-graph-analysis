# Highest-blast-radius module (5 downstream: lib-a..d + app) - real,
# deliberately-heaviest compile (6 generated .cpp files, see
# ../generate_sources.py) mirroring examples/04's core.bst (sleep 4)
# design intent, but now real gcc/g++ work instead of a proxy.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/src/core
variables:
  generator: Unix Makefiles
