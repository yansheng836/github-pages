#!/usr/bin/env python3
"""Unit tests for generate_nav — stdlib unittest, no third-party deps.

Run with:  python -m unittest test_generate_nav
"""
import os
import unittest
from datetime import datetime, timezone, timedelta

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


class TestSorting(unittest.TestCase):
    def test_entries_sorted_by_updated_desc(self):
        entries = [
            {"name": "old", "description": "", "repo_url": "", "pages_url": "", "updated": "2024-01-01"},
            {"name": "new", "description": "", "repo_url": "", "pages_url": "", "updated": "2026-11-17"},
            {"name": "mid", "description": "", "repo_url": "", "pages_url": "", "updated": "2025-06-01"},
        ]
        ordered = sorted(entries, key=lambda e: e["updated"], reverse=True)
        self.assertEqual([e["name"] for e in ordered], ["new", "mid", "old"])


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

    def test_english_lang_switches_strings(self):
        os.environ["LANG"] = "en_US.UTF-8"
        html = gn.render("someone", [])
        self.assertIn("No public repos with GitHub Pages enabled yet.", html)
        self.assertIn('lang="en"', html)


if __name__ == "__main__":
    unittest.main()
