# Added for P4-12/P4-15's kind-diversity requirement (both tasks'
# Acceptance Test asks for a real, kind-diverse fixture) - `manual` is
# the "genuine compute work" contrast kind against the fixture's other
# additions (`all.bst`, kind: stack) and existing `subproj-junction.bst`
# (kind: junction) - see docs/tasks/P4-12-element-kind-based-heuristics.md's
# Background for why these specific kinds were chosen.
kind: manual
depends:
- filename: base.bst
  type: build
config:
  install-commands:
  - "true"
