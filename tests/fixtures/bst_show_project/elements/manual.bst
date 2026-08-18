# Added for P4-12/P4-15's kind-diversity requirement (both tasks'
# Acceptance Test asks for a real, kind-diverse fixture) - `manual` is
# the "genuine compute work" contrast kind against the fixture's other
# additions (`all.bst`, kind: stack) and existing `subproj-junction.bst`
# (kind: junction) - see docs/backlog/tasks/P4-12-element-kind-based-heuristics.md's
# Background for why these specific kinds were chosen.
#
# UX-22: also doubles as this fixture's real per-element `max-jobs`
# override (`public: bst: max-jobs:` - confirmed empirically the real
# mechanism, NOT `variables: max-jobs:`, which BuildStream rejects as
# "invalid redefinition of protected variable" - and NOT visible via
# `%{vars}` either, only `%{public}`). Not a dependency of `app.bst` (the
# target other tests against this fixture use), so it doesn't affect them.
kind: manual
depends:
- filename: base.bst
  type: build
config:
  install-commands:
  - "true"
public:
  bst:
    max-jobs: 16
