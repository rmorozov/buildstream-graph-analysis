# Independent leaf element - depends only on runtime.bst, so all eight
# work-*.bst elements are simultaneously buildable, ready at the same
# time. Real wall-clock work (sleep, not a busy-loop, so duration is
# deterministic regardless of the CI runner's CPU speed) - held long
# enough to be visible against BuildStream's own timestamp resolution,
# and against a small --builders count, to produce genuine resource/
# scheduler-wait gaps for the elements that can't start immediately.
kind: manual
depends:
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 3"
