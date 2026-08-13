kind: cmake
sources:
- kind: git
  url: upstream:data-format/libxml.git
  track: main
variables:
  cmake-local: -DBUILD_SHARED_LIBS=ON

depends:
- core-utils.bst:elements/libcore.bst
