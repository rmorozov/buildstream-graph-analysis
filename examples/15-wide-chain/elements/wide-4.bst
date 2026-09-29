# UX-1132: the chain's tail - waits on wide-3.bst, same size.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
- filename: wide-3.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh wide_4 128 %{unit_lines}
  - |
    %{cmake}
