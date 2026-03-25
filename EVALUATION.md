# Evaluation: Claude Code & Agentic AI Best Practices

> Generated from 12 scraped Medium articles + official Claude Code docs (context7).
> Compares best practices against our current ai-dev-starter setup.

---

## 1. CLAUDE.md — The #1 Productivity Lever

### What the research says

Per Anthropic's own docs + Article 1 ("10 Game-Changing CLAUDE.md Entries"):
- Teams with well-tuned CLAUDE.md files achieve **2-3x faster execution**
- CLAUDE.md is auto-loaded into every session as persistent context
- Keep it **under 500 lines** (official docs); move reference material to skills/rules
- The `/init` command can bootstrap it, but manual refinement is essential
- **Hierarchical**: root `CLAUDE.md` + subdirectory `CLAUDE.md` files + `.claude/rules/` for topic-specific rules

### The 10 recommended sections (Article 1)

| # | Section | Purpose |
|---|---------|---------|
| 1 | **Architecture Blueprint** | 10,000-ft view: frameworks, layers, data flow |
| 2 | **Command Center** | All CLI commands (prevents scanning package.json) |
| 3 | **Style Guide** | Code style rules (formatting, naming, imports) |
| 4 | **Test Bench Coach** | Testing framework + TDD expectations |
| 5 | **Error Handling Mantra** | How to handle errors, debugging approach |
| 6 | **Clean Code Commandments** | Function size limits, DRY, naming |
| 7 | **Security Sentry** | Input validation, auth, XSS/CSRF prevention |
| 8 | **Teamwork Protocol** | Git conventions, branching, commit messages |
| 9 | **Edge-Case Oracle** | Enforce edge case thinking before coding |
| 10 | **Agentic Workflow Guardrails** | Plan -> Implement -> Verify -> Adjust pattern |

### Our current CLAUDE.md — Gap analysis

| Section | Status | Assessment |
|---------|--------|------------|
| Architecture Blueprint | **Complete** | File map + data flow + layer description |
| Command Center | **Complete** | All make commands documented |
| Style Guide | **Complete** | ruff rules, naming, imports, paths, secrets, async |
| Test Bench Coach | **Complete** | pytest framework, mocking, coverage |
| Error Handling | **Complete** | Boundary validation, specific exceptions, logging |
| Clean Code Rules | **Complete** | Function size limits, DRY, SRP, naming |
| Security Sentry | **Complete** | .env secrets, input validation, dependency pinning |
| Teamwork Protocol | **Complete** | Git conventions, commit format, pre-commit hooks |
| Edge-Case Oracle | **Complete** | Pre-implementation edge case checklist |
| Agentic Guardrails | **Complete** | Plan->Implement->Verify->Adjust + context management |

**Score: 10/10 sections present. CLAUDE.md fully upgraded.**

### Official docs additions (from context7)

- Use `@README` and `@package.json` imports in CLAUDE.md for references
- Use `.claude/rules/` directory for topic-specific rules (code-style.md, testing.md, security.md)
- Subdirectory CLAUDE.md files are loaded on-demand when Claude touches those files
- `/init` command (with `CLAUDE_CODE_NEW_INIT=true`) does interactive multi-phase setup

---

## 2. Context Window Management — The Silent Killer

### What the research says (Article 2)

- **Lost-in-the-middle effect**: Models over-prioritize start/end content, bury middle details
- Stay under **70-80%** of token limit; reset or compact regularly
- Each MCP server consumes significant context (tool definitions, metadata)
- Can eat **1/3 of your entire context window** before you start coding

### Critical commands

| Command | When to use |
|---------|------------|
| `context` | Check current token usage |
| `clear` | Wipe conversation (new task, or >75% full) |
| `compact` | Summarize + free space (70k -> 4k tokens) |

### Our current setup — Assessment

| Item | Status | Risk |
|------|--------|------|
| 4 MCP servers configured | Acceptable | Sequential-thinking + context7 + filesystem + github is a reasonable set |
| No MCP audit guidance | Gap | Should document which MCPs to disable for heavy sessions |
| No context management reminders | Gap | CLAUDE.md should include "compact at 70%" rule |

**Recommendation**: Add context management section to CLAUDE.md. Our 4 MCPs are a lean set (Article 11 validates sequential-thinking + git as essential).

---

## 3. Dual-Model / Multi-Agent Workflows

### What the research says (Articles 6, 7, 8, 9)

**Three proven patterns:**

**Pattern A: Cursor + Claude Code (Article 6)**
- Cursor = IDE for code generation, architecture, background agents
- Claude Code = terminal for infrastructure, DevOps, migrations
- Morning: review overnight Cursor background agents
- Afternoon: deep implementation with Claude Code
- Evening: queue night shift agents

**Pattern B: Claude + Codex side-by-side (Articles 8, 9)**
- Claude = architect (planning, systems thinking, tradeoffs)
- Codex = builder (implementation, surgical fixes)
- You = tech lead orchestrating
- Workflow: Plan (Claude) -> Validate (Codex) -> Implement -> Cross-review
- Result: 70-80% faster delivery

**Pattern C: Parallel Claude Code agents with Git Worktrees (Article 7)**
- Multiple agents on same repo = collision problems
- Solution: each agent gets separate Git worktree
- Up to 5 agents in parallel on same repo
- Warp terminal with split panes for visibility

### Our current setup — Assessment

Currently single-agent, single-tool (Copilot in VS Code). No multi-agent patterns configured.

**Recommendation**:
- Start with Pattern A (Copilot/Cursor for IDE + Claude Code for terminal)
- For parallel work, learn git worktrees
- For critical features, try dual-model review (Claude plans, Codex validates)

---

## 4. Slash Commands & Reusable Prompts

### What the research says (Articles 6, 7 + official docs)

- Store frequently-used prompts as `.md` files
- **Two benefits**: Save time + enforce consistency
- Claude Code: `.claude/commands/` directory
- Copilot: `.github/copilot-instructions.md` (we already have this)

### Recommended slash commands (from articles + docs)

| Command | Purpose |
|---------|---------|
| `/review` | Code review for quality + security |
| `/document` | Generate docs for a file |
| `/plan` | Plan a feature before implementing |
| `/test` | Generate tests for current code |
| `/deploy` | Deploy checklist |
| `/pr` | Create PR with latest dev, rebase, precommit |

### Our current setup — Assessment ✅ COMPLETE

- `.claude/commands/` created with: review.md, plan.md, test.md
- `.github/prompts/` created with: review.prompt.md, plan.prompt.md, test.prompt.md
- Both tools have matching slash commands for the same workflows

---

## 5. Agent Configuration & Subagents

### What the research says (official docs + Articles 3, 4)

**Claude Code supports custom agents** via `.claude/agents/agent-name.md`:
```yaml
---
name: code-reviewer
description: Use this agent when code changes need quality review
model: inherit
color: blue
tools: ["Read", "Grep", "Glob"]
---
System prompt here...
```

**Subagent orchestration** (from official docs):
- Use subagents for parallel or isolated tasks
- Don't over-delegate simple operations
- Best for: code review, test running, security scanning in parallel

**Agent memory** (Article 3 - HINDSIGHT):
- Future direction: 4-layer memory (world, experience, opinion, observation)
- Current practical approach: CLAUDE.md + `.claude/rules/` for persistent memory

**Reasoning strategies** (Article 4):
- Chain-of-Thought: best average accuracy (87%)
- Self-Consistency: when correctness is critical
- Tree of Thoughts: multi-step planning
- ReAct: tool-augmented reasoning

### Our current setup — Assessment ✅ COMPLETE

- `.github/agents/code-reviewer.agent.md` — Code review specialist (tools: read, search)
- `.github/agents/planner.agent.md` — Architecture planner, read-only (tools: read, search)
- Claude Code subagents configured via CLAUDE.md agentic workflow section

---

## 6. Security in Agentic Workflows

### What the research says (Article 10 - LiteLLM attack)

**The LiteLLM catastrophe** (March 2025):
- Poisoned PyPI package exfiltrated ALL credentials (SSH, AWS, API keys, DB passwords)
- `.pth` file auto-executed on every Python process start
- 10,000s of installs in 3 hours before PyPI quarantine
- Affected tools with LiteLLM as transitive dependency (Cursor, DSPy)

**Critical lessons:**
1. **Never** let agents run unapproved `pip install` commands
2. **Always** sandbox agent work
3. **Pin** exact dependency versions + lockfile
4. **Audit** transitive dependencies regularly
5. **Rotate** credentials after any agent-driven dependency updates
6. Agents auto-installing packages = "apocalypse scenario"

### Our current setup — Assessment

| Item | Status | Grade |
|------|--------|-------|
| uv.lock (pinned deps) | **Good** | A |
| .env for secrets (not hardcoded) | **Good** | A |
| pre-commit hooks | **Good** | A |
| No agent auto-install policy | Gap | Needs documentation |
| No dependency audit routine | Gap | Should add to workflow |

**Recommendation**: Add security section to CLAUDE.md. Document that agents must NEVER auto-install packages without review.

---

## 7. MCP Server Strategy

### What the research says (Articles 2, 11, 12)

**Essential MCP servers** (validated across articles):
- **Sequential Thinking**: Complex problem solving, planning (highest rated)
- **Git/GitHub**: Version control automation, PR management
- **Context7**: Live library documentation

**Good to have:**
- **Sentry**: Error tracking (if using Sentry)
- **Puppeteer**: Browser automation
- **Firebase**: If using Firebase

**Critical rule**: Don't enable all servers. Each one consumes context tokens.

### Our current setup — Assessment

| MCP Server | Status | Verdict |
|------------|--------|---------|
| filesystem | Enabled | Essential - keep |
| sequential-thinking | Enabled | Essential - keep |
| context7 | Enabled | Essential - keep |
| github | Enabled | Essential - keep |

**Score: Optimal.** We have exactly the 4 most valuable servers. No bloat.

---

## 8. The Simplicity Principle

### What the research says (Articles 5, 12)

**Article 12** (PowerPoint case study):
- When tools remove constraints, systems naturally accumulate complexity
- Great engineering requires **restraint**
- "More matter with less art" — Robert Gaskins

**Article 5** (15KB trading system):
- Simple pattern-matching system (15KB) beat 500MB neural networks
- Simpler, constraint-aware systems often outperform complex ones

**Application to our setup:**
- Lean CLAUDE.md (specific guidance, not everything)
- Minimal necessary MCP servers (not all available)
- Clear architecture boundaries
- Simple systems beat complex ones when both work

### Our current setup — Assessment

**Good**: We've been following this principle:
- Makefile instead of complex build system
- Plain HTTP scraper instead of AI-powered extraction
- Direct CLI commands instead of wrapper layers
- 4 MCP servers, not 10

**Risk area**: n8n adds complexity for what `make scrape` already does. But we've correctly positioned it as the "visual config" layer for switching output directories.

---

## 9. Claude Code + GitHub Copilot Interplay Architecture

### Design Principle

Both tools cover the **same project knowledge**, optimized for each tool's strengths:
- **CLAUDE.md** is richer (Claude Code handles longer context, auto-loads at session start)
- **copilot-instructions.md** is leaner (Copilot loads it on every chat request)
- **Topic rules** live in parallel directories with identical knowledge, different formats
- **Slash commands** mirror each other so the same workflows are available in both tools

### File Map — Who Reads What

| Purpose | GitHub Copilot | Claude Code |
|---------|---------------|-------------|
| Always-on instructions | `.github/copilot-instructions.md` | `CLAUDE.md` |
| Python code style rules | `.github/instructions/python.instructions.md` | `.claude/rules/code-style.md` |
| Testing conventions | `.github/instructions/testing.instructions.md` | `.claude/rules/testing.md` |
| Security requirements | `.github/instructions/security.instructions.md` | `.claude/rules/security.md` |
| Code review command | `.github/prompts/review.prompt.md` | `.claude/commands/review.md` |
| Planning command | `.github/prompts/plan.prompt.md` | `.claude/commands/plan.md` |
| Test generation command | `.github/prompts/test.prompt.md` | `.claude/commands/test.md` |
| Code reviewer agent | `.github/agents/code-reviewer.agent.md` | (subagent via CLAUDE.md) |
| Planner agent | `.github/agents/planner.agent.md` | (subagent via CLAUDE.md) |
| MCP server config | `.vscode/mcp.json` | `.mcp.json` |
| Shared config | `pyproject.toml`, `.vscode/settings.json` | `pyproject.toml`, `.vscode/settings.json` |

### Workflow: When to Use Which Tool

| Task | Best Tool | Why |
|------|-----------|-----|
| Quick inline completions | **Copilot** | Tab-completion is instant |
| Chat about current file | **Copilot** | File context is pre-loaded |
| Multi-file refactors | **Claude Code** | Better at holding large context |
| Planning & architecture | **Either** | Both have `/plan` command |
| Code review | **Either** | Both have `/review` command |
| Terminal/CLI tasks | **Claude Code** | Direct terminal access |
| Git operations | **Claude Code** | MCP github server integration |
| Library docs lookup | **Either** | Both have context7 MCP |
| Test generation | **Either** | Both have `/test` command |

### Key Insight

The setup ensures **zero lock-in**: switching between Claude Code and Copilot is seamless because both share the same project knowledge, conventions, and slash commands. The developer's workflow stays the same regardless of which tool is active.

---

## Summary Scorecard

| Category | Score | Target | Status |
|----------|:---:|:---:|:---:|
| CLAUDE.md completeness | 10/10 | 10/10 | **Done** |
| copilot-instructions.md | Complete | Complete | **Done** |
| Context management awareness | High | High | **Done** |
| MCP server strategy | Optimal | Optimal | **Done** |
| Security posture | Excellent | Excellent | **Done** |
| Slash commands (Copilot) | 3/3 | 3 | **Done** |
| Slash commands (Claude Code) | 3/3 | 3 | **Done** |
| Custom agents (Copilot) | 2/2 | 2 | **Done** |
| Topic rules (Copilot) | 3/3 | 3 | **Done** |
| Topic rules (Claude Code) | 3/3 | 3 | **Done** |
| Claude + Copilot interplay | Full | Full | **Done** |
| Simplicity discipline | Good | Good | **Maintained** |

---

## Action Plan

### Phase 1: Foundation — COMPLETED
1. ~~Upgrade CLAUDE.md with all 10 recommended sections~~
2. ~~Add context management rules to CLAUDE.md~~
3. ~~Add security guidelines to CLAUDE.md~~

### Phase 2: Automation — COMPLETED
4. ~~Create `.claude/commands/` (review, plan, test)~~
5. ~~Create `.claude/rules/` (code-style, testing, security)~~
6. ~~Create `.github/prompts/` (review, plan, test)~~
7. ~~Create `.github/instructions/` (python, testing, security)~~
8. ~~Create `.github/agents/` (code-reviewer, planner)~~
9. ~~Upgrade `.github/copilot-instructions.md`~~

### Phase 3: Advanced — READY
10. Document multi-agent workflow with git worktrees (when needed)
11. Set up dual-model review loop for critical features (when needed)
12. Add more slash commands as workflows emerge

---

## Key Quotes from Research

> "Teams with well-tuned CLAUDE.md files achieve 2-3x faster execution on tasks" — Anthropic

> "Context window management is the #1 skill separating 10x developers from those getting poor results" — Article 2

> "Each MCP server can consume 1/3 of your entire context window before you start coding" — Article 2

> "When tools remove constraints, systems naturally accumulate complexity. Great engineering requires restraint." — Article 12

> "Agents running pip install with no human review = apocalypse scenario" — Article 10

> "Keep CLAUDE.md under 500 lines. Move reference material to skills, which load on-demand." — Official Claude Code docs
