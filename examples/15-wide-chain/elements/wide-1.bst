# UX-1132: the chain's head - 128 generated C units, `unit_lines` each.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh wide_1 128 %{unit_lines}
  - |
    %{cmake}
