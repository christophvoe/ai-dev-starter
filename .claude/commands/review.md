Review the code for quality, security, and compliance with project standards.

Focus areas:
1. **Code Quality**: Readability, DRY violations, functions over 50 lines, descriptive naming
2. **Security**: Hardcoded secrets, unsafe eval/exec, unvalidated external input, OWASP top 10
3. **Error Handling**: Bare except: blocks, swallowed exceptions, missing boundary validation
4. **Type Safety**: Missing type hints on public APIs, mypy compatibility
5. **Project Standards**: ruff (line-length 100), absolute imports from src/, double quotes, snake_case

For each issue found:
- State the file and line
- Classify as critical / major / minor
- Provide the specific fix

End with: 1 sentence overall assessment + the single highest-priority fix.

If $ARGUMENTS is provided, focus the review on: $ARGUMENTS
Otherwise, review the most recently changed files (use `git diff --name-only HEAD~1`).
