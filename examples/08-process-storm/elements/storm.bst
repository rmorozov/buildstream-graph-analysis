# 2000 short-lived dynamically-linked processes in one sandbox.
#
# `cat /dev/null` rather than a builtin: the point is the exec, and a
# shell builtin never makes one. Two thousand rather than a round
# hundred because the quantity being measured is per-process cost - at
# 100 processes it hides inside the sandbox's own setup time, and at
# 2000 it is most of the element's wall clock.
kind: manual
depends:
- filename: toolchain.bst
  type: build
config:
  install-commands:
  - |
    i=0
    while [ "$i" -lt 2000 ]; do
      cat /dev/null
      i=$((i + 1))
    done
