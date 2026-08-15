# A full, real gcc/g++/cmake/make/binutils sysroot, staged from the host
# running `bst` (see ../stage_cpp_toolchain.sh) - BuildStream's sandbox
# binds in nothing from the host except staged dependencies, so every
# binary, shared library, and header search path a real C/C++ build needs
# has to be staged explicitly, at the exact absolute path gcc/cmake
# hardcode internally (not relocatable).
kind: import
sources:
- kind: local
  path: files/toolchain
