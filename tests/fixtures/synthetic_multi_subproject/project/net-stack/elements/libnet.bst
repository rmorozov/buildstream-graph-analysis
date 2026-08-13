kind: cmake
sources:
- kind: git
  url: upstream:net-stack/libnet.git
  track: main
variables:
  cmake-local: -DBUILD_SHARED_LIBS=ON

depends:
- libcrypto.bst
- core-utils.bst:elements/liblog.bst
