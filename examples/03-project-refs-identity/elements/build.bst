# Real work combined with the git-ref-tracked source, so the "touch and
# rebuild" retry-data run (see examples/README.md) produces a genuine
# rebuild with measurable duration, not an instant one.
kind: manual
depends:
- filename: libbar.bst
  type: build
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 2"
