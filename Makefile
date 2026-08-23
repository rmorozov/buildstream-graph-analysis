# BuildStream Build Efficiency Analyzer - Makefile

.PHONY: test test-small test-medium test-large test-fast test-e2e lint lint-docs dev-run clean check-clean install dev help

# Default target
help:
	@echo "BuildStream Build Efficiency Analyzer (bga) - Available targets:"
	@echo ""
	@echo "  make test        - Run the whole suite (~6 min) - required before marking a task done"
	@echo "  make test-small  - The default tier: 160 files, ~20s - the inner loop"
	@echo "  make test-medium - Process/node harnesses: 53 files, ~3 min"
	@echo "  make test-large  - Scale fixtures and real process trees: 7 files, ~2.5 min"
	@echo "  make test-fast   - small + medium, everything that needs no real bst"
	@echo "  make test-e2e    - Run end-to-end tests directly"
	@echo "  make lint        - Run code linting (ruff)"
	@echo "  make lint-docs   - Markdown correctness (UX-98); part of make lint"
	@echo "  make dev-run     - Analyze a sample fixture and print a real report (fast smoke check)"
	@echo "  make clean       - Remove build artifacts and cache"
	@echo "  make check-clean - Fail if any ignored/build-artifact path is tracked by git"
	@echo "  make install     - Install package in production mode"
	@echo "  make dev         - Install package in development mode"
	@echo ""

# UX-238: four tiers, assigned from measured per-file duration in
# tests/tiers.py. `test` still runs everything and is what a task's
# Definition of Done requires; the tiers are for the inner loop.
#
#   small   160 files    18.2s   pure Python over in-memory fixtures
#   medium   53 files   184.0s   spawns a process or a node harness
#   large     7 files   159.0s   scale fixtures, real process trees
#   enormous  (the `bst` marker) needs a real bst/bwrap build
#
# Run the tier your change touches while you work; run `make test`
# before you mark anything done.
test:
	python -m pytest tests/ -v

test-small:
	python -m pytest tests/ -m small -q

test-medium:
	python -m pytest tests/ -m medium -q

test-large:
	python -m pytest tests/ -m large -q

# Everything that does not need a real bst build - the widest tier a
# machine without BuildStream can actually run to completion.
test-fast:
	python -m pytest tests/ -m "small or medium" -q

# Run end-to-end tests directly  
test-e2e:
	python tests/test_e2e.py

# Code linting (ruff, pyflakes rule set - see pyproject.toml's [tool.ruff])
lint: lint-docs
	ruff check bga/ tools/ tests/

# UX-98: markdown correctness. Only the class that changes how a document
# renders is enabled - see .pymarkdown.json for why each disabled rule is
# disabled. Table cell counts are NOT checked here: PyMarkdown implements
# MD001-MD048 and the table rules are markdownlint v0.34+ additions with
# no equivalent, so tests/unit/test_docs_links_and_commands.py owns that
# one - which is the defect this repo actually shipped, five times.
lint-docs:
	python3 -m pymarkdown --config .pymarkdown.json scan -r README.md docs/

# Local dev convenience: analyze a checked-in sample fixture and print a
# real report - one command from "I changed some code" to "I can see
# what a real report looks like" (P4-03). Pass ARGS=--large for the
# bigger synthetic_multi_subproject fixture instead of the small,
# instant golden one.
dev-run:
	./tools/dev_run.sh $(ARGS)

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/
	@echo "Cleaned build artifacts"

# Guard: fail if any file matching .gitignore patterns is nonetheless tracked by git.
# Run this before every commit. It would have caught bga.egg-info/, bga/**/__pycache__/,
# and tests/__pycache__/ getting committed in PR #9.
check-clean:
	@tracked_ignored=$$(git ls-files -ci --exclude-standard); \
	if [ -n "$$tracked_ignored" ]; then \
		echo "ERROR: the following tracked files match .gitignore patterns:"; \
		echo "$$tracked_ignored"; \
		echo ""; \
		echo "Fix with: git rm -r --cached <path>  (then commit the removal)"; \
		exit 1; \
	fi
	@echo "OK: no ignored files are tracked"

# Install in production mode
install:
	pip install -e .

# Install in development mode with test dependencies
dev:
	pip install -e ".[dev]"
