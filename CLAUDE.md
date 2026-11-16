# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo does

A single Python script scans a GitHub account's public repos, keeps the ones with GitHub Pages enabled, and renders a self-contained dark card-grid `index.html`. A daily GitHub Action regenerates and auto-commits it, and GitHub Pages serves it. The tool is meant to be forked by other users to generate their own nav page.

## Commands

```bash
# Run tests (stdlib unittest, no deps)
python -m unittest test_generate_nav -v

# Run a single test
python -m unittest test_generate_nav.TestEsc.test_none_becomes_empty -v

# Generate the nav page locally (writes index.html next to the script)
OWNER=yansheng836 python generate_nav.py

# With a token to raise the API rate limit
GITHUB_TOKEN=$(gh auth token) OWNER=yansheng836 python generate_nav.py
```

## Architecture

`generate_nav.py` is the entire product — one file, Python 3.12 stdlib only (no third-party deps ever; `requirements.txt` is intentionally empty). The flow:

1. Resolve owner from `OWNER` → `GITHUB_REPOSITORY_OWNER` → `GITHUB_REPOSITORY` env (in that order).
2. `list_public_repos` paginates `/users/{owner}/repos`.
3. For each repo, query `/repos/{full}/pages`; keep those returning 200.
4. Sort entries by `pushed_at` (desc) and render via `render()`.

The render layer is fully parameterised by the `STRINGS` dict + `strings()` helper, which picks zh-CN or English based on the `LANG` env var. Adding a language = add a dict entry; do not hardcode user-facing strings in `render`/`card_html`.

Timestamps render in `TIMEZONE` (IANA, default `Asia/Shanghai`) via `now_in_tz`, which falls back to a fixed offset if `zoneinfo` is unavailable.

## Auto-commit loop

`.github/workflows/update-nav.yml` runs daily (UTC 00:00), on every push to `main`, and on manual dispatch, regenerates `index.html`, and commits/pushes only if it changed. Therefore:

- **Do not commit `index.html` yourself** unless a code change alters its rendered output — the workflow owns it.
- The workflow commits as `github-actions[bot]`; when pulling, expect a `chore: 自动更新 Pages 导航` commit on the remote.

`test.yml` runs the unittest suite on push/PR to `main`.

## Conventions

- Commit messages: `type: 中文描述` where type ∈ feat/fix/docs/refactor/style/test/ci/chore.
- README is bilingual: `README.md` (English, primary) and `README.zh-CN.md`. Keep both in sync when changing user-facing docs.
- User-facing page strings must go through `STRINGS`, not be inlined.
