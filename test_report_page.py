#!/usr/bin/env python3
"""Regression checks for bugs found in the test-evidence page."""

import re
import unittest

import viz_test_evidence as viz

TEMPLATE = viz.TEMPLATE.read_text(encoding="utf-8")


def css_rule(selector):
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", TEMPLATE)
    return match.group(1) if match else ""


def js_statement(name):
    match = re.search(re.escape(name) + r"[^;]*;", TEMPLATE)
    return match.group(0) if match else ""


class ReportPageTests(unittest.TestCase):
    def test_renamed_series_is_caught(self):
        """Renaming a series left DATA.annual behind and every chart came up empty."""
        with self.assertRaises(ValueError):
            viz.render({"hundred": []}, "const DATA = __DATA__; DATA.annual.map();")

    def test_chart_box_does_not_clip_the_tooltip(self):
        """overflow-x on .chart made overflow-y compute to auto, hiding every tooltip."""
        self.assertNotIn("overflow", css_rule(".chart"))
        self.assertIn("position: relative", css_rule(".chart"))

    def test_tooltip_places_both_axes_in_pixels(self):
        """The tooltip read top straight from viewBox units while left was scaled."""
        for axis in ("left", "top"):
            self.assertIn("scale", js_statement(f"tip.style.{axis} ="))


if __name__ == "__main__":
    unittest.main()
