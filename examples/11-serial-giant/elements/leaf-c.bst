# One of three small leaves (see leaf-a.bst, leaf-b.bst) that wait on
# giant.bst - the shape UX-857 exists to show: nothing else can start
# until the one long element finishes, so its own cap is the whole
# critical path's cap. 8 generated C files, same generator as
# giant.bst, a tenth its size.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
- filename: giant.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh leaf_c 8 1800
  - |
    %{cmake}

