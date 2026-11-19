#!/usr/bin/env python3
"""Unit tests for generate_nav — stdlib unittest, no third-party deps.

Run with:  python -m unittest test_generate_nav
"""
import io
import os
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


if __name__ == "__main__":
    unittest.main()
