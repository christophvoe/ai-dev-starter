## Security Rules

These rules apply when handling secrets, external input, or security-sensitive code.

### Secrets Management
- All secrets in `.env` only, loaded via python-dotenv
- NEVER hardcode secrets, API keys, or tokens in source code
- NEVER log secrets or credentials (even at debug level)
- Treat MEDIUM_COOKIES as sensitive credentials
- See `.env.example` for the expected variables

### Input Validation
- Validate ALL external input: user arguments, API responses, scraped HTML
- Sanitize URLs before making HTTP requests
- Check HTTP status codes; handle 403/429 with appropriate backoff
- Never trust Content-Type headers blindly

### Dangerous Operations
- Never `eval()` or `exec()` on external data
- Never use `shell=True` in subprocess calls with user input
- Never construct SQL with string concatenation — use parameterized queries
- Never auto-install packages without explicit user review

### Dependencies
- Pin versions via uv.lock
- Audit dependencies before updating
- Prefer well-maintained packages with security track records

### File System
- Use `Path` methods for all file operations
- Validate paths to prevent directory traversal
- Handle encoding explicitly (UTF-8)
