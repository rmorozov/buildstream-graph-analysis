# The junctioned cmake element UX-872 exists to build: one trivial C
# file, real gcc/cmake/make - real enough for the jobserver decision to
# be real (UX-871/UX-842/UX-843), small enough that the build itself is
# not the point (Out of Scope: no second, bigger workload here).
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/hello
variables:
  generator: Unix Makefiles
