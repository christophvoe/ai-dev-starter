.PHONY: help install sync lock lint format typecheck test test-cov check clean pre-commit scrape scrape-list scrape-tag scrape-article scrape-bookmarks summarize

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────

install: ## First-time setup: create venv, install all deps, install pre-commit hooks
	uv sync
	uv run pre-commit install
	@echo "✓ Setup complete. Run 'make check' to verify."

sync: ## Sync dependencies (fast — uses lockfile)
	uv sync

lock: ## Re-resolve and update uv.lock
	uv lock

update: ## Update all dependencies to latest compatible versions
	uv lock --upgrade
	uv sync

# ── Code Quality ──────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	uv run ruff check src/ tests/

format: ## Auto-format code with ruff
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

typecheck: ## Run mypy type checker
	uv run mypy src/

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage report
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

check: lint typecheck test ## Run all checks (lint + typecheck + test)
	@echo "✓ All checks passed."

# ── Pre-commit ────────────────────────────────────────────────────────────────

pre-commit: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

pre-commit-update: ## Update pre-commit hook versions
	uv run pre-commit autoupdate

# ── Project Commands ──────────────────────────────────────────────────────────
# Pass OUTPUT=path/to/dir to save articles to a different directory/repo.
# Pass DATED=1 to save into a YYYY-MM-DD subfolder.
# Example: make scrape OUTPUT=../my-knowledge-repo/data/knowledge/raw/medium
# Example: make scrape DATED=1

OUTPUT_FLAG = $(if $(OUTPUT),--output "$(OUTPUT)",)
DATED_FLAG = $(if $(DATED),--dated,)

scrape: ## Scrape your coding list (default)
	uv run python -m knowledge.medium_scraper --list "https://medium.com/@voeltzke.christoph/list/coding-6c7978acb372" --max 20 $(OUTPUT_FLAG) $(DATED_FLAG)

scrape-list: ## Scrape a Medium list (usage: make scrape-list URL="https://...")
	uv run python -m knowledge.medium_scraper --list "$(URL)" --max 20 $(OUTPUT_FLAG) $(DATED_FLAG)

scrape-tag: ## Scrape a tag (usage: make scrape-tag TAG="ai-agents")
	uv run python -m knowledge.medium_scraper --tag "$(TAG)" --max 10 $(OUTPUT_FLAG) $(DATED_FLAG)

scrape-article: ## Scrape a single article (usage: make scrape-article URL="https://...")
	uv run python -m knowledge.medium_scraper --article "$(URL)" $(OUTPUT_FLAG) $(DATED_FLAG)

scrape-bookmarks: ## Scrape your private bookmarks
	uv run python -m knowledge.medium_scraper --bookmarks --max 20 $(OUTPUT_FLAG) $(DATED_FLAG)

summarize: ## Show digest of recent articles in knowledge base
	uv run python -m knowledge.medium_scraper --summarize --max 10 $(OUTPUT_FLAG)

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage dist/ build/ *.egg-info
