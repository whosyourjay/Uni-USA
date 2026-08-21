"""Regressions for school matching and sample selection."""

import unittest

import class_rank


class ClassRankRegressionTests(unittest.TestCase):
    def test_wrong_repository_document_regression(self):
        text = "Name of College/University: St. Olaf College, Northfield MN"
        self.assertFalse(
            class_rank.document_identity_matches("Stanford University", text)
        )
        self.assertTrue(class_rank.document_identity_matches(
            "Stanford University", "Name of College/University: Stanford University"
        ))

    def test_top_sample_iterator_regression(self):
        rows = (
            {
                "school": str(index),
                "freshman_score": str(index),
                "ability": str(30 - index),
            }
            for index in range(30)
        )
        sample = class_rank.top_sample_rows(rows)
        self.assertEqual(len(sample), 20)
        self.assertEqual(len({row["school"] for row in sample}), 20)


if __name__ == "__main__":
    unittest.main()
