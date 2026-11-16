# Security Policy

## Supported versions

Only the latest `main` branch is supported with security updates.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

Instead, report them privately:

1. Go to the repo's **Security** tab → **Report a vulnerability**, or
2. DM the owner via **https://github.com/yansheng836**.

Please include:

- A clear description of the issue and its impact.
- Steps to reproduce (proof of concept if possible).
- Suggested fix, if any.

You should receive a response within 72 hours. Please allow reasonable time for
a fix before any public disclosure.

## Scope

This project is a static-site generator that reads public GitHub data and renders
a single HTML file. It does not handle authentication secrets beyond the read-only
`GITHUB_TOKEN` used to raise API rate limits. Vulnerabilities in that token's
handling, or any path that could expose a secret, are in scope.
