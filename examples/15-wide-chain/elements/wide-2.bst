# UX-1132: the chain's second link - waits on wide-1.bst, same size.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
- filename: wide-1.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh wide_2 128 %{unit_lines}
  - |
    %{cmake}
