# BuildStream Build Efficiency Analyzer - Makefile

.PHONY: test test-e2e lint dev-run clean check-clean install dev help

# Default target
help:
	@echo "BuildStream Build Efficiency Analyzer (bga) - Available targets:"
	@echo ""
	@echo "  make test        - Run all tests with pytest"
	@echo "  make test-e2e    - Run end-to-end tests directly"
	@echo "  make lint        - Run code linting (ruff)"
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
lint:
	ruff check bga/ tools/ tests/

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
