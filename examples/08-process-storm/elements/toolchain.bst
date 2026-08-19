# The same real gcc/g++/cmake/make/binutils sysroot examples/05, 06 and
# 07 use, staged from the host by ../stage_cpp_toolchain.sh (never
# committed - see .gitignore). Only `/bin/sh` and `/usr/bin/cat` are
# needed here; the whole sysroot is staged because it already exists as
# a hardlink clone and building a smaller one would cost real disk.
kind: import
sources:
- kind: local
  path: files/toolchain
