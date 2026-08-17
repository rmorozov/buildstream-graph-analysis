# The TRUE POSITIVE case: declares exactly what user.bst declares, and
# consumes none of it. `files/unrelated/unrelated.cpp` includes nothing
# from base.bst, so a real traced build opens zero of its five staged
# files and UX-46 must report this edge as an unused-dependency
# candidate.
#
# The pair (user.bst, unrelated.bst) is the point of this project: same
# declared dependencies, different real usage.
kind: cmake
depends:
- filename: base.bst
  type: build
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/unrelated
variables:
  generator: Unix Makefiles
