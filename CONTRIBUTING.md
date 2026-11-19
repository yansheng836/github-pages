# Contributing to github-pages

Thanks for your interest in contributing! This is a small, focused project, so the
process is intentionally lightweight.

## Ways to contribute

- Report bugs or request features via [Issues](https://github.com/yansheng836/github-pages/issues).
- Improve the `generate_nav.py` script or the rendered `index.html` styles.
- Fix typos or translate the README into another language.
- Star the repo and share it with others who maintain multiple Pages sites.

## Development setup

```bash
git clone https://github.com/yansheng836/github-pages.git
cd github-pages
export GITHUB_TOKEN=$(gh auth token)   # optional, raises rate limit
OWNER=yansheng836 python generate_nav.py --out index.local.html
```

Open `index.local.html` in a browser to inspect your changes. Using `--out` keeps you from
accidentally overwriting the committed `index.html`, which the Action owns.

## Before opening a pull request

1. Keep changes **minimal and focused** — one concern per PR.
2. The script must remain **standard-library only** (no third-party dependencies).
3. Don't commit the regenerated `index.html` unless your change alters its output —
   the daily workflow commits it automatically.
4. Test locally: run `python generate_nav.py` and confirm it produces valid output.
5. Follow the existing code and commit style: `type: 中文描述` for commit messages
   (e.g. `feat: 支持按主题过滤`, `fix: 修正时区回退逻辑`).

## Pull request checklist

- [ ] PR title follows the commit style.
- [ ] No third-party dependencies introduced.
- [ ] `index.html` is not committed unless its rendered output changed.
- [ ] README updated if the user-facing behaviour changed.

## Reporting security issues

Please do **not** open a public issue for security problems. See
[SECURITY.md](SECURITY.md) for how to report privately.
