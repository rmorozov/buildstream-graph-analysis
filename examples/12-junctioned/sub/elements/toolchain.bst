# Same staged sysroot every cmake example uses - BuildStream's sandbox
# binds in nothing from the host (see ../../stage_cpp_toolchain.sh,
# which hardlink-clones into this subproject's own files/toolchain/
# too - a junctioned subproject is a real, separate BuildStream
# project, so `kind: local` sources resolve inside it, not the parent).
kind: import
sources:
- kind: local
  path: files/toolchain
