# UX-1284: 32 plain units compile wide, then `late` - 4 -flto units of
# late_k x unit_lines lines - links last, its lto1 the element's peak
# (project.conf has the measured ratios).
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
# the sandbox stages no mkdir: a second copy of the generator makes late/
- kind: local
  path: files/gen/cmake
  directory: late
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh giant 32 %{unit_lines}
  - cd late && sh generate.sh late 4 $((%{late_k} * %{unit_lines}))
  - |
    cat >> CMakeLists.txt <<'LATE'
    file(GLOB LATE_SOURCES "late/*.c")
    add_executable(late ${LATE_SOURCES})
    target_compile_options(late PRIVATE -flto)
    target_link_options(late PRIVATE -flto -flto-partition=one)
    add_dependencies(late giant)
    install(TARGETS late RUNTIME DESTINATION bin)
    LATE
  - |
    %{cmake}
