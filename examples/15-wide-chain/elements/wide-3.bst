# UX-1132: the chain's third link - waits on wide-2.bst, same size.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
- filename: wide-2.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh wide_3 128 %{unit_lines}
  - |
    %{cmake}
