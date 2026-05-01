.PHONY: install dev-install test lint typecheck audit clean build help

PYTHON   := python3
PKG      := mcp_einvoicing_de
AUDIT_OUT := audit/report.json

help:          ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:       ## Install the package (production deps only)
	pip install -e .

dev-install:   ## Install the package with all dev dependencies
	pip install -e ".[dev]"

test:          ## Run the test suite with coverage
	pytest --tb=short

lint:          ## Run ruff linter
	ruff check $(PKG)/ tests/ audit/

lint-fix:      ## Run ruff with auto-fix
	ruff check --fix $(PKG)/ tests/ audit/

typecheck:     ## Run mypy type checker
	mypy $(PKG)/

audit:         ## Run pre-publish audit against mcp-einvoicing-core
	$(PYTHON) audit/audit_vs_core.py --output $(AUDIT_OUT)

audit-strict:  ## Run audit; exit non-zero on any warning
	$(PYTHON) audit/audit_vs_core.py --output $(AUDIT_OUT) --fail-on warnings

audit-ci:      ## Run audit in CI mode (blocking failures only)
	$(PYTHON) audit/audit_vs_core.py --output $(AUDIT_OUT) --fail-on blocking

build:         ## Build wheel and sdist
	$(PYTHON) -m build

clean:         ## Remove build artefacts and caches
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete

run:           ## Start the MCP server (stdio transport)
	mcp-einvoicing-de
