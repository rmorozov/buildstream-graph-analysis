# UX-1132: the first of two giants - 11's own element (256 generated C
# units, `giant_lines` each), ready from the start beside giant-b.bst.
# Neither caps the other: `check_shape_property.py two-giants` reads
# both wider than one job and their BUILD spans overlapping.
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
  - sh generate.sh giant_a 256 %{giant_lines}
  - |
    %{cmake}
