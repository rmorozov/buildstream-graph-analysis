# UX-916: one of the two arms that cross `style_for_make_version` in a
# single capture (see switch-4-4.bst). The pair is identical but for
# the `make` its `PATH` resolves - `stage_cpp_toolchain.sh` stages a
# pinned 4.4.1 and a pinned 4.2.1 under /usr/lib/bga-make/<series>/,
# so which branch this element takes is the project's own declaration
# and not the staging host's. 8 generated C files, the leaves' size;
# depends on toolchain.bst alone, so neither arm sits on UX-857's
# critical path.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
environment:
  PATH: /usr/lib/bga-make/4.2:/usr/bin:/bin:/usr/sbin:/sbin
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh switch_4_2 8 1800
  - |
    %{cmake}
