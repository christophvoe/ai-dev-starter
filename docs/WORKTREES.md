# Parallel Agent Development with Git Worktrees

> Run multiple AI agents (Claude Code + Copilot) on the same repo simultaneously
> without file conflicts. Each gets its own working directory.

---

## Why Worktrees?

When two agents edit the same repo simultaneously, they collide on file writes.
Git worktrees solve this: each agent gets a **separate checkout** of the repo
that shares the same `.git` history. Changes merge cleanly through branches.

## Quick Setup

```bash
# From your main repo directory
cd c:\Users\Voelt\ai-dev-starter

# Create a worktree for a parallel agent on a new branch
git worktree add ../ai-dev-agent-2 -b feature/agent-2-task

# Create another for a third agent
git worktree add ../ai-dev-agent-3 -b feature/agent-3-task
```

This creates:
```
c:\Users\Voelt\
  ai-dev-starter/          ← Main repo (your primary agent works here)
  ai-dev-agent-2/          ← Worktree 1 (second agent works here)
  ai-dev-agent-3/          ← Worktree 2 (third agent works here)
```

## Workflow: Agent A Implements, Agent B Reviews

### Step 1: Agent A implements in worktree
```bash
# In ai-dev-agent-2/ (Claude Code terminal)
cd ../ai-dev-agent-2
# Agent A writes code on feature/agent-2-task branch
git add -A && git commit -m "feat(scraper): add new feature"
```

### Step 2: Agent B reviews from main
```bash
# In ai-dev-starter/ (Copilot or second Claude Code session)
git fetch
git diff main..feature/agent-2-task  # see what Agent A changed

# Or use @code-reviewer in Copilot Chat:
# "@code-reviewer review the changes on feature/agent-2-task"
```

### Step 3: Merge when approved
```bash
# From main repo
git merge feature/agent-2-task
```

## Cross-Tool Parallel Pattern

| Agent | Location | Tool | Task |
|-------|----------|------|------|
| Agent 1 | `ai-dev-starter/` | Copilot (VS Code) | Feature implementation |
| Agent 2 | `ai-dev-agent-2/` | Claude Code (terminal) | Independent feature |
| Reviewer | `ai-dev-starter/` | `@code-reviewer` | Reviews Agent 2's branch |

### Setup in VS Code
1. Open `ai-dev-starter/` as primary workspace
2. Open `ai-dev-agent-2/` in a **second VS Code window**
3. Each window has its own Copilot + Claude Code context

### Setup in Terminal (Claude Code)
```bash
# Terminal 1: Main agent
cd ai-dev-starter/

# Terminal 2: Parallel agent (separate terminal/pane)
cd ai-dev-agent-2/
```

## Managing Worktrees

```bash
# List all worktrees
git worktree list

# Remove a worktree when done
git worktree remove ../ai-dev-agent-2

# Prune stale worktree references
git worktree prune
```

## Best Practices

1. **One branch per worktree** — never share branches across worktrees
2. **Short-lived** — create for a task, merge, remove
3. **Independent work** — avoid editing the same files in parallel worktrees
4. **Commit often** — small commits make merges easier
5. **Review before merge** — use `@code-reviewer` or `/review` on the branch diff

## The Interplay

The real power is combining tools:

```
Copilot (VS Code)                    Claude Code (Terminal)
────────────────                     ──────────────────────
1. /plan feature X  
                                     2. /implement feature X
                                        (writes code + tests)
3. @code-reviewer review  
   feature/agent-2-task  
                                     4. Fixes review feedback
5. Merge to main  
```

This gives you:
- **Planning** in Copilot (visual, chat-based)
- **Implementation** in Claude Code (terminal, full access)
- **Review** back in Copilot (structured @code-reviewer agent)
- **Iteration** until quality gate passes
