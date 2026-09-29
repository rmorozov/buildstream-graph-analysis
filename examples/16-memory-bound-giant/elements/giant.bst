# UX-1132: the memory-bound giant - 32 units of `mem_lines` lines, so
# each job's cc1 holds hundreds of MB to GB (project.conf has the rate).
# `check_shape_property.py memory-giant` reads its peak RSS per job.
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
  - sh generate.sh mem_giant 32 %{mem_lines}
  - |
    %{cmake}
