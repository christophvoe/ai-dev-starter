.PHONY: help install sync lock lint format typecheck test test-cov check clean pre-commit scrape scrape-list scrape-tag scrape-article scrape-bookmarks summarize notify bot review orchestrate-start orchestrate-next orchestrate-block orchestrate-resume orchestrate-status orchestrate-done orchestrate-check-failed orchestrate-explain onboard template-clean discover discover-scrape promote workspace

# PYTHONPATH so `uv run python -m agents.*` and `uv run python -m bot.*` resolve
export PYTHONPATH := src

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

discover: ## Discover trending articles from Medium tags (report only)
	uv run python -m knowledge.medium_scraper --discover --max 15 $(if $(TAGS),--discover-tags "$(TAGS)",) $(if $(KEYWORDS),--keywords "$(KEYWORDS)",) $(if $(CURATE),--curate,)

discover-scrape: ## Discover trending articles and auto-scrape top 10
	uv run python -m knowledge.medium_scraper --discover --max 15 --scrape-top 10 --enrich $(OUTPUT_FLAG) $(DATED_FLAG) $(if $(TAGS),--discover-tags "$(TAGS)",) $(if $(KEYWORDS),--keywords "$(KEYWORDS)",) $(if $(CURATE),--curate,)

# ── Telegram Notifications ────────────────────────────────────────────────────

notify: ## Send a Telegram notification (usage: make notify MSG="your message")
	uv run python -m bot.notify "$(MSG)"

bot: ## Start the interactive Telegram bot
	uv run python -m bot.telegram_bot

# ── Code Review ───────────────────────────────────────────────────────────────

review: ## AI code review (usage: make review [BRANCH=feat/x] [NOTIFY=1])
	uv run python -m agents.reviewer $(if $(BRANCH),--branch "$(BRANCH)",) $(if $(NOTIFY),--notify,)

# ── Orchestration ──────────────────────────────────────────────────────────────

orchestrate-start: ## Start orchestration session (TASK="..." [AGENT=copilot] [WORKTREE=1])
	uv run python -m agents.orchestrator start "$(TASK)" $(if $(AGENT),--agent "$(AGENT)",) $(if $(WORKTREE),--worktree,)

orchestrate-next: ## Advance to next phase [FAILED=1 if review failed]
	uv run python -m agents.orchestrator next $(if $(FAILED),--failed,)

orchestrate-block: ## Block session with reason (REASON="...")
	uv run python -m agents.orchestrator block "$(REASON)"

orchestrate-resume: ## Resume blocked/paused session
	uv run python -m agents.orchestrator resume

orchestrate-status: ## Show current orchestration state
	uv run python -m agents.orchestrator status

orchestrate-done: ## Mark session complete
	uv run python -m agents.orchestrator done

orchestrate-check-failed: ## Increment failed check counter (call after make check fails)
	uv run python -m agents.orchestrator check-failed

orchestrate-explain: ## Send Explanation from handoff.md to Telegram
	uv run python -m agents.orchestrator explain

onboard: ## Interactive new-project onboarding agent
	uv run python -m agents.onboarding

promote: ## Promote AI tooling into an existing repo (TARGET="../my-repo")
	uv run python -m agents.onboarding --promote-to "$(TARGET)"

workspace: ## Generate .code-workspace for multi-root Copilot+Claude indexing (TARGET="../my-repo")
	uv run python -m agents.onboarding --make-workspace "$(TARGET)"

template-clean: ## Reset repo to clean template state (strips example data)
	@echo "Cleaning example data..."
	find data/knowledge/raw/medium -name "*.md" -delete 2>/dev/null || true
	find data/knowledge/meta -name "*.json" -delete 2>/dev/null || true
	@echo '{"task":"","phase":"PLANNING","agent":"claude","iterations":0,"failed_checks":0,"uncertainty":false,"status":"ACTIVE","started_at":"","worktree":null,"history":[]}' > docs/orchestration/session.json
	@printf '## Task\n\n\n## Changed Files\n\n\n## Output\n\n(test results, key observations)\n\n## Explanation\n\n(plain English: what was changed, why, and how)\n\n## Uncertainty\n\nNone\n' > docs/orchestration/handoff.md
	@echo "" > docs/orchestration/human_input.md
	@echo "Template clean. Edit .env and run: make orchestrate-start TASK='your first task'"

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage dist/ build/ *.egg-info
