"""Regressions for Common Data Set C10 extraction."""

import unittest

import cds_c10


class C10ExtractionRegressionTests(unittest.TestCase):
    def test_bare_docx_values_regression(self):
        block = """C10. Percent in top tenth of high school graduating class95
Percent in top quarter of high school graduating class99
Percent in top half of high school graduating class100
Percent in bottom half of high school graduating class0
Percent in bottom quarter of high school graduating class0
Percent of total first-time, first-year students who submitted high school class rank: 39
C11 GPA distribution
"""
        values = {
            key: cds_c10.percentage_after_label(block, labels)
            for key, labels in cds_c10.RANK_LABELS.items()
        }
        self.assertEqual(values["top_10_pct"], 95)
        self.assertEqual(values["bottom_50_pct"], 0)
        self.assertEqual(cds_c10.reporting_percentage(block), 39)

    def test_omitted_zero_bins_regression(self):
        values = cds_c10.complete_rank_values({
            "top_10_pct": 99,
            "top_25_pct": 100,
            "top_50_pct": None,
            "bottom_50_pct": None,
            "bottom_25_pct": None,
        })
        self.assertEqual(values["top_50_pct"], 100)
        self.assertEqual(values["bottom_50_pct"], 0)
        self.assertEqual(values["bottom_25_pct"], 0)

    def test_broken_pdf_ligatures_regression(self):
        text = "first- me students; gradua ng class; bo om half; submi ed rank"
        self.assertEqual(
            cds_c10.normalize_extracted_text(text),
            "first-time students; graduating class; bottom half; submitted rank",
        )

    def test_wrapped_c10_heading_regression(self):
        text = """C10 Percent of all degree-seeking, first-time, first-year students
who had high school class rank within each of the following ranges.
C10 Percent in top tenth of high school graduating class 31.7%
C10 Percent in top quarter of high school graduating class 66.5%
C10 Percent in top half of high school graduating class 95.1%
C10 Percent in bottom half of high school graduating class 4.9%
C10 Percent in bottom quarter of high school graduating class 0.6%
C11 GPA distribution
"""
        block = cds_c10.c10_block(text)
        values = {
            key: cds_c10.percentage_after_label(block, labels)
            for key, labels in cds_c10.RANK_LABELS.items()
        }
        self.assertEqual(values, {
            "top_10_pct": 31.7,
            "top_25_pct": 66.5,
            "top_50_pct": 95.1,
            "bottom_50_pct": 4.9,
            "bottom_25_pct": 0.6,
        })


if __name__ == "__main__":
    unittest.main()
