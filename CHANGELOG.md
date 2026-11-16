# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Bilingual README (English `README.md` + `README.zh-CN.md`).
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`.
- Issue templates (bug report, feature request) and pull request template.
- Preview screenshot in `docs/screenshot.png`.
- CI/license/Python/stars badges in the README.
- `test_generate_nav.py` covering `esc()`, `now_in_tz()`, and entry sorting.
- Bilingual generated page: `LANG=en` switches the rendered `index.html` UI to English.

## [1.1.0] - 2026-11-17

### Added
- Configurable timezone for the "updated at" stamp via `TIMEZONE` env var (defaults to `Asia/Shanghai`).
- Account avatar injected as site favicon and apple-touch-icon.

## [1.0.0] - 2026-11-16

### Added
- Initial release: scans a GitHub account's public repos, keeps those with Pages enabled,
  renders a responsive dark card-grid `index.html`, and auto-publishes via a daily
  GitHub Action.
