# A full, real gcc/g++/cmake/make/binutils sysroot, staged from the host
# running `bst` (see ../stage_cpp_toolchain.sh) - same mechanism and same
# reasoning as examples/05-cmake-cpp-toolchain/elements/toolchain.bst.
kind: import
sources:
- kind: local
  path: files/toolchain
