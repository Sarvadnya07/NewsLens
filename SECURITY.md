# Security Policy

## Supported Versions

Only the latest commit on the `master` branch is supported with active security updates.

| Version | Supported          |
| ------- | ------------------ |
| master  | :white_check_mark: |
| < 1.0.0 | :x:                |

## Reporting a Vulnerability

We take the security of NewsLens India seriously. If you identify a security issue, vulnerability, or secret exposure, please report it privately:

1. **Do NOT open a public GitHub issue.**
2. Send vulnerability details to: `sarvadnyasonkambale0@gmail.com`
3. Include:
   - Type of vulnerability (e.g. injection, rate-limiting bypass, secret leak, SSRF).
   - Detailed proof of concept (PoC) or steps to reproduce.
   - Potential impact and affected components.

## Security Practices in NewsLens India

- **Zero Stored Secrets:** NewsLens India queries public, unauthenticated RSS feeds and GDELT 2.0 endpoints. No API tokens or secrets belong in source files or repository history.
- **SQL Injection Prevention:** All SQLite queries use strictly parameterized `?` placeholders via `sqlite3`.
- **XSS Prevention:** Streamlit and custom component outputs sanitize user-controlled fields using `html.escape`.
- **Egress Throttling:** All GDELT queries enforce an explicit 5-second backoff throttle to prevent unintentional upstream denial of service.
