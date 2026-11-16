# github-pages

自动收集账号下所有启用了 GitHub Pages 的公开仓库，生成一个导航页面。

## 站点

- 导航页：<https://yansheng836.github.io/github-pages/>
- 仓库：<https://github.com/yansheng836/github-pages>

## 工作原理

1. `generate_nav.py` 通过 GitHub API 列出账号下的公开仓库
2. 逐个检查 `/repos/{owner}/{repo}/pages`，筛出启用了 Pages 的
3. 收集仓库名、描述、仓库链接、Pages 站点链接、最近更新时间
4. 生成卡片网格状的 `index.html`，按最近更新时间排序

GitHub Action 每天定时跑一次，自动提交并推送新的 `index.html`，
Pages 随之更新。

## 维护仓库信息

导航页显示的「描述」直接取自 GitHub 仓库的 description 字段。
要修改某个仓库在导航页上的描述，去该仓库的 **Settings → About**
改描述即可，下次 Action 运行后自动同步。

## 手动触发更新

在仓库的 **Actions** 页选择「更新 Pages 导航」工作流，点击 **Run workflow** 即可立即重新生成。

## 项目结构

```text
github-pages/
├── generate_nav.py                # 扫描并生成导航的脚本
├── index.html                     # 脚本生成的导航页（自动提交）
├── .github/
│   ├── workflows/
│   │   └── update-nav.yml         # 定时更新工作流
│   └── dependabot.yml             # 自动升级 action 版本
└── LICENSE
```

## 本地运行

```bash
# 设置环境变量（可选，提供后可提高 API 速率限制）
export GITHUB_TOKEN=$(gh auth token)

# 运行脚本，生成 index.html
python generate_nav.py
```

脚本会读取 `GITHUB_REPOSITORY_OWNER` 或 `OWNER` 环境变量确定扫描的账号；本地运行时可手动指定：

```bash
OWNER=yansheng836 python generate_nav.py
```

## 技术栈

- Python 3.12（仅标准库，无第三方依赖）
- GitHub Actions（定时 + 手动触发）
- GitHub Pages（静态托管）

## 许可证

[MIT](LICENSE)
