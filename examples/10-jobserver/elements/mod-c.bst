# One of two cmake elements (see mod-d.bst) - independent of every other
# mod-*.bst. `files/gen/cmake/generate.sh` (staged as this element's own
# source) writes 64 generated C files, a header, a main(), and a
# CMakeLists.txt *inside the sandbox*, run as the first configure-
# commands step, before `%{cmake}` configures against it (UX-848).
# `generator: Unix Makefiles` - stage_cpp_toolchain.sh stages no ninja,
# cmake's default generator. `cmake --build ... -- ${JOBS}` (cmake.yaml)
# passes `-jN` as an explicit make argument rather than through
# MAKEFLAGS - this pair does not join the jobserver in this round
# (UX-843, not yet landed here).
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh mod_c 64 1800
  - |
    %{cmake}
