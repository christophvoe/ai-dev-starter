---
description: "Plan a feature or task before implementing — think through design, edge cases, and tradeoffs"
argument-hint: "Describe the feature or task to plan"
agent: "agent"
tools: [read, search]
---
Before writing any code, create a plan for: $ARGUMENTS

Your plan should include:

1. **Goal**: What this achieves in one sentence
2. **Approach**: How to implement it (files to change, new files needed)
3. **Edge Cases**: What could go wrong? (empty input, network errors, file conflicts, Windows vs Unix)
4. **Dependencies**: Any new packages needed? Any existing code to reuse?
5. **Testing**: What tests to write and what to mock
6. **Tradeoffs**: Alternative approaches considered and why this one is better

Do NOT write implementation code. Focus on the design. I will review the plan before we proceed.
