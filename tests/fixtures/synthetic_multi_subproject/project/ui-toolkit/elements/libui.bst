kind: cmake
sources:
- kind: git
  url: upstream:ui-toolkit/libui.git
  track: main
variables:
  cmake-local: -DBUILD_SHARED_LIBS=ON

depends:
- libwidgets.bst
- data-format.bst:elements/libjson.bst
