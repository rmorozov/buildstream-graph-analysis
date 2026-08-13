kind: cmake
sources:
- kind: git
  url: upstream:ui-toolkit/libwidgets.git
  track: main
variables:
  cmake-local: -DBUILD_SHARED_LIBS=ON

depends:
- core-utils.bst:elements/libcore.bst
