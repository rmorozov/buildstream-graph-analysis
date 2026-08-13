# Shared library, no internal dependencies - the diamond's root.
kind: cmake
sources:
- kind: git
  url: upstream:core-utils/libcore.git
  track: main
variables:
  cmake-local: -DBUILD_SHARED_LIBS=ON
