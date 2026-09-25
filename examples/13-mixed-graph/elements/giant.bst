# UX-1010: the same giant as examples/11-serial-giant's own giant.bst -
# 256 generated C files (files/gen/cmake/generate.sh, hardlink-cloned
# in, not a second copy), `giant_lines` lines each (default 9800). No
# `max-jobs` cap here: unlike 11, this project's win shape is about
# `--builders` (how many elements run at once), not `max-jobs` (how
# wide one element's own recipe runs) - the giant uses BuildStream's
# own default width while the 24 narrow-*.bst elements queue for a
# builder slot beside it.
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
  - sh generate.sh giant 256 %{giant_lines}
  - |
    %{cmake}
