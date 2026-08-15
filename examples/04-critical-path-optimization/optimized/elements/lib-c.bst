# One of four independent libraries depending on core.bst - a genuine
# 4-way fan-out. With a builder count smaller than 4, real
# RESOURCE_WAIT/SCHEDULER_WAIT gaps appear here - see
# docs/optimization-walkthrough.md.
kind: manual
depends:
- filename: core.bst
  type: build
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 2"
