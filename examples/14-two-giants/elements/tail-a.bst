# UX-1132: giant-a.bst's own chain - a small element that waits on it,
# so each giant sits on a critical chain of its own (8 units, 1800 lines).
kind: cmake
depends:
- filename: toolchain.bst
  type: build
- filename: giant-a.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh tail_a 8 1800
  - |
    %{cmake}
