# The same real gcc/g++/cmake/make/binutils sysroot as examples/06 -
# stage_cpp_toolchain.sh hardlink-clones it here too (UX-848: do not
# stage a second one).
kind: import
sources:
- kind: local
  path: files/toolchain
