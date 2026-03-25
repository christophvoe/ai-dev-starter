---
description: "Use when working with security-sensitive code: .env files, API keys, cookies, authentication, user input validation, dependency management."
---
# Security Guidelines

- Secrets in `.env` only — loaded via python-dotenv. NEVER in code or logs.
- Validate ALL external input (user arguments, API responses, scraped HTML)
- Never `eval()` or `exec()` on external data
- Pin dependency versions via uv.lock. Audit before updating.
- Never let agents auto-install packages without human review
- Cookie handling: Treat MEDIUM_COOKIES as sensitive credentials
- Use parameterized queries for any database operations
- Check for OWASP Top 10 vulnerabilities in any web-facing code
