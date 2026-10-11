# UX-1283: giant.bst's twin, for `both.bst` - two memory-bound giants
# ready at once draw on one pool, the case the seed must not overcommit.
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
  - sh generate.sh mem_giant_b 32 %{mem_lines}
  - |
    %{cmake}
