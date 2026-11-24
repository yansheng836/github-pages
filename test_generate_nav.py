#!/usr/bin/env python3
"""Unit tests for generate_nav — stdlib unittest, no third-party deps.

Run with:  python -m unittest test_generate_nav
"""
import io
import os
import tempfile
import unittest
import urllib.error
from datetime import timedelta
from unittest import mock

import generate_nav as gn


class TestEsc(unittest.TestCase):
    def test_none_becomes_empty(self):
        self.assertEqual(gn.esc(None), "")

    def test_html_special_chars_are_escaped(self):
        self.assertEqual(gn.esc("<script>x</script>"), "&lt;script&gt;x&lt;/script&gt;")

    def test_quotes_escaped(self):
        self.assertEqual(gn.esc('"hello"'), "&quot;hello&quot;")


class TestNowInTz(unittest.TestCase):
    def test_valid_iana_zone(self):
        dt = gn.now_in_tz("UTC")
        # UTC offset should be zero
        self.assertEqual(dt.utcoffset(), timedelta(0))

    def test_fallback_offset_when_zoneinfo_missing(self):
        # Shanghai fallback path returns a +8 offset datetime
        dt = gn.now_in_tz("Asia/Shanghai")
        self.assertEqual(dt.utcoffset(), timedelta(hours=8))


class TestFallbackOffset(unittest.TestCase):
    def test_known_zone_uses_real_offset(self):
        self.assertEqual(gn.fixed_offset("America/New_York"), timedelta(hours=-5))

    def test_unknown_zone_falls_back_to_utc(self):
        self.assertEqual(gn.fixed_offset("Not/AZone"), timedelta(0))

    def test_missing_tzdata_does_not_silently_use_utc(self):
        # 模拟 tzdata 缺失：ZoneInfo 抛异常时仍应得到正确的 +8，而不是 0
        with mock.patch.object(gn, "ZoneInfo", side_effect=gn.ZoneInfoNotFoundError("no tzdata")):
            dt = gn.now_in_tz("Asia/Shanghai")
        self.assertEqual(dt.utcoffset(), timedelta(hours=8))

    def test_now_in_tz_explicit_offset_zone(self):
        dt = gn.now_in_tz("Etc/GMT-9")
        self.assertEqual(dt.utcoffset(), timedelta(hours=9))


class TestSorting(unittest.TestCase):
    def test_entries_sorted_by_updated_desc(self):
        entries = [
            {"name": "old", "description": "", "repo_url": "", "pages_url": "", "updated": "2024-01-01"},
            {"name": "new", "description": "", "repo_url": "", "pages_url": "", "updated": "2026-11-17"},
            {"name": "mid", "description": "", "repo_url": "", "pages_url": "", "updated": "2025-06-01"},
        ]
        ordered = gn.sort_entries(entries)
        self.assertEqual([e["name"] for e in ordered], ["new", "mid", "old"])

    def test_entries_without_date_sort_last(self):
        entries = [
            {"name": "none", "description": "", "repo_url": "", "pages_url": "", "updated": ""},
            {"name": "dated", "description": "", "repo_url": "", "pages_url": "", "updated": "2024-01-01"},
        ]
        self.assertEqual([e["name"] for e in gn.sort_entries(entries)], ["dated", "none"])


class TestApiErrors(unittest.TestCase):
    def test_http_error_raises_api_error(self):
        err = urllib.error.HTTPError(
            "https://api.github.com/x", 429, "rate limited", {}, io.BytesIO(b"{}")
        )
        with mock.patch.object(gn.urllib.request, "urlopen", side_effect=err), \
                self.assertRaises(gn.ApiError) as ctx:
            gn.api_get("/x")
        self.assertEqual(ctx.exception.status, 429)

    def test_list_public_repos_propagates_first_page_failure(self):
        err = urllib.error.HTTPError(
            "https://api.github.com/users/o/repos", 500, "boom", {}, io.BytesIO(b"{}")
        )
        with mock.patch.object(gn.urllib.request, "urlopen", side_effect=err), \
                self.assertRaises(gn.ApiError):
            gn.list_public_repos("o", None)

    def test_pagination_stops_at_max_pages(self):
        full_page = [{"name": f"r{i}"} for i in range(100)]
        with mock.patch.object(gn, "MAX_PAGES", 3), \
                mock.patch.object(gn, "api_get", return_value=(200, full_page)) as get:
            repos = gn.list_public_repos("o", None)
        self.assertEqual(get.call_count, 3)
        self.assertEqual(len(repos), 300)

    def test_collect_entries_reports_truncated_pagination(self):
        page = [{"name": f"r{i}", "full_name": f"o/r{i}"} for i in range(100)]
        with mock.patch.object(gn, "MAX_PAGES", 2), \
                mock.patch.object(gn, "api_get", return_value=(200, page)):
            repos = gn.list_public_repos("o", None)
        self.assertEqual(len(repos), 200)
        with mock.patch.object(gn, "MAX_PAGES", 2), \
                mock.patch.object(gn, "list_public_repos", return_value=repos), \
                mock.patch.object(gn, "api_get", return_value=(404, None)):
            _, failed = gn.collect_entries("o", None)
        self.assertTrue(any("上限" in f for f in failed))

    def test_pages_check_errors_are_skipped_not_dropped(self):
        repos = [
            {"name": "ok", "full_name": "o/ok", "html_url": "u", "pushed_at": "2026-01-01"},
            {"name": "flaky", "full_name": "o/flaky", "html_url": "u", "pushed_at": "2026-01-02"},
        ]
        responses = {
            "/users/o": (200, {"avatar_url": "a"}),
            "/users/o/repos": (200, repos),
            "/repos/o/ok/pages": (200, {"html_url": "https://o.github.io/ok/"}),
        }

        def fake_get(path, token=None):
            if path.startswith("/users/o/repos"):
                return responses["/users/o/repos"]
            if path in responses:
                return responses[path]
            raise gn.ApiError(502, path)

        with mock.patch.object(gn, "api_get", side_effect=fake_get):
            entries, failed = gn.collect_entries("o", None)
        self.assertEqual([e["name"] for e in entries], ["ok"])
        self.assertEqual(failed, ["o/flaky"])

    def test_card_fields_are_collected(self):
        repos = [{
            "name": "ok", "full_name": "o/ok", "html_url": "https://github.com/o/ok",
            "pushed_at": "2026-01-02T00:00:00Z", "created_at": "2020-05-06T00:00:00Z",
        }]
        langs = {"Python": 8000, "HTML": 1000, "CSS": 500, "Shell": 100, "Dockerfile": 10}

        def fake_get(path, token=None):
            if path.startswith("/users/o/repos"):
                return 200, repos
            if path == "/repos/o/ok/pages":
                return 200, {"html_url": "https://o.github.io/ok/"}
            if path == "/repos/o/ok/languages":
                return 200, langs
            raise gn.ApiError(502, path)

        with mock.patch.object(gn, "api_get", side_effect=fake_get):
            entries, failed = gn.collect_entries("o", None)
        self.assertEqual(failed, [])
        self.assertEqual(entries[0]["created"], "2020-05-06")
        self.assertEqual(entries[0]["languages"], ["Python", "HTML", "CSS"])

    def test_languages_error_is_tolerated(self):
        repos = [{"name": "ok", "full_name": "o/ok", "html_url": "u", "pushed_at": "2026-01-02"}]

        def fake_get(path, token=None):
            if path.startswith("/users/o/repos"):
                return 200, repos
            if path == "/repos/o/ok/pages":
                return 200, {"html_url": "https://o.github.io/ok/"}
            raise gn.ApiError(502, path)

        with mock.patch.object(gn, "api_get", side_effect=fake_get):
            entries, failed = gn.collect_entries("o", None)
        self.assertEqual(entries[0]["languages"], [])
        self.assertEqual(failed, [])


class TestTopLanguages(unittest.TestCase):
    def test_sorted_by_bytes_desc_and_capped(self):
        langs = {"Python": 10, "HTML": 500, "CSS": 30, "Shell": 1, "Go": 99}
        self.assertEqual(gn.top_languages(langs), ["HTML", "Go", "CSS"])

    def test_empty_or_missing_data(self):
        self.assertEqual(gn.top_languages({}), [])
        self.assertEqual(gn.top_languages(None), [])

    def test_zero_byte_languages_ignored(self):
        self.assertEqual(gn.top_languages({"Python": 0, "HTML": 5}), ["HTML"])


class TestRender(unittest.TestCase):
    def setUp(self):
        self._orig_lang = os.environ.get("LANG")
        os.environ["LANG"] = "zh-CN"

    def tearDown(self):
        if self._orig_lang is None:
            os.environ.pop("LANG", None)
        else:
            os.environ["LANG"] = self._orig_lang

    def test_empty_entries_renders_empty_state(self):
        html = gn.render("someone", [])
        self.assertIn("暂未发现启用了 GitHub Pages 的公开仓库", html)
        self.assertIn("someone", html)

    def test_entry_appears_in_render(self):
        entries = [{"name": "myrepo", "description": "a demo", "repo_url": "https://example.com",
                    "pages_url": "https://example.com/io", "updated": "2026-11-17"}]
        html = gn.render("someone", entries)
        self.assertIn("myrepo", html)
        self.assertIn("a demo", html)

    def test_long_description_is_truncated(self):
        entries = [{"name": "r", "description": "x" * 500, "repo_url": "", "pages_url": "", "updated": ""}]
        html = gn.render("someone", entries)
        self.assertNotIn("x" * (gn.DESC_LIMIT + 1), html)
        self.assertIn("…", html)

    def test_multiline_description_is_flattened(self):
        entries = [{"name": "r", "description": "line1\nline2\r\nline3", "repo_url": "", "pages_url": "", "updated": ""}]
        html = gn.render("someone", entries)
        self.assertIn("line1 line2 line3", html)

    def test_english_lang_switches_strings(self):
        os.environ["LANG"] = "en_US.UTF-8"
        html = gn.render("someone", [])
        self.assertIn("No public repos with GitHub Pages enabled yet.", html)
        self.assertIn('lang="en"', html)

    def test_card_shows_page_created_and_languages(self):
        entries = [{
            "name": "r", "description": "d", "repo_url": "https://github.com/o/r",
            "pages_url": "https://o.github.io/r/", "updated": "2026-11-17",
            "created": "2020-05-06", "languages": ["Python", "HTML", "CSS"],
        }]
        html = gn.render("someone", entries)
        self.assertIn("Page：", html)
        self.assertIn('href="https://o.github.io/r/"', html)
        self.assertIn(">o.github.io/r/</a>", html)
        self.assertIn("创建：2020-05-06", html)
        self.assertIn("语言：Python · HTML · CSS", html)

    def test_card_placeholders_for_missing_fields(self):
        entries = [{"name": "r", "description": "d", "repo_url": "", "pages_url": "",
                    "updated": "", "created": "", "languages": []}]
        html = gn.render("someone", entries)
        self.assertIn("创建：" + gn.STRINGS["zh-CN"]["unknown"], html)
        self.assertIn("语言：" + gn.STRINGS["zh-CN"]["no_lang"], html)

    def test_card_field_order(self):
        s = gn.STRINGS["zh-CN"]
        entries = [{"name": "r", "description": "d", "repo_url": "https://github.com/o/r",
                    "pages_url": "https://o.github.io/r/", "updated": "2026-11-17",
                    "created": "2020-05-06", "languages": ["Python"]}]
        html = gn.render("someone", entries)
        labels = [s["repo_label"], s["page_label"], s["langs_label"], s["created_label"], s["updated_label"]]
        positions = [html.index(lbl) for lbl in labels]
        self.assertEqual(positions, sorted(positions))

    def test_card_urls_shown_without_protocol(self):
        entries = [{"name": "r", "description": "d", "repo_url": "https://github.com/o/r",
                    "pages_url": "https://o.github.io/r/", "updated": "2026-11-17",
                    "created": "2020-05-06", "languages": ["Python"]}]
        html = gn.render("someone", entries)
        self.assertIn(">github.com/o/r</a>", html)
        self.assertIn(">o.github.io/r/</a>", html)
        self.assertNotIn(">https://", html)

    def test_card_accepts_entry_without_new_keys(self):
        entries = [{"name": "r", "description": "d", "repo_url": "", "pages_url": "https://x/", "updated": ""}]
        self.assertIn("语言：", gn.render("someone", entries))


class TestMainOutput(unittest.TestCase):
    def _run(self, argv, out):
        env = {"OWNER": "someone"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(gn, "api_get", return_value=(200, {"avatar_url": "a"})), \
                mock.patch.object(gn, "collect_entries", return_value=([], [])):
            gn.main(argv)
        return out

    def test_out_flag_writes_to_given_path(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nav.html")
            self._run(["--out", path], path)
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as f:
                self.assertIn('lang="zh-CN"', f.read())

    def test_unknown_argument_exits_with_usage(self):
        with mock.patch.dict(os.environ, {"OWNER": "someone"}, clear=True), \
                self.assertRaises(SystemExit) as ctx:
            gn.main(["--bogus"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
