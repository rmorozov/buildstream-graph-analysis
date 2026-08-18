# BuildStream Build Efficiency Analyzer - Makefile

.PHONY: test test-e2e lint lint-docs dev-run clean check-clean install dev help

# Default target
help:
	@echo "BuildStream Build Efficiency Analyzer (bga) - Available targets:"
	@echo ""
	@echo "  make test        - Run all tests with pytest"
	@echo "  make test-e2e    - Run end-to-end tests directly"
	@echo "  make lint        - Run code linting (ruff)"
	@echo "  make lint-docs   - Markdown correctness (UX-98); part of make lint"
	@echo "  make dev-run     - Analyze a sample fixture and print a real report (fast smoke check)"
	@echo "  make clean       - Remove build artifacts and cache"
	@echo "  make check-clean - Fail if any ignored/build-artifact path is tracked by git"
	@echo "  make install     - Install package in production mode"
	@echo "  make dev         - Install package in development mode"
	@echo ""

# Run all tests with pytest
test:
	python -m pytest tests/ -v

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
