kind: cmake
sources:
- kind: git
  url: upstream:core-utils/liblog.git
  track: main
variables:
  cmake-local: -DBUILD_SHARED_LIBS=ON

depends:
- libcore.bst
